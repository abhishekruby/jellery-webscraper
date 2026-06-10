"""
Playwright browser setup with stealth configuration.
Handles browser launch, context creation, and anti-bot measures.
"""

import asyncio
import logging
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

import config

logger = logging.getLogger("scraper")


async def create_browser(headless: Optional[bool] = None) -> tuple:
    """
    Launch a Playwright Chromium browser with stealth settings.

    Args:
        headless: Override config HEADLESS setting

    Returns:
        Tuple of (playwright_instance, browser, context, page)
    """
    is_headless = headless if headless is not None else config.HEADLESS
    user_agent = config.get_random_user_agent()

    logger.info(f"Launching browser (headless={is_headless})")
    logger.debug(f"User-Agent: {user_agent}")

    pw = await async_playwright().start()

    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--window-size=1920,1080",
        "--disable-extensions",
        # WebGL / GPU flags — required for 3D viewers
        "--enable-webgl",
        "--enable-webgl2",
        "--use-gl=angle",
        "--enable-gpu-rasterization",
        "--ignore-gpu-blocklist",
        "--enable-features=Vulkan",
        "--disable-software-rasterizer",
        # Cross-origin iframe access for 360° viewer
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
    ]

    launch_kwargs = {
        "headless": is_headless,
        "args": browser_args,
        "channel": "chrome",
    }

    # Add proxy if configured
    if config.PROXY_SERVER:
        launch_kwargs["proxy"] = {"server": config.PROXY_SERVER}
        logger.info(f"Using proxy: {config.PROXY_SERVER}")

    try:
        browser = await pw.chromium.launch(**launch_kwargs)
        logger.info("Launched system Chrome")
    except Exception as e:
        logger.warning(f"System Chrome not available ({e}), falling back to Chromium")
        launch_kwargs.pop("channel", None)
        browser = await pw.chromium.launch(**launch_kwargs)

    context = await browser.new_context(
        viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
        user_agent=user_agent,
        locale="en-US",
        timezone_id="America/New_York",
        bypass_csp=True,
        # Stealth: mask webdriver detection
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    )

    # Stealth: Override navigator.webdriver and other automation markers
    await context.add_init_script("""
        // Delete the webdriver property entirely
        delete Object.getPrototypeOf(navigator).webdriver;

        // Override chrome detection
        window.chrome = {
            runtime: { id: undefined },
            loadTimes: function() { return {}; },
            csi: function() { return {}; },
            app: { isInstalled: false, getDetails: function() {} },
        };

        // Override permissions query
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);

        // Override plugins — match real Chrome
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' },
                ];
                plugins.length = 3;
                return plugins;
            },
        });

        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });

        // Override platform
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
        });

        // Override hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
        });

        // Override WebGL vendor and renderer to look real
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Google Inc. (NVIDIA)';
            if (parameter === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)';
            return getParameter.call(this, parameter);
        };
    """)

    page = await context.new_page()

    # Set default timeouts
    page.set_default_timeout(config.PAGE_TIMEOUT)
    page.set_default_navigation_timeout(config.PAGE_TIMEOUT)

    logger.info("Browser ready")
    return pw, browser, context, page


async def safe_goto(page: Page, url: str, wait_until: str = "domcontentloaded") -> bool:
    """
    Navigate to a URL with error handling.

    Args:
        page: Playwright page
        url: URL to navigate to
        wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')

    Returns:
        True if navigation succeeded
    """
    try:
        response = await page.goto(url, wait_until=wait_until, timeout=config.PAGE_TIMEOUT)
        if response and response.status >= 400:
            logger.warning(f"HTTP {response.status} for {url}")
            return False
        return True
    except Exception as e:
        logger.error(f"Navigation failed for {url}: {e}")
        return False


async def wait_for_content(page: Page, selector: str, timeout: int = None) -> bool:
    """
    Wait for a specific element to appear on the page.

    Args:
        page: Playwright page
        selector: CSS selector to wait for
        timeout: Override default timeout (ms)

    Returns:
        True if element found
    """
    timeout = timeout or config.ELEMENT_TIMEOUT
    try:
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        return True
    except Exception:
        logger.warning(f"Element not found: {selector} (timeout: {timeout}ms)")
        return False


async def human_like_scroll(page: Page, scrolls: int = 3, delay: float = 0.5):
    """Simulate human-like scrolling behavior."""
    for _ in range(scrolls):
        await page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
        await asyncio.sleep(delay)


async def close_browser(pw, browser):
    """Safely close browser and playwright."""
    try:
        await browser.close()
        await pw.stop()
        logger.info("Browser closed")
    except Exception as e:
        logger.warning(f"Error closing browser: {e}")
