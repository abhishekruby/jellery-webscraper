import asyncio
from utils.browser import create_browser

async def main():
    playwright, browser, context, page = await create_browser()
    await page.goto("https://www.jamesallen.com/engagement-rings/custom-engagement-rings/solitaire-engagement-ring-embellished-with-a-four-prong-signature-head-item-126429")
    await page.wait_for_timeout(10000)
    html = await page.content()
    with open("page_html_stealth.html", "w") as f:
        f.write(html)
    print("Done")
    await browser.close()
    await playwright.stop()

asyncio.run(main())
