"""
Detail Scraper for JamesAllen Fine Jewelry Rings.

Visits each product page and extracts:
- Full product details (name, SKU, description, specs)
- All variation prices (per metal type)
- Gallery image URLs
- Video URLs
- 360° viewer capture (screenshots during rotation)
"""

import asyncio
import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import config
from utils.browser import (
    create_browser,
    safe_goto,
    close_browser,
    wait_for_content,
    human_like_scroll,
)
from utils.logger import setup_logger
from utils.retry import retry

logger = setup_logger("detail_scraper")


class DetailScraper:
    """Scrapes individual product pages for complete data."""

    def __init__(self, pw=None, browser=None, context=None, page=None):
        self.pw = pw
        self.browser = browser
        self.context = context
        self.page = page
        self.owns_browser = False
        self.intercepted_images = []
        self.intercepted_videos = []
        self.intercepted_api_data = {}
        self.intercepted_3d_assets = []

    async def _ensure_browser(self):
        """Create browser if not provided externally."""
        if self.page is None:
            self.pw, self.browser, self.context, self.page = await create_browser()
            self.owns_browser = True

    async def _setup_interceptors(self):
        """Set up network request interceptors to capture media URLs and API data."""
        self.intercepted_images = []
        self.intercepted_videos = []
        self.intercepted_api_data = {}
        self.intercepted_3d_assets = []

        async def on_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")

            # Capture image URLs from CDN
            if any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                if url not in self.intercepted_images:
                    self.intercepted_images.append(url)

            # Capture video URLs
            if any(ext in url.lower() for ext in [".mp4", ".webm", ".mov"]):
                if url not in self.intercepted_videos:
                    self.intercepted_videos.append(url)
                    
            # Capture 3D WebGL assets
            if "JewelryViewer" in url and any(ext in url.lower() for ext in [".gltf", ".bin", ".hdr", ".json"]):
                if url not in self.intercepted_3d_assets:
                    self.intercepted_3d_assets.append(url)

            # Capture JSON API responses
            if "json" in content_type or "service-api" in url:
                try:
                    body = await response.json()
                    self.intercepted_api_data[url] = body
                except Exception:
                    pass

        self.page.on("response", on_response)

    async def scrape_product(self, product_url: str) -> dict:
        """
        Scrape a single product page for all data.

        Args:
            product_url: URL of the product page

        Returns:
            Dict with all product data
        """
        await self._ensure_browser()
        await self._setup_interceptors()

        logger.info(f"Scraping: {product_url}")

        product_data = {
            "product_url": product_url,
            "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            "product_id": "",
            "sku": "",
            "product_name": "",
            "category": "",
            "subcategory": "Fine Jewelry > Rings",
            "description": "",
            "base_price": "",
            "currency": "USD",
            "metal_type": "",
            "all_metal_options": "",
            "price_14k_white_gold": "",
            "price_14k_yellow_gold": "",
            "price_14k_rose_gold": "",
            "price_18k_white_gold": "",
            "price_18k_yellow_gold": "",
            "price_platinum": "",
            "stone_type": "",
            "carat": "",
            "stone_color": "",
            "stone_clarity": "",
            "ring_sizes": "",
            "ring_width": "",
            "ring_style": "",
            "image_main_url": "",
            "all_image_urls": "",
            "image_local_paths": "",
            "video_url": "",
            "video_local_path": "",
            "360_url": product_url,
            "360_local_path": "",
        }

        # Navigate to product page
        success = await safe_goto(self.page, product_url)
        if not success:
            logger.error(f"Failed to load: {product_url}")
            product_data["error"] = "Failed to load page"
            return product_data

        # Wait for page content
        await asyncio.sleep(4)

        # Extract product ID from URL
        product_data["product_id"] = self._extract_product_id(product_url)
        product_data["sku"] = product_data["product_id"]
        product_data["category"] = self._extract_category(product_url)

        # ── PRIMARY: Extract from JSON-LD structured data (most reliable) ──
        jsonld = await self._extract_jsonld_product()
        if jsonld:
            product_data["product_name"] = jsonld.get("name", "")
            product_data["description"] = jsonld.get("description", "")
            product_data["sku"] = jsonld.get("sku", product_data["sku"])
            product_data["metal_type"] = jsonld.get("material", "")
            offers = jsonld.get("offers", {})
            if offers.get("price"):
                product_data["base_price"] = str(offers["price"])
            if offers.get("priceCurrency"):
                product_data["currency"] = offers["priceCurrency"]
            logger.info(f"  JSON-LD ✓ name='{product_data['product_name'][:40]}' price=${product_data['base_price']}")

        # ── FALLBACK: Extract from DOM if JSON-LD missed anything ──
        if not product_data["product_name"] or not product_data["base_price"]:
            basic_info = await self._extract_basic_info()
            if not product_data["product_name"]:
                product_data["product_name"] = basic_info.get("product_name", "")
            if not product_data["base_price"]:
                product_data["base_price"] = basic_info.get("base_price", "")

        # Append structured specs to description
        specs_text = await self._extract_specs_text()
        if specs_text:
            product_data["description"] = (product_data["description"] + "\n\n" + specs_text).strip()

        # Extract stone/spec details
        specs = await self._extract_specifications()
        product_data.update(specs)

        # Extract available metal options and their prices
        metal_prices = await self._extract_metal_variations()
        product_data.update(metal_prices)

        # Extract ring sizes
        sizes = await self._extract_ring_sizes()
        product_data["ring_sizes"] = sizes

        # Collect all image URLs (from DOM + intercepted network)
        images = await self._extract_image_urls()
        if images:
            product_data["image_main_url"] = images[0]
            product_data["all_image_urls"] = " | ".join(images)

        # Collect video URLs
        videos = await self._extract_video_urls()
        if videos:
            product_data["video_url"] = " | ".join(videos)

        # Capture 360° rotation screenshots (Deprecated, now using WebGL assets)
        rotation_frames = []
        product_data["360_frames_captured"] = len(rotation_frames)
        product_data["_360_frames"] = rotation_frames  # internal, for media downloader

        # Store raw intercepted data for media downloader
        product_data["_all_intercepted_images"] = list(set(self.intercepted_images))
        product_data["_all_intercepted_videos"] = list(set(self.intercepted_videos))
        product_data["_all_intercepted_3d_assets"] = list(set(self.intercepted_3d_assets))

        logger.info(
            f"[green]✓[/green] {product_data['product_name'][:50]} | "
            f"${product_data['base_price']} | "
            f"{len(images)} images | "
            f"{len(rotation_frames)} 360° frames"
        )

        return product_data

    async def _extract_jsonld_product(self) -> dict:
        """Extract product data from JSON-LD structured data embedded in the page.
        
        JamesAllen embeds a <script type="application/ld+json"> with @type=Product
        containing reliable name, description, price, SKU, and material data.
        """
        try:
            result = await self.page.evaluate(r"""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const s of scripts) {
                        try {
                            const data = JSON.parse(s.textContent);
                            if (data['@type'] === 'Product') {
                                return data;
                            }
                        } catch (e) {}
                    }
                    return null;
                }
            """)
            return result or {}
        except Exception as e:
            logger.debug(f"JSON-LD extraction failed: {e}")
            return {}

    async def _extract_basic_info(self) -> dict:
        """Fallback: Extract product name and price from DOM elements."""
        info = {}

        # Try title tag first (JamesAllen has no h1, but title is reliable)
        info["product_name"] = await self._safe_text_content([
            'h1',
            '[class*="product-name"]',
            '[class*="ProductName"]',
            '[class*="product-title"]',
            '[class*="ProductTitle"]',
            '[data-testid*="product-name"]',
        ])
        # Last resort: extract from <title> tag
        if not info["product_name"]:
            title = await self.page.title()
            if title:
                # Strip the suffix like "-s01w14h01w14"
                info["product_name"] = re.sub(r'-[a-z0-9]+$', '', title, flags=re.I).strip()

        # Price: target the specific JamesAllen price span
        price_text = await self._safe_text_content([
            'span[class*="price--"]',
            'span[class*="prices--"]',
            '[class*="price"]',
            '[class*="Price"]',
        ])
        if price_text:
            price_clean = re.sub(r'[^\d.]', '', price_text.split("–")[0].split("-")[0])
            info["base_price"] = price_clean

        return info

    async def _extract_specs_text(self) -> str:
        """Extract structured specs (ring info table) as clean text."""
        try:
            specs_text = await self.page.evaluate(r"""
                () => {
                    // JamesAllen stores ring specs in descriptionTables class
                    const tables = document.querySelectorAll(
                        '[class*="descriptionTables"], [class*="info-table-row"]'
                    );
                    const lines = [];
                    for (const t of tables) {
                        const rows = t.querySelectorAll('[class*="info-table-row"]');
                        for (const r of rows) {
                            const cells = r.querySelectorAll('div, span');
                            const parts = [];
                            for (const c of cells) {
                                const txt = c.textContent?.trim();
                                if (txt && !parts.includes(txt)) parts.push(txt);
                            }
                            if (parts.length >= 2) {
                                lines.push(parts[0] + ': ' + parts.slice(1).join(', '));
                            }
                        }
                    }
                    return lines.join('\n');
                }
            """)
            return specs_text or ""
        except Exception:
            return ""

    async def _extract_specifications(self) -> dict:
        """Extract stone details and ring specifications."""
        specs = {}

        # Try to get spec data from structured elements
        spec_data = await self.page.evaluate(r"""
            () => {
                const specs = {};
                // Look for specification tables/lists
                const specSelectors = [
                    '[class*="spec"]', '[class*="Spec"]',
                    '[class*="detail"]', '[class*="Detail"]',
                    '[class*="attribute"]', '[class*="Attribute"]',
                    '[class*="info"]', '[class*="Info"]',
                    'table', 'dl',
                ];

                for (const sel of specSelectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const text = el.textContent || '';
                        // Extract key-value pairs
                        const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                        for (const line of lines) {
                            const lower = line.toLowerCase();
                            if (lower.includes('carat') || lower.includes('ct')) {
                                const match = line.match(/([\d.]+)\s*(ct|carat)/i);
                                if (match) specs.carat = match[1];
                            }
                            if (lower.includes('color')) {
                                const match = line.match(/color[:\s]*([A-Z\-]+)/i);
                                if (match) specs.stone_color = match[1];
                            }
                            if (lower.includes('clarity')) {
                                const match = line.match(/clarity[:\s]*([A-Z\d\-]+)/i);
                                if (match) specs.stone_clarity = match[1];
                            }
                            if (lower.includes('width')) {
                                const match = line.match(/([\d.]+)\s*mm/i);
                                if (match) specs.ring_width = match[1] + 'mm';
                            }
                            if (lower.includes('diamond')) specs.stone_type = 'Diamond';
                            if (lower.includes('sapphire')) specs.stone_type = 'Sapphire';
                            if (lower.includes('ruby')) specs.stone_type = 'Ruby';
                            if (lower.includes('emerald')) specs.stone_type = 'Emerald';
                            if (lower.includes('moissanite')) specs.stone_type = 'Moissanite';
                        }
                    }
                }

                return specs;
            }
        """)

        if spec_data:
            specs.update({k: v for k, v in spec_data.items() if v})

        return specs

    async def _extract_metal_variations(self) -> dict:
        """Extract per-metal prices by handling TWO JamesAllen page types:
        
        Type A — Custom/Fine Jewelry rings:
            Metal swatches are <button data-qa="head_metalColor_option_...">
            Clicking a button updates the price in-place via React.
            
        Type B — Engagement Ring Settings:
            Metal swatches are <a> links pointing to separate URLs per metal.
            Each URL has the metal pre-selected and its price pre-rendered.
            e.g. /14k-white-gold-...-item-50380 vs /platinum-...-item-50380
        """
        result = {
            "all_metal_options": "",
            "price_14k_white_gold": "",
            "price_14k_yellow_gold": "",
            "price_14k_rose_gold": "",
            "price_18k_white_gold": "",
            "price_18k_yellow_gold": "",
            "price_18k_rose_gold": "",
            "price_platinum": "",
        }

        await self.page.evaluate("window.scrollBy(0, 400)")
        await asyncio.sleep(2)

        # ── Try Type A first: button-based metal swatches ──
        metal_buttons = await self._find_metal_buttons()
        
        if metal_buttons:
            logger.info(f"  Found {len(metal_buttons)} metal buttons (Type A: button-click)")
            return await self._extract_prices_via_buttons(result, metal_buttons)
        
        # ── Try Type B: link-based metal swatches ──
        metal_links = await self._find_metal_links()
        
        if metal_links:
            logger.info(f"  Found {len(metal_links)} metal links (Type B: navigation)")
            return await self._extract_prices_via_links(result, metal_links)
        
        logger.warning("No metal variation elements found (neither buttons nor links)")
        return result

    async def _find_metal_buttons(self) -> list:
        """Find button-based metal selectors (Type A: Custom/Fine Jewelry rings)."""
        for attempt in range(3):
            try:
                await self.page.wait_for_selector(
                    'button[data-qa*="metalColor_option"], ul[class*="metal"] button[title]',
                    timeout=5000,
                )
            except Exception:
                logger.debug(f"  Metal buttons wait attempt {attempt+1}/3 timed out")
                continue

            metal_buttons = await self.page.evaluate(r"""
                () => {
                    const buttons = [];
                    const seen = new Set();
                    const qaButtons = document.querySelectorAll(
                        'button[data-qa*="metalColor_option"]'
                    );
                    for (const btn of qaButtons) {
                        const title = btn.getAttribute('title') || '';
                        const qa = btn.getAttribute('data-qa') || '';
                        if (qa.startsWith('shank_')) continue;
                        if (title && !seen.has(title)) {
                            seen.add(title);
                            buttons.push({ title, qa, type: 'button' });
                        }
                    }
                    if (buttons.length === 0) {
                        const metalLists = document.querySelectorAll('ul[class*="metal"]');
                        if (metalLists.length > 0) {
                            const items = metalLists[0].querySelectorAll('button[title]');
                            for (const btn of items) {
                                const title = btn.getAttribute('title') || '';
                                if (title && !seen.has(title)) {
                                    seen.add(title);
                                    buttons.push({ title, qa: '', type: 'button' });
                                }
                            }
                        }
                    }
                    return buttons;
                }
            """)
            if metal_buttons:
                return metal_buttons
        return []

    async def _find_metal_links(self) -> list:
        """Find link-based metal selectors (Type B: Engagement Ring Settings).
        
        These are <a> tags whose href contains metal keywords like
        '14k-white-gold', '18k-yellow-gold', 'platinum', etc.
        They're typically inside a metal color selector container.
        """
        metal_links = await self.page.evaluate(r"""
            () => {
                const links = [];
                const seen = new Set();
                
                // Known metal URL patterns
                const metalPatterns = [
                    { pattern: '14k-white-gold', label: '14K White Gold' },
                    { pattern: '14k-yellow-gold', label: '14K Yellow Gold' },
                    { pattern: '14k-rose-gold', label: '14K Rose Gold' },
                    { pattern: '18k-white-gold', label: '18K White Gold' },
                    { pattern: '18k-yellow-gold', label: '18K Yellow Gold' },
                    { pattern: '18k-rose-gold', label: '18K Rose Gold' },
                    { pattern: 'platinum', label: 'Platinum' },
                ];
                
                // Find all <a> links near metal selectors
                const allLinks = document.querySelectorAll('a[href*="engagement-rings"], a[href*="fine-jewelry"], a[href*="wedding-rings"]');
                
                for (const a of allLinks) {
                    const href = a.getAttribute('href') || '';
                    const hrefLower = href.toLowerCase();
                    
                    for (const mp of metalPatterns) {
                        if (hrefLower.includes(mp.pattern) && !seen.has(mp.label)) {
                            // Make sure this is a metal variant link (same item, different metal)
                            // They typically share the same item number at the end
                            const itemMatch = href.match(/item-(\d+)/);
                            if (itemMatch) {
                                seen.add(mp.label);
                                const fullUrl = href.startsWith('http') ? href : window.location.origin + href;
                                links.push({ 
                                    title: mp.label, 
                                    url: fullUrl,
                                    type: 'link' 
                                });
                            }
                        }
                    }
                }
                
                return links;
            }
        """)
        return metal_links or []

    async def _extract_prices_via_buttons(self, result: dict, metal_buttons: list) -> dict:
        """Extract prices by clicking button-based metal selectors (Type A)."""
        metal_options = []
        
        baseline_price = await self._read_current_price()
        logger.info(f"  Baseline price: ${baseline_price}")
        
        for btn_info in metal_buttons:
            metal_label = btn_info["title"]
            metal_options.append(metal_label)

            try:
                qa_val = btn_info.get("qa", "")
                selector = f'button[data-qa="{qa_val}"]' if qa_val else f'button[title="{metal_label}"]'

                await self.page.evaluate(
                    """(sel) => {
                        const btn = document.querySelector(sel);
                        if (btn) {
                            btn.removeAttribute('disabled');
                            btn.click();
                        }
                    }""",
                    selector,
                )
                await asyncio.sleep(2.5)

                price_clean = await self._read_current_price()
                if price_clean:
                    col = self._metal_to_column(metal_label)
                    if col:
                        result[col] = price_clean
                        logger.info(f"  Metal ✓ {metal_label}: ${price_clean}")
                else:
                    logger.debug(f"  Metal ✗ {metal_label}: could not read price")
            except Exception as e:
                logger.debug(f"Failed to click metal option '{metal_label}': {e}")

        result["all_metal_options"] = ", ".join(metal_options)
        return result

    async def _extract_prices_via_links(self, result: dict, metal_links: list) -> dict:
        """Extract prices by navigating to each metal variant URL (Type B).
        
        For engagement ring settings, each metal is a separate page URL.
        We visit each URL, read the price, then return to the original.
        """
        metal_options = []
        original_url = self.page.url
        
        # First, read the current page's price (it's one of the metals)
        current_price = await self._read_current_price()
        current_metal = self._detect_metal_from_url(original_url)
        if current_metal and current_price:
            col = self._metal_to_column(current_metal)
            if col:
                result[col] = current_price
                logger.info(f"  Metal ✓ {current_metal}: ${current_price} (current page)")
            metal_options.append(current_metal)
        
        # Visit each other metal variant URL
        for link_info in metal_links:
            metal_label = link_info["title"]
            metal_url = link_info["url"]
            
            if metal_label in metal_options:
                continue  # Already got this one
            metal_options.append(metal_label)
            
            try:
                # Navigate to the metal variant page
                from utils.browser import safe_goto
                success = await safe_goto(self.page, metal_url)
                if not success:
                    logger.debug(f"  Metal ✗ {metal_label}: failed to navigate")
                    continue
                
                await asyncio.sleep(3)
                
                price_clean = await self._read_current_price()
                if price_clean:
                    col = self._metal_to_column(metal_label)
                    if col:
                        result[col] = price_clean
                        logger.info(f"  Metal ✓ {metal_label}: ${price_clean}")
                else:
                    logger.debug(f"  Metal ✗ {metal_label}: could not read price")
                    
            except Exception as e:
                logger.debug(f"Failed to navigate to metal '{metal_label}': {e}")
        
        # Navigate back to the original URL
        try:
            from utils.browser import safe_goto
            await safe_goto(self.page, original_url)
            await asyncio.sleep(2)
        except Exception:
            pass
        
        result["all_metal_options"] = ", ".join(metal_options)
        return result

    def _detect_metal_from_url(self, url: str) -> str:
        """Detect which metal is selected based on URL path."""
        url_lower = url.lower()
        metal_url_map = {
            "14k-white-gold": "14K White Gold",
            "14k-yellow-gold": "14K Yellow Gold",
            "14k-rose-gold": "14K Rose Gold",
            "18k-white-gold": "18K White Gold",
            "18k-yellow-gold": "18K Yellow Gold",
            "18k-rose-gold": "18K Rose Gold",
            "platinum": "Platinum",
        }
        for pattern, label in metal_url_map.items():
            if pattern in url_lower:
                return label
        return ""

    async def _read_current_price(self) -> str:
        """Read the current displayed price from the page using multiple selector strategies.
        
        JamesAllen renders prices in various elements depending on page type:
        - Custom rings: span[class*="price--"] inside topPriceWrapper
        - Standard rings: span[class*="prices--"] 
        - Some pages: [class*="price"] with nested content
        
        Returns cleaned price string (digits only) or empty string.
        """
        # Strategy 1: Use page.evaluate to try multiple selectors and get the first valid price
        price_text = await self.page.evaluate(r"""
            () => {
                // Ordered from most specific to most generic
                const selectors = [
                    '[class*="topPriceWrapper"] span[class*="price"]',
                    'span[class*="price--"]',
                    'span[class*="prices--"]',
                    '[class*="settingPrice"] span',
                    '[class*="Price"] span',
                    '[class*="price"]',
                ];
                
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const text = el.textContent || '';
                        // Look for a dollar sign followed by digits
                        const match = text.match(/\$[\d,]+/);
                        if (match) {
                            return match[0];
                        }
                    }
                }
                return '';
            }
        """)
        
        if price_text:
            price_clean = re.sub(r'[^\d.]', '', price_text.split("–")[0].split("-")[0])
            return price_clean
        
        # Strategy 2: Fallback to _safe_text_content
        price_text = await self._safe_text_content([
            'span[class*="price--"]',
            'span[class*="prices--"]',
            '[class*="topPriceWrapper"] span',
            '[class*="price"]',
        ])
        if price_text:
            price_clean = re.sub(r'[^\d.]', '', price_text.split("–")[0].split("-")[0])
            return price_clean
            
        return ""

    async def _extract_ring_sizes(self) -> str:
        """Extract available ring sizes."""
        sizes = await self.page.evaluate(r"""
            () => {
                const sizes = [];
                const selectors = [
                    'select[class*="size"] option',
                    'select[name*="size"] option',
                    '[class*="size-option"]',
                    '[class*="SizeOption"]',
                    '[data-testid*="size"]',
                ];

                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const text = el.textContent?.trim() || el.value || '';
                        const sizeMatch = text.match(/(\d+\.?\d*)/);
                        if (sizeMatch) {
                            sizes.push(sizeMatch[1]);
                        }
                    }
                    if (sizes.length > 0) break;
                }

                return [...new Set(sizes)].sort((a, b) => parseFloat(a) - parseFloat(b));
            }
        """)

        return ", ".join(sizes) if sizes else ""

    async def _extract_image_urls(self) -> list[str]:
        """Extract high-quality product images only.
        
        JamesAllen product images live under paths containing
        'Photoshoot' or 'BrioPackshot'. All other images on the page
        (matcap textures, panorama cubemaps, menu banners, SVG icons)
        are not product images and must be excluded.
        """
        # ── Strategy 1: Get all img src from DOM and filter ──
        dom_images = await self.page.evaluate(r"""
            () => {
                const images = [];
                const allImgs = document.querySelectorAll('img');
                for (const img of allImgs) {
                    const src = img.src || img.dataset.src || img.dataset.lazySrc || '';
                    if (src && (src.includes('Photoshoot') || src.includes('BrioPackshot'))) {
                        images.push(src);
                    }
                }

                // Also check JSON-LD for the canonical product image
                const ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (const s of ldScripts) {
                    try {
                        const data = JSON.parse(s.textContent);
                        if (data['@type'] === 'Product' && data.image) {
                            images.push(data.image);
                        }
                    } catch (e) {}
                }

                // Check og:image meta tag
                const ogImg = document.querySelector('meta[property="og:image"]');
                if (ogImg && ogImg.content) images.push(ogImg.content);

                return [...new Set(images)];
            }
        """)

        all_images = list(dom_images or [])

        # ── Strategy 2: Filter intercepted network images ──
        # Only keep actual product photos from the CDN
        PRODUCT_IMAGE_PATTERNS = [
            "Photoshoot", "BrioPackshot", "stage.jpg",
        ]
        EXCLUDE_PATTERNS = [
            "matcap", "panorama", "MenuBanner", "metalIcon",
            "favicon", "logo", "apple-touch", "ring_studio",
            ".svg", "clearance", "Campaigns", "close.svg",
        ]
        for url in self.intercepted_images:
            if any(p in url for p in PRODUCT_IMAGE_PATTERNS):
                if not any(x in url for x in EXCLUDE_PATTERNS):
                    if url not in all_images:
                        all_images.append(url)

        return all_images

    async def _extract_video_urls(self) -> list[str]:
        """Extract video URLs from DOM and intercepted requests."""
        dom_videos = await self.page.evaluate(r"""
            () => {
                const videos = [];
                // Check video elements
                const videoEls = document.querySelectorAll('video source, video');
                for (const v of videoEls) {
                    const src = v.src || v.querySelector('source')?.src || '';
                    if (src) videos.push(src);
                }
                // Check iframes (might contain embedded video)
                const iframes = document.querySelectorAll('iframe[src*="video"], iframe[src*="player"]');
                for (const f of iframes) {
                    videos.push(f.src);
                }
                return [...new Set(videos)];
            }
        """)

        all_videos = list(dom_videos or [])
        for url in self.intercepted_videos:
            if url not in all_videos:
                all_videos.append(url)

        return all_videos

    async def _capture_360_rotation(self) -> list[bytes]:
        """
        Capture full spherical 360° frames by screenshotting the WebGL viewer
        at multiple vertical tilt angles, each with a complete horizontal rotation.
        
        Layout:
          Row 1 (tilt up):   top-down view — 36 frames
          Row 2 (eye level): straight-on view — 36 frames
          Row 3 (tilt down): bottom-up view — 36 frames
          Total: 108 frames covering all angles
        
        Returns:
            List of frame bytes (JPEG images)
        """
        frames = []
        logger.info("Attempting 360° capture (full spherical)...")

        try:
            VIEWER_LOAD_WAIT = 8
            MIN_VALID_FRAME_SIZE = 15000

            # Check for media error in main page text
            page_text = await self.page.evaluate("document.body.innerText")
            if page_text and "Real Time Item Media Not Available" in page_text:
                logger.warning("360° media not available (main page). Skipping.")
                return frames

            # Check inside iframes for the error
            try:
                for frame in self.page.frames:
                    try:
                        frame_text = await frame.evaluate(
                            "document.body ? document.body.innerText : ''"
                        )
                        if frame_text and "Real Time Item Media Not Available" in frame_text:
                            logger.warning("360° media not available (iframe). Skipping.")
                            return frames
                    except Exception:
                        pass
            except Exception:
                pass

            # Find the 360° viewer element
            viewer_box = await self.page.evaluate("""
                () => {
                    const figures = document.querySelectorAll('figure');
                    for (const fig of figures) {
                        const text = fig.textContent || '';
                        if (text.includes('360') || text.includes('SPIN') || text.includes('DRAG')) {
                            const rect = fig.getBoundingClientRect();
                            if (rect.width > 100 && rect.height > 100)
                                return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, found_via: '360-figure' };
                        }
                    }
                    for (const c of document.querySelectorAll('canvas')) {
                        const rect = c.getBoundingClientRect();
                        if (rect.width > 200 && rect.height > 200)
                            return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, found_via: 'canvas' };
                    }
                    for (const f of document.querySelectorAll('iframe')) {
                        const rect = f.getBoundingClientRect();
                        if (rect.width > 200 && rect.height > 200)
                            return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, found_via: 'iframe' };
                    }
                    const sels = ['[class*="360"]','[class*="viewer"]','[class*="Viewer"]',
                                  '[class*="spin"]','[class*="rotate"]','[id*="360"]','[id*="viewer"]'];
                    for (const sel of sels) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 200 && rect.height > 200)
                                return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, found_via: 'class-match' };
                        }
                    }
                    return null;
                }
            """)
            if not viewer_box:
                logger.debug("No 360° viewer element found on page")
                return frames

            logger.info(f"360° viewer found via: {viewer_box.get('found_via')}")
            logger.info(f"Viewer size: {viewer_box['width']:.0f}x{viewer_box['height']:.0f}")

            # Wait for the WebGL 3D model to fully render
            logger.info(f"Waiting {VIEWER_LOAD_WAIT}s for WebGL viewer to render...")
            await asyncio.sleep(VIEWER_LOAD_WAIT)

            vx, vy = viewer_box["x"], viewer_box["y"]
            vw, vh = viewer_box["width"], viewer_box["height"]
            center_x = vx + vw / 2
            center_y = vy + vh / 2

            # Click to activate the viewer and dismiss the overlay
            await self.page.mouse.click(center_x, center_y)
            await asyncio.sleep(1)
            await self.page.mouse.click(center_x, center_y)
            await asyncio.sleep(0.5)

            # Clip region (slight inset to avoid borders)
            clip = {
                "x": max(0, vx + 2),
                "y": max(0, vy + 2),
                "width": vw - 4,
                "height": vh - 4,
            }

            # Validate the viewer is rendering real content
            test_shot = await self.page.screenshot(
                clip=clip,
                type=config.SCREENSHOT_FORMAT,
                quality=config.SCREENSHOT_QUALITY,
            )
            if len(test_shot) < MIN_VALID_FRAME_SIZE:
                logger.warning(
                    f"360° viewer shows invalid content ({len(test_shot)} bytes). Skipping."
                )
                return frames
            logger.info(f"WebGL viewer is active ({len(test_shot)} bytes)")

            # ── Multi-row spherical capture ─────────────────────────────
            tilt_rows = config.VERTICAL_TILT_ROWS
            total_expected = len(tilt_rows) * config.ROTATION_FRAMES
            logger.info(
                f"Capturing {len(tilt_rows)} vertical rows × "
                f"{config.ROTATION_FRAMES} horizontal frames = {total_expected} total"
            )

            for row_idx, tilt_fraction in enumerate(tilt_rows):
                row_label = "top-down" if tilt_fraction < 0 else ("bottom-up" if tilt_fraction > 0 else "eye-level")
                logger.info(f"Row {row_idx + 1}/{len(tilt_rows)}: {row_label} (tilt={tilt_fraction:+.2f})")

                # ── Apply vertical tilt ─────────────────────────────────
                if tilt_fraction != 0:
                    tilt_distance = vh * tilt_fraction  # pixels to drag vertically
                    await self.page.mouse.move(center_x, center_y)
                    await self.page.mouse.down()
                    await asyncio.sleep(0.1)

                    # Smooth vertical drag
                    tilt_steps = max(5, int(abs(tilt_distance) / 3))
                    dy = tilt_distance / tilt_steps
                    current_tilt_y = center_y
                    for _ in range(tilt_steps):
                        current_tilt_y += dy
                        await self.page.mouse.move(center_x, current_tilt_y)
                        await asyncio.sleep(0.01)

                    await self.page.mouse.up()
                    await asyncio.sleep(0.3)

                # ── Capture first frame of this row ─────────────────────
                screenshot = await self.page.screenshot(
                    clip=clip,
                    type=config.SCREENSHOT_FORMAT,
                    quality=config.SCREENSHOT_QUALITY,
                )
                frames.append(screenshot)

                # ── Horizontal 360° rotation for this row ───────────────
                total_drag = vw * 2.0
                step_distance = total_drag / config.ROTATION_FRAMES
                start_x = vx + vw * 0.3
                current_x = start_x
                drag_y = center_y + (vh * tilt_fraction * 0.3)  # drag along the tilted axis

                await self.page.mouse.move(start_x, drag_y)
                await self.page.mouse.down()
                await asyncio.sleep(0.15)

                for i in range(1, config.ROTATION_FRAMES):
                    # Smooth horizontal drag
                    micro_steps = max(3, int(step_distance / 5))
                    dx = step_distance / micro_steps
                    for _ in range(micro_steps):
                        current_x += dx
                        await self.page.mouse.move(current_x, drag_y)
                        await asyncio.sleep(0.01)

                    await asyncio.sleep(config.ROTATION_STEP_DELAY)

                    # Re-anchor if past viewer edge
                    if current_x > vx + vw * 0.9:
                        await self.page.mouse.up()
                        await asyncio.sleep(0.1)
                        current_x = start_x
                        await self.page.mouse.move(current_x, drag_y)
                        await self.page.mouse.down()
                        await asyncio.sleep(0.1)

                    # Capture frame
                    screenshot = await self.page.screenshot(
                        clip=clip,
                        type=config.SCREENSHOT_FORMAT,
                        quality=config.SCREENSHOT_QUALITY,
                    )
                    frames.append(screenshot)

                await self.page.mouse.up()
                logger.info(f"  Row {row_idx + 1} done — {len(frames)} frames so far")

                # ── Reset tilt back to center before next row ───────────
                if tilt_fraction != 0:
                    reset_distance = -vh * tilt_fraction
                    await self.page.mouse.move(center_x, center_y)
                    await self.page.mouse.down()
                    await asyncio.sleep(0.1)

                    tilt_steps = max(5, int(abs(reset_distance) / 3))
                    dy = reset_distance / tilt_steps
                    current_tilt_y = center_y
                    for _ in range(tilt_steps):
                        current_tilt_y += dy
                        await self.page.mouse.move(center_x, current_tilt_y)
                        await asyncio.sleep(0.01)

                    await self.page.mouse.up()
                    await asyncio.sleep(0.3)

            logger.info(f"✓ Captured {len(frames)} 360° frames ({len(tilt_rows)} rows × {config.ROTATION_FRAMES} angles)")

        except Exception as e:
            logger.warning(f"360° capture failed: {e}")

        return frames

    async def _safe_text_content(self, selectors: list[str]) -> str:
        """Try multiple selectors and return the first text content found."""
        for sel in selectors:
            try:
                el = await self.page.query_selector(sel)
                if el:
                    text = await el.text_content()
                    if text and text.strip():
                        return text.strip()
            except Exception:
                pass
        return ""

    def _extract_product_id(self, url: str) -> str:
        """Extract product ID from URL."""
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p]
        if parts:
            # Last segment is usually the product slug
            slug = parts[-1]
            # Try to extract numeric ID
            match = re.search(r'(\d{4,})', slug)
            if match:
                return match.group(1)
            # Use the slug as ID
            return slug
        return ""

    def _extract_category(self, url: str) -> str:
        """Extract category from URL."""
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            return parts[1].replace("-", " ").title()
        return "Rings"

    def _metal_to_column(self, metal_label: str) -> str:
        """Map a metal label to its CSV column name."""
        label_lower = metal_label.lower()
        mapping = {
            "14k white gold": "price_14k_white_gold",
            "14k yellow gold": "price_14k_yellow_gold",
            "14k rose gold": "price_14k_rose_gold",
            "18k white gold": "price_18k_white_gold",
            "18k yellow gold": "price_18k_yellow_gold",
            "18k rose gold": "price_18k_rose_gold",
            "platinum": "price_platinum",
        }
        for key, col in mapping.items():
            if key in label_lower:
                return col
        return ""

    async def close(self):
        """Close browser if we own it."""
        if self.owns_browser and self.browser:
            await close_browser(self.pw, self.browser)


async def scrape_single_product(url: str) -> dict:
    """Convenience function to scrape a single product."""
    scraper = DetailScraper()
    try:
        return await scraper.scrape_product(url)
    finally:
        await scraper.close()


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.jamesallen.com/fine-jewelry/"
    result = asyncio.run(scrape_single_product(url))
    print(json.dumps({k: v for k, v in result.items() if not k.startswith("_")}, indent=2))
