#!/usr/bin/env python3
"""
Quick script to fetch 3 products from JamesAllen.
Picks 3 URLs that haven't been scraped yet (no existing output folder).
"""

import asyncio
import json
import sys
from pathlib import Path

import config
from scraper.detail_scraper import DetailScraper
from scraper.media_downloader import MediaDownloader
from output.csv_generator import append_to_csv
from output.folder_generator import save_product_metadata
from utils.logger import setup_logger

logger = setup_logger("fetch_3")

# Already-scraped product IDs (from output directory)
ALREADY_SCRAPED = set()
for d in config.OUTPUT_DIR.iterdir():
    if d.is_dir() and d.name.startswith("product_"):
        ALREADY_SCRAPED.add(d.name.replace("product_", ""))


async def main():
    # Read URLs from urls.txt
    urls_file = Path("urls.txt")
    with open(urls_file) as f:
        all_urls = [line.strip() for line in f if line.strip()]

    # Pick 3 URLs not yet scraped
    import re
    selected = []
    for url in all_urls:
        match = re.search(r'item-(\d+)', url)
        if match and match.group(1) not in ALREADY_SCRAPED:
            selected.append(url)
        if len(selected) >= 3:
            break

    if not selected:
        logger.error("No unscraped URLs found!")
        sys.exit(1)

    logger.info(f"Selected {len(selected)} products to scrape:")
    for url in selected:
        logger.info(f"  → {url}")

    scraper = DetailScraper()
    downloader = MediaDownloader()

    try:
        for i, url in enumerate(selected):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i+1}/{len(selected)}] Scraping: {url}")
            logger.info(f"{'='*60}")

            try:
                # Scrape product details
                product_data = await scraper.scrape_product(url)
                if product_data.get("error"):
                    logger.error(f"Scraping failed: {product_data['error']}")
                    continue

                # Download media (images, 3D assets, videos)
                product_data = await downloader.download_product_media(product_data)

                # Save metadata JSON
                save_product_metadata(product_data)

                # Append to CSV
                append_to_csv(product_data)

                logger.info(f"✅ Done: {product_data.get('product_name', 'Unknown')}")

            except Exception as e:
                logger.error(f"❌ Failed: {url} — {e}")

            # Small delay between products
            await asyncio.sleep(3)

    finally:
        await scraper.close()
        await downloader.close()

    logger.info("\n🎉 All done! Check the output/ directory for results.")


if __name__ == "__main__":
    asyncio.run(main())
