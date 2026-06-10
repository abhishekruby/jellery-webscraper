import asyncio
from utils.browser import create_browser, safe_goto
from bs4 import BeautifulSoup
import json

async def main():
    pw, browser, context, page = await create_browser()
    await safe_goto(page, "https://www.jamesallen.com/engagement-rings/custom-engagement-rings/solitaire-engagement-ring-embellished-with-a-four-prong-signature-head-item-126429")
    await asyncio.sleep(5)
    content = await page.content()
    
    soup = BeautifulSoup(content, 'html.parser')
    for script in soup.find_all('script'):
        if script.string and 'window.__INITIAL_STATE__' in script.string:
            with open('state.js', 'w') as f:
                f.write(script.string)
                print("Found __INITIAL_STATE__")
        elif script.string and 'window.__APOLLO_STATE__' in script.string:
            with open('apollo.js', 'w') as f:
                f.write(script.string)
                print("Found __APOLLO_STATE__")
        elif script.string and 'product' in script.string.lower() and '{' in script.string:
            # might be another blob
            pass
            
    await browser.close()
    await pw.stop()

asyncio.run(main())
