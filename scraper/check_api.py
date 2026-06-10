import asyncio
from utils.browser import create_browser, safe_goto

async def main():
    pw, browser, context, page = await create_browser()
    
    api_responses = {}
    
    async def on_response(response):
        url = response.url
        if "api" in url or "product" in url or "viewer" in url or "glb" in url or "gltf" in url or "json" in url:
            if "jamesallen" in url:
                try:
                    if response.headers.get("content-type", "").startswith("application/json"):
                        api_responses[url] = await response.json()
                except:
                    pass

    page.on("response", on_response)
    
    await safe_goto(page, "https://www.jamesallen.com/engagement-rings/custom-engagement-rings/solitaire-engagement-ring-embellished-with-a-four-prong-signature-head-item-126429")
    await asyncio.sleep(10)
    
    # Save the keys to see what we intercepted
    with open("intercepted_urls.txt", "w") as f:
        for url in api_responses.keys():
            f.write(url + "\n")
            
    await browser.close()
    await pw.stop()

asyncio.run(main())
