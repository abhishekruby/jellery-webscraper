"""Debug: check if metal buttons exist in the DOM via stealth browser."""
import asyncio
from utils.browser import create_browser, safe_goto

async def main():
    pw, browser, context, page = await create_browser()
    await safe_goto(page, "https://www.jamesallen.com/engagement-rings/custom-engagement-rings/solitaire-engagement-ring-embellished-with-a-four-prong-signature-head-item-126429")
    await asyncio.sleep(6)

    # Scroll down gradually
    for i in range(5):
        await page.evaluate(f"window.scrollBy(0, 300)")
        await asyncio.sleep(1)

    # Check multiple selectors
    checks = [
        'button[data-qa*="metalColor"]',
        'ul[class*="metal"]',
        'li[class*="metal"]',
        'button[title*="Gold"]',
        'button[title*="Platinum"]',
        '[class*="metalColor"]',
        'button[name*="metal"]',
        'button[optiontype="metalColor"]',
    ]
    for sel in checks:
        count = await page.evaluate(f'document.querySelectorAll(\'{sel}\').length')
        if count > 0:
            # Get details
            details = await page.evaluate(f'''
                () => {{
                    const els = document.querySelectorAll('{sel}');
                    return Array.from(els).slice(0, 3).map(e => ({{
                        tag: e.tagName,
                        title: e.title || '',
                        qa: e.getAttribute('data-qa') || '',
                        disabled: e.disabled || false,
                        text: e.textContent?.trim()?.substring(0, 40) || ''
                    }}));
                }}
            ''')
            print(f"✓ {sel}: {count} found → {details}")
        else:
            print(f"✗ {sel}: 0 found")
    
    await browser.close()
    await pw.stop()

asyncio.run(main())
