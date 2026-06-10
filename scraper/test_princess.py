import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Capture console messages
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
        
        await page.goto("http://localhost:8899/product_119325/360/index.html")
        await page.wait_for_timeout(2000)
        print("Page loaded, clicking Princess...")
        
        # Click princess button
        await page.evaluate("() => { document.querySelectorAll('.jv-shape')[3].click(); }")
        
        await page.wait_for_timeout(3000)
        print("Done.")
        await browser.close()

asyncio.run(main())
