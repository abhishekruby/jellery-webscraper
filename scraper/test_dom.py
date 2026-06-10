import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        await page.goto("https://www.jamesallen.com/engagement-rings/custom-engagement-rings/solitaire-engagement-ring-embellished-with-a-four-prong-signature-head-item-126429")
        await page.wait_for_timeout(5000)
        html = await page.content()
        with open("page_html.html", "w") as f:
            f.write(html)
        print("Done")
        await browser.close()

asyncio.run(main())
