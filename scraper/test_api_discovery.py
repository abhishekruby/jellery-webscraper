import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        api_responses = []
        
        async def handle_response(response):
            if "jamesallen.com" in response.url and ("api" in response.url or "graphql" in response.url or "products" in response.url or "search" in response.url):
                try:
                    if response.status == 200:
                        content_type = response.headers.get("content-type", "")
                        if "application/json" in content_type:
                            data = await response.json()
                            api_responses.append({
                                "url": response.url,
                                "data": str(data)[:500] # store preview
                            })
                            print(f"Captured JSON from: {response.url}")
                except Exception as e:
                    pass

        page.on("response", handle_response)
        
        print("Navigating to engagement rings...")
        await page.goto("https://www.jamesallen.com/engagement-rings/", wait_until="networkidle", timeout=30000)
        
        # Scroll down to trigger lazy loading / API calls
        await page.evaluate("window.scrollBy(0, 1000)")
        await asyncio.sleep(2)
        await page.evaluate("window.scrollBy(0, 2000)")
        await asyncio.sleep(2)
        
        with open("api_discovery_results.json", "w") as f:
            json.dump(api_responses, f, indent=2)
            
        print(f"Captured {len(api_responses)} API responses. Saved to api_discovery_results.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
