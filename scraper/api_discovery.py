"""
API Discovery Tool for JamesAllen.com

Intercepts all network requests on a product page to identify:
- Product data API endpoints
- Image CDN URL patterns
- 360° asset URLs
- Price/variation API calls

Run this FIRST before building scrapers.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

import config
from utils.browser import create_browser, safe_goto, close_browser, human_like_scroll
from utils.logger import setup_logger

logger = setup_logger("discovery")


class APIDiscovery:
    """Intercepts and analyzes network traffic on JamesAllen product pages."""

    def __init__(self):
        self.requests_log = []
        self.responses_log = []
        self.api_endpoints = defaultdict(list)
        self.cdn_patterns = set()
        self.image_urls = []
        self.video_urls = []
        self.json_responses = []

    def _categorize_url(self, url: str) -> str:
        """Categorize a URL by its likely purpose."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        hostname = parsed.hostname or ""

        if "service-api" in path or "api" in path:
            return "API"
        elif any(ext in path for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"]):
            return "IMAGE"
        elif any(ext in path for ext in [".mp4", ".webm", ".mov"]):
            return "VIDEO"
        elif any(ext in path for ext in [".js"]):
            return "SCRIPT"
        elif any(ext in path for ext in [".css"]):
            return "STYLE"
        elif any(ext in path for ext in [".woff", ".woff2", ".ttf", ".eot"]):
            return "FONT"
        elif "cdn" in hostname or "akamai" in hostname or "cloudfront" in hostname:
            return "CDN"
        elif any(tracker in hostname for tracker in ["google", "facebook", "analytics", "doubleclick", "segment", "hotjar"]):
            return "TRACKING"
        else:
            return "OTHER"

    async def _on_request(self, request):
        """Callback for intercepted requests."""
        url = request.url
        category = self._categorize_url(url)
        method = request.method
        resource_type = request.resource_type

        self.requests_log.append({
            "url": url,
            "method": method,
            "resource_type": resource_type,
            "category": category,
            "headers": dict(request.headers) if category == "API" else None,
        })

        if category == "IMAGE":
            self.image_urls.append(url)
        elif category == "VIDEO":
            self.video_urls.append(url)

    async def _on_response(self, response):
        """Callback for intercepted responses."""
        url = response.url
        category = self._categorize_url(url)
        status = response.status
        content_type = response.headers.get("content-type", "")

        entry = {
            "url": url,
            "status": status,
            "content_type": content_type,
            "category": category,
        }

        # Try to capture JSON responses (likely API data)
        if "json" in content_type or category == "API":
            try:
                body = await response.json()
                entry["body_preview"] = json.dumps(body, indent=2)[:2000]
                self.json_responses.append({
                    "url": url,
                    "status": status,
                    "body": body,
                })
                logger.info(f"[bold green]JSON API found:[/bold green] {url}")
            except Exception:
                pass

        self.responses_log.append(entry)
        self.api_endpoints[category].append(url)

    async def discover(self, product_url: str = None):
        """
        Run API discovery on a product page.

        Args:
            product_url: Specific product URL to analyze. If None, uses the listing page.
        """
        target_url = product_url or config.FINE_JEWELRY_RINGS_URL

        logger.info(f"[bold]Starting API Discovery[/bold]")
        logger.info(f"Target: {target_url}")

        pw, browser, context, page = await create_browser(headless=False)

        try:
            # Attach network interceptors
            page.on("request", self._on_request)
            page.on("response", self._on_response)

            # Navigate to the page
            logger.info("Navigating to target page...")
            await safe_goto(page, target_url, wait_until="domcontentloaded")

            # Wait for content to load
            logger.info("Waiting for dynamic content to load...")
            await asyncio.sleep(5)

            # Scroll to trigger lazy-loaded content
            logger.info("Scrolling to trigger lazy content...")
            await human_like_scroll(page, scrolls=5, delay=1.0)
            await asyncio.sleep(3)

            # If on a product page, try interacting with variation selectors
            if product_url:
                logger.info("Attempting to interact with variation selectors...")
                try:
                    # Try clicking metal options
                    metal_selectors = await page.query_selector_all(
                        '[data-testid*="metal"], [class*="metal"], [class*="Metal"], '
                        'button[class*="swatch"], [class*="option"]'
                    )
                    for i, selector in enumerate(metal_selectors[:3]):
                        try:
                            await selector.click()
                            await asyncio.sleep(2)
                            logger.info(f"Clicked variation selector {i+1}")
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug(f"Variation interaction failed: {e}")

            # Wait a bit more for any delayed requests
            await asyncio.sleep(3)

            # Generate report
            self._generate_report()

            # Keep browser open for manual inspection
            logger.info("[bold yellow]Browser left open for manual inspection.[/bold yellow]")
            logger.info("Press Ctrl+C to close and save report.")

            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass

        finally:
            await close_browser(pw, browser)

    def _generate_report(self):
        """Generate and save the discovery report."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("JAMESALLEN.COM — API DISCOVERY REPORT")
        report_lines.append(f"Generated: {datetime.now().isoformat()}")
        report_lines.append("=" * 80)

        # Summary
        report_lines.append("\n## SUMMARY")
        report_lines.append(f"Total requests intercepted: {len(self.requests_log)}")
        report_lines.append(f"Total responses captured: {len(self.responses_log)}")
        report_lines.append(f"JSON API responses found: {len(self.json_responses)}")
        report_lines.append(f"Image URLs found: {len(self.image_urls)}")
        report_lines.append(f"Video URLs found: {len(self.video_urls)}")

        # Requests by category
        report_lines.append("\n## REQUESTS BY CATEGORY")
        for category, urls in sorted(self.api_endpoints.items()):
            report_lines.append(f"\n### {category} ({len(urls)} requests)")
            # Deduplicate and show unique URL patterns
            unique_patterns = set()
            for url in urls:
                parsed = urlparse(url)
                pattern = f"{parsed.scheme}://{parsed.hostname}{parsed.path}"
                unique_patterns.add(pattern)
            for pattern in sorted(unique_patterns)[:20]:
                report_lines.append(f"  - {pattern}")
            if len(unique_patterns) > 20:
                report_lines.append(f"  ... and {len(unique_patterns) - 20} more")

        # JSON API Details
        if self.json_responses:
            report_lines.append("\n## JSON API RESPONSES (CRITICAL)")
            for i, resp in enumerate(self.json_responses):
                report_lines.append(f"\n### API Response {i+1}")
                report_lines.append(f"URL: {resp['url']}")
                report_lines.append(f"Status: {resp['status']}")
                # Show structure of the JSON
                body = resp["body"]
                if isinstance(body, dict):
                    report_lines.append(f"Keys: {list(body.keys())}")
                    report_lines.append(f"Preview:\n{json.dumps(body, indent=2)[:3000]}")
                elif isinstance(body, list):
                    report_lines.append(f"Array of {len(body)} items")
                    if body:
                        report_lines.append(f"First item keys: {list(body[0].keys()) if isinstance(body[0], dict) else 'N/A'}")
                        report_lines.append(f"Preview:\n{json.dumps(body[0], indent=2)[:2000]}")

        # Image URL Patterns
        if self.image_urls:
            report_lines.append("\n## IMAGE URL PATTERNS")
            domains = defaultdict(int)
            for url in self.image_urls:
                parsed = urlparse(url)
                domains[parsed.hostname] += 1
            for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
                report_lines.append(f"  {domain}: {count} images")
            report_lines.append("\nSample image URLs:")
            for url in self.image_urls[:10]:
                report_lines.append(f"  - {url}")

        # Video URL Patterns
        if self.video_urls:
            report_lines.append("\n## VIDEO URL PATTERNS")
            for url in self.video_urls[:10]:
                report_lines.append(f"  - {url}")

        # Save report
        report_text = "\n".join(report_lines)
        config.DISCOVERY_REPORT_FILE.write_text(report_text, encoding="utf-8")
        logger.info(f"[bold green]Report saved:[/bold green] {config.DISCOVERY_REPORT_FILE}")

        # Also print to console
        print("\n" + report_text)


async def run_discovery(product_url: str = None):
    """Entry point for API discovery."""
    discovery = APIDiscovery()
    await discovery.discover(product_url)
    return discovery


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(run_discovery(url))
