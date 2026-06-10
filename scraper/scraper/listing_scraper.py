"""
Listing Scraper for JamesAllen Engagement Rings.

Crawls the listing page(s) and collects all product URLs,
names, thumbnails, and prices into an index file.
"""

import asyncio
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

import config
from utils.browser import (
    create_browser,
    safe_goto,
    close_browser,
    wait_for_content,
)
from utils.logger import setup_logger

logger = setup_logger("listing_scraper")

class ListingScraper:
    """Scrapes product listing pages to build an index of all products interactively."""

    def __init__(self):
        self.products = []
        self.seen_urls = set()

    async def scrape_listings(self, target_url: str = "https://www.jamesallen.com/engagement-rings/") -> list[dict]:
        """
        Scrape all ring product listings interactively.

        Args:
            target_url: URL to scrape (default is engagement rings)

        Returns:
            List of product dicts with url, name, thumbnail, price, category
        """
        logger.info("[bold]Starting Interactive Listing Scraper[/bold]")
        logger.info(f"Target: {target_url}")
        
        # Force headless to False for the interactive process
        original_headless = config.HEADLESS
        config.HEADLESS = False

        pw, browser, context, page = await create_browser()

        try:
            # Navigate to the rings listing
            logger.info(f"Navigating to {target_url}...")
            success = await safe_goto(page, target_url)
            if not success:
                logger.error("Failed to load listing page")
                return []

            logger.info("\n" + "="*60)
            logger.info("👨‍💻 ACTION REQUIRED IN BROWSER 👨‍💻")
            logger.info("1. Please solve any CAPTCHAs if they appear.")
            logger.info("2. Manually scroll down the page to the very bottom.")
            logger.info("3. Ensure all products (approx 754) have loaded on screen.")
            logger.info("="*60 + "\n")
            
            # Wait for user to confirm they are done scrolling
            await self._wait_for_user_confirmation()

            # Extract products from the page
            products = await self._extract_products(page)
            logger.info(f"Extracted {len(products)} products from listing")

            # Save index
            self._save_index()

            return self.products

        finally:
            config.HEADLESS = original_headless
            await close_browser(pw, browser)

    async def _wait_for_user_confirmation(self):
        """Wait for the user to press Enter in the console asynchronously."""
        loop = asyncio.get_event_loop()
        print("\n>>> When you have reached the bottom of the page, press ENTER to start extracting... <<<", flush=True)
        await loop.run_in_executor(None, sys.stdin.readline)
        logger.info("User confirmed. Starting extraction...")

    async def _extract_products(self, page) -> list[dict]:
        """Extract product data from the current page."""
        logger.info("Extracting product data from page...")

        products = await page.evaluate("""
            () => {
                const products = [];
                const seen = new Set();

                // Find all product links (engagement rings usually have 'item-' or are within engagement-rings path)
                const links = document.querySelectorAll('a[href*="/engagement-rings/"], a[href*="/fine-jewelry/"], a[href*="item-"]');
                for (const link of links) {
                    const href = link.href;

                    // We want product links. Product links usually have 'item-' in the URL
                    if (!href.includes('item-')) continue;

                    if (seen.has(href)) continue;
                    seen.add(href);

                    // Try to extract product info from the card
                    const card = link.closest('[class*="product"], [class*="Product"], [class*="item"], [class*="Item"], [class*="card"], [class*="Card"]') || link;

                    // Name
                    const nameEl = card.querySelector('[class*="name"], [class*="Name"], [class*="title"], [class*="Title"], h2, h3, h4');
                    const name = nameEl ? nameEl.textContent.trim() : link.textContent.trim();

                    // Price
                    const priceEl = card.querySelector('[class*="price"], [class*="Price"], [class*="amount"]');
                    const price = priceEl ? priceEl.textContent.trim() : '';

                    // Thumbnail
                    const imgEl = card.querySelector('img');
                    const thumbnail = imgEl ? (imgEl.src || imgEl.dataset.src || '') : '';

                    if (name && name.length > 2) {
                        products.push({
                            url: href,
                            name: name.substring(0, 200),
                            price: price,
                            thumbnail: thumbnail,
                        });
                    }
                }

                return products;
            }
        """)

        # Deduplicate and add to main list
        for product in products:
            url = product["url"]
            if url not in self.seen_urls:
                self.seen_urls.add(url)
                product["category"] = "Engagement Rings"
                product["scraped_at"] = datetime.now().isoformat()
                self.products.append(product)

        return products

    def _save_index(self):
        """Save product index to CSV."""
        if not self.products:
            logger.warning("No products to save!")
            return

        filepath = Path("checkpoints/engagement_rings_index.csv")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["url", "name", "price", "thumbnail", "category", "scraped_at"],
            )
            writer.writeheader()
            writer.writerows(self.products)

        logger.info(f"[bold green]Product index saved:[/bold green] {filepath}")
        logger.info(f"Total products indexed: {len(self.products)}")


async def run_listing_scraper() -> list[dict]:
    """Entry point for listing scraper."""
    scraper = ListingScraper()
    return await scraper.scrape_listings()


if __name__ == "__main__":
    asyncio.run(run_listing_scraper())

