import asyncio
import json
from utils.browser import create_browser, safe_goto

async def main():
    pw, browser, context, page = await create_browser()
    
    saved_data = {}
    
    async def on_response(response):
        url = response.url
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                data = await response.json()
                saved_data[url] = data
        except:
            pass

    page.on("response", on_response)
    
    await safe_goto(page, "https://www.jamesallen.com/engagement-rings/custom-engagement-rings/solitaire-engagement-ring-embellished-with-a-four-prong-signature-head-item-126429")
    await asyncio.sleep(10)
    
    # Save everything to a big json file
    with open("all_api_data.json", "w") as f:
        json.dump(saved_data, f, indent=2)
            
    await browser.close()
    await pw.stop()

asyncio.run(main())
