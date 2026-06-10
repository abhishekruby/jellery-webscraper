#!/usr/bin/env python3
"""
JamesAllen.com Engagement Rings Scraper — Main Entry Point

Usage:
    python main.py discover [--target URL]    # Phase 1: Interactive URL discovery
    python main.py scrape                     # Phase 2: Scrape in batches
    python main.py status                     # View progress dashboard
    python main.py test --url URL             # Test: Scrape 1 product end-to-end
    python main.py csv                        # Regenerate CSV from downloaded data
    python main.py summary                    # Show output summary
"""

import argparse
import asyncio
import csv
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import config
from utils.logger import setup_logger
from utils.progress_tracker import ProgressTracker

logger = setup_logger("main")


async def cmd_discover(args):
    """Guide the user to manually extract URLs using their personal browser."""
    logger.info("[bold cyan]═══ BROWSER-BASED URL DISCOVERY ═══[/bold cyan]")
    
    print("\n" + "="*80)
    print("🚨 FIXING THE 67 URL ISSUE 🚨")
    print("JamesAllen uses a 'virtualized' DOM. When you scroll down, old rings disappear")
    print("from memory! To fix this, we will run a background tracker WHILE you scroll.")
    print("="*80 + "\n")
    print("STEP 1: Open your Chrome to: https://www.jamesallen.com/engagement-rings/")
    print("STEP 2: BEFORE scrolling, right-click -> 'Inspect' -> 'Console' tab.")
    print("STEP 3: Paste the following code and press Enter to start the tracker:\n")
    
    js_code = """
window.allJamesAllenUrls = new Set();

// Grab initially visible rings
document.querySelectorAll('a[href*="/engagement-rings/"], a[href*="item-"]').forEach(link => {
    if (link.href.includes('item-')) window.allJamesAllenUrls.add(link.href);
});

// Watch for new rings as you scroll
const observer = new MutationObserver(() => {
    document.querySelectorAll('a[href*="/engagement-rings/"], a[href*="item-"]').forEach(link => {
        if (link.href.includes('item-')) window.allJamesAllenUrls.add(link.href);
    });
});
observer.observe(document.body, { childList: true, subtree: true });

console.log('✅ TRACKER STARTED! Start scrolling down slowly... ✅');

// Create a floating counter on the screen
const counter = document.createElement('div');
counter.style = 'position:fixed;top:10px;left:10px;background:red;color:white;padding:10px;font-size:20px;z-index:999999;border-radius:5px;';
document.body.appendChild(counter);
setInterval(() => { counter.innerText = 'Rings Found: ' + window.allJamesAllenUrls.size; }, 500);

// Function to run when finished
window.finishScraping = function() {
    observer.disconnect();
    const result = Array.from(window.allJamesAllenUrls).join('\\n');
    copy(result);
    console.log('✅ FINISHED! ' + window.allJamesAllenUrls.size + ' URLs copied to clipboard! ✅');
    counter.innerText = 'COPIED TO CLIPBOARD!';
};
"""
    print("\033[93m" + js_code + "\033[0m")
    
    print("\nSTEP 4: Now, scroll slowly down the page until you reach the bottom.")
    print("        (You will see a red counter in the top-left corner tracking the rings!)")
    print("STEP 5: When the counter reaches ~754, type this in the Console and press Enter:\n")
    print("\033[96mfinishScraping();\033[0m\n")
    print("STEP 6: The URLs are now copied! Open 'urls.txt' in this directory, paste them, and save.")
    
    input("\n>>> Press ENTER when you have saved 'urls.txt' <<<")
    
    try:
        urls_file = Path("urls.txt")
        if not urls_file.exists():
            logger.error("urls.txt not found. Please create it and paste the URLs.")
            return
            
        with open(urls_file, "r") as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]
            
        if not urls:
            logger.error("urls.txt is empty!")
            return
            
        logger.info(f"Read {len(urls)} URLs from urls.txt")
        
        # Load into DB
        tracker = ProgressTracker()
        
        import sqlite3
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR IGNORE INTO products (url, last_updated) VALUES (?, CURRENT_TIMESTAMP)",
                [(u,) for u in urls]
            )
            conn.commit()
            
        logger.info("[bold green]✅ URLs successfully loaded into database![/bold green]")
        logger.info("You can now run: python main.py scrape")
        
    except Exception as e:
        logger.error(f"Failed to ingest URLs: {e}")


async def cmd_status(args):
    """Show progress dashboard."""
    tracker = ProgressTracker()
    stats = tracker.get_stats()
    
    logger.info("[bold cyan]═══ SCRAPER STATUS ═══[/bold cyan]")
    logger.info(f"Total Discovered: {stats['total']}")
    logger.info(f"Completed:        [green]{stats['completed']}[/green]")
    logger.info(f"Pending:          [yellow]{stats['pending']}[/yellow]")
    logger.info(f"Failed:           [red]{stats['failed']}[/red]")


async def cmd_test(args):
    """Test scrape a single product end-to-end."""
    from scraper.detail_scraper import DetailScraper
    from scraper.media_downloader import MediaDownloader
    from output.csv_generator import append_to_csv
    from output.folder_generator import save_product_metadata, print_output_summary

    url = args.url
    if not url:
        logger.error("Please provide a product URL with --url")
        return

    logger.info("[bold cyan]═══ TEST MODE: Single Product ═══[/bold cyan]")
    logger.info(f"URL: {url}")

    scraper = DetailScraper()
    try:
        product_data = await scraper.scrape_product(url)
    finally:
        await scraper.close()

    if product_data.get("error"):
        logger.error(f"Scraping failed: {product_data['error']}")
        return

    downloader = MediaDownloader()
    try:
        product_data = await downloader.download_product_media(product_data)
    finally:
        await downloader.close()

    save_product_metadata(product_data)
    
    csv_path = config.OUTPUT_DIR / "test_product.csv"
    if csv_path.exists():
        csv_path.unlink()
    append_to_csv(product_data, csv_path)

    print_output_summary()


async def cmd_scrape(args):
    """Run the batch scraping pipeline with SQLite tracking."""
    from scraper.detail_scraper import DetailScraper
    from scraper.media_downloader import MediaDownloader
    from output.csv_generator import append_to_csv
    from output.folder_generator import save_product_metadata, print_output_summary

    logger.info("[bold cyan]═══ BATCH SCRAPE MODE ═══[/bold cyan]")
    
    tracker = ProgressTracker()
    
    # Check if we have URLs
    stats = tracker.get_stats()
    if stats['total'] == 0:
        logger.error("No products in database! Run 'python main.py discover' first.")
        return
        
    logger.info(f"Database contains {stats['total']} products. {stats['pending']} pending.")

    scraper = DetailScraper()
    downloader = MediaDownloader()

    try:
        while True:
            # Get next batch
            batch_urls = tracker.get_pending_batch(config.BATCH_SIZE)
            if not batch_urls:
                logger.info("[bold green]All products completed![/bold green]")
                break
                
            logger.info(f"\n[bold magenta]Starting batch of {len(batch_urls)} products...[/bold magenta]")
            
            for i, url in enumerate(batch_urls):
                logger.info(f"\n[bold][{i+1}/{len(batch_urls)}][/bold] Scraping: {url}")
                
                try:
                    product_data = await scraper.scrape_product(url)
                    if product_data.get("error"):
                        raise Exception(product_data["error"])

                    product_data = await downloader.download_product_media(product_data)
                    save_product_metadata(product_data)
                    append_to_csv(product_data)
                    
                    tracker.mark_status(url, "COMPLETED", product_data.get("product_id"))
                    
                except Exception as e:
                    logger.error(f"[red]✗[/red] Failed: {url} — {e}")
                    tracker.mark_status(url, "FAILED")

                # Throttle between products
                delay = config.get_random_delay()
                logger.debug(f"Waiting {delay:.1f}s...")
                await asyncio.sleep(delay)
                
            # Cooldown after batch if more remain
            if len(batch_urls) == config.BATCH_SIZE:
                logger.info(f"\n[bold yellow]Batch finished. Cooling down for {config.BATCH_COOLDOWN}s...[/bold yellow]")
                await asyncio.sleep(config.BATCH_COOLDOWN)

    finally:
        await scraper.close()
        await downloader.close()
        cmd_status(None)
        print_output_summary()


async def cmd_csv(args):
    """Regenerate CSV from existing product folders."""
    from output.csv_generator import generate_csv

    logger.info("[bold cyan]═══ CSV GENERATION MODE ═══[/bold cyan]")
    products = []
    
    for product_dir in sorted(config.OUTPUT_DIR.iterdir()):
        if not product_dir.is_dir() or not product_dir.name.startswith("product_"):
            continue

        metadata_file = product_dir / "product_data.json"
        if metadata_file.exists():
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            products.append(data)

    if products:
        generate_csv(products)
    else:
        logger.warning("No product data found in output directory!")


async def cmd_summary(args):
    """Show output directory summary."""
    from output.folder_generator import print_output_summary
    print_output_summary()


def main():
    parser = argparse.ArgumentParser(
        description="JamesAllen.com Engagement Rings Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # discover
    discover_parser = subparsers.add_parser("discover", help="Interactive URL discovery")
    discover_parser.add_argument("--target", type=str, default="https://www.jamesallen.com/engagement-rings/", help="Target URL")

    # status
    subparsers.add_parser("status", help="Show progress dashboard")

    # test
    test_parser = subparsers.add_parser("test", help="Test scrape a single product")
    test_parser.add_argument("--url", type=str, required=True, help="Product URL to test")

    # scrape
    subparsers.add_parser("scrape", help="Batch scrape all rings")

    # csv & summary
    subparsers.add_parser("csv", help="Regenerate CSV from existing data")
    subparsers.add_parser("summary", help="Show output summary")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "discover": cmd_discover,
        "status": cmd_status,
        "test": cmd_test,
        "scrape": cmd_scrape,
        "csv": cmd_csv,
        "summary": cmd_summary,
    }

    asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    main()
