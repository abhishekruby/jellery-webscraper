"""
360° Frame Extractor for JamesAllen.com Products
=================================================
James Allen uses a WebGL-based real-time 3D viewer inside a cross-origin
iframe. There are NO individual .jpg frame files on the CDN to download.

The ONLY way to capture 360° frames is:
  1. Load the product page in a real browser
  2. Locate the 360° viewer element (the figure/iframe/canvas area)
  3. Simulate mouse drag to rotate the 3D model step by step
  4. Screenshot the viewer region at each rotation step
  5. Save as high-quality JPEGs

This produces 36-72 frames that can be stitched into a 360° viewer
on your WordPress/WooCommerce site.

Usage:
    python -m scraper.360_extractor --url "https://www.jamesallen.com/engagement-rings/..." 
    python -m scraper.360_extractor --url "..." --frames 72 --out "./my_output/360"
"""

import asyncio
import argparse
import re
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Missing playwright. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# ─── Configuration ─────────────────────────────────────────────────────────

DEFAULT_FRAMES = 36          # frames per full rotation (every 10°)
SCREENSHOT_QUALITY = 92      # JPEG quality (1-100)
VIEWER_LOAD_WAIT = 6         # seconds to wait for 3D model to render
ROTATION_STEP_DELAY = 0.20   # seconds between each drag step
POST_DRAG_SETTLE = 0.15      # seconds to let the model settle after each step
DRAG_SPEED_PX = 5            # pixels per mouse.move micro-step (slower = smoother)
MIN_VALID_FRAME_SIZE = 15000 # bytes — real 3D content > 15KB; error msg ~ 8KB


def product_id_from_url(url: str) -> str:
    """Extract item ID from a JamesAllen product URL."""
    m = re.search(r"item-(\d+)", url)
    return m.group(1) if m else "unknown"


def default_output_dir(url: str) -> Path:
    pid = product_id_from_url(url)
    return Path(f"output/product_{pid}/360")


# ─── Browser Setup ─────────────────────────────────────────────────────────

async def create_stealth_browser(headless: bool = True):
    """Launch a stealth Chromium browser that avoids bot detection."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-web-security",      # helps with cross-origin iframe access
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        bypass_csp=True,
    )
    # Mask automation indicators
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = { runtime: {} };
    """)
    page = await context.new_page()
    return pw, browser, context, page


# ─── Viewer Detection ──────────────────────────────────────────────────────

async def find_360_viewer(page) -> dict | None:
    """
    Find the 360° viewer element on the page.
    Returns bounding box dict or None.
    """
    # Strategy 1: Look for the figure element containing "360°" text
    viewer_info = await page.evaluate("""
        () => {
            // Look for figure elements (JamesAllen wraps the viewer in <figure>)
            const figures = document.querySelectorAll('figure');
            for (const fig of figures) {
                const text = fig.textContent || '';
                if (text.includes('360') || text.includes('SPIN') || text.includes('DRAG')) {
                    const rect = fig.getBoundingClientRect();
                    if (rect.width > 100 && rect.height > 100) {
                        return {
                            selector: 'figure',
                            x: rect.x, y: rect.y,
                            width: rect.width, height: rect.height,
                            found_via: '360-figure'
                        };
                    }
                }
            }
            
            // Look for canvas elements (WebGL renderer)
            const canvases = document.querySelectorAll('canvas');
            for (const c of canvases) {
                const rect = c.getBoundingClientRect();
                if (rect.width > 200 && rect.height > 200) {
                    return {
                        selector: 'canvas',
                        x: rect.x, y: rect.y,
                        width: rect.width, height: rect.height,
                        found_via: 'canvas'
                    };
                }
            }
            
            // Look for iframes that might contain the viewer
            const iframes = document.querySelectorAll('iframe');
            for (const f of iframes) {
                const rect = f.getBoundingClientRect();
                if (rect.width > 200 && rect.height > 200) {
                    return {
                        selector: 'iframe',
                        x: rect.x, y: rect.y,
                        width: rect.width, height: rect.height,
                        found_via: 'iframe'
                    };
                }
            }
            
            // Fallback: any element with 360/viewer/spin class
            const selectors = [
                '[class*="360"]', '[class*="viewer"]', '[class*="Viewer"]',
                '[class*="spin"]', '[class*="Spin"]', '[class*="rotate"]',
                '[class*="ThreeSixty"]', '[class*="three-sixty"]',
                '[id*="360"]', '[id*="viewer"]',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 200 && rect.height > 200) {
                        return {
                            selector: sel,
                            x: rect.x, y: rect.y,
                            width: rect.width, height: rect.height,
                            found_via: 'class-match'
                        };
                    }
                }
            }
            
            return null;
        }
    """)
    return viewer_info


# ─── 360° Capture ──────────────────────────────────────────────────────────

async def capture_360_frames(
    page,
    viewer_box: dict,
    num_frames: int = 36,
    output_dir: Path = None,
) -> list[Path]:
    """
    Rotate the 3D viewer by dragging and capture a screenshot at each step.
    
    The viewer responds to horizontal mouse drag. We drag across the full
    width of the viewer to complete one full 360° rotation, taking a
    screenshot at evenly-spaced intervals.
    
    Args:
        page: Playwright page
        viewer_box: {x, y, width, height} of the viewer element
        num_frames: Number of frames to capture
        output_dir: Where to save the frame images
        
    Returns:
        List of saved file paths
    """
    saved_frames = []
    
    # Calculate viewer center and drag parameters
    vx = viewer_box["x"]
    vy = viewer_box["y"]
    vw = viewer_box["width"]
    vh = viewer_box["height"]
    center_y = vy + vh / 2
    
    # We need to drag the full width multiple times to complete 360°
    # James Allen's viewer typically needs about 2x the viewer width
    # of total drag distance to complete a full rotation
    total_drag_distance = vw * 2.0
    step_distance = total_drag_distance / num_frames
    
    # Start position: left side of viewer
    start_x = vx + vw * 0.3
    current_x = start_x
    
    print(f"\n  Viewer: {vw:.0f}x{vh:.0f} at ({vx:.0f}, {vy:.0f})")
    print(f"  Capturing {num_frames} frames with {step_distance:.1f}px per step")
    print(f"  Total drag: {total_drag_distance:.0f}px")
    
    # First, click on the viewer to activate/focus it
    await page.mouse.click(vx + vw / 2, center_y)
    await asyncio.sleep(1)
    
    # Hide the overlay text (360° CLICK AND DRAG...) by clicking
    await page.mouse.click(vx + vw / 2, center_y)
    await asyncio.sleep(0.5)
    
    # Capture frame 1 BEFORE any rotation (the starting position)
    frame_path = output_dir / "frame_001.jpg"
    await page.screenshot(
        path=str(frame_path),
        clip={
            "x": max(0, vx + 2),      # small inset to avoid border
            "y": max(0, vy + 2),
            "width": vw - 4,
            "height": vh - 4,
        },
        type="jpeg",
        quality=SCREENSHOT_QUALITY,
    )
    
    # Validate first frame — reject if it's just the error message
    frame_size = frame_path.stat().st_size
    if frame_size < MIN_VALID_FRAME_SIZE:
        print(f"  ❌ Frame 1 is only {frame_size} bytes (threshold: {MIN_VALID_FRAME_SIZE}).")
        print(f"     This likely means the viewer is showing an error message.")
        print(f"     Skipping 360° capture for this product.")
        frame_path.unlink()  # delete the bad frame
        return saved_frames
    
    saved_frames.append(frame_path)
    print(f"  Frame 001/{num_frames:03d} captured (starting position, {frame_size} bytes — valid)")
    
    # Now drag to rotate and capture remaining frames
    await page.mouse.move(start_x, center_y)
    await page.mouse.down()
    await asyncio.sleep(0.1)
    
    for i in range(1, num_frames):
        frame_num = i + 1
        
        # Move mouse by step_distance pixels to the right
        target_x = start_x + (step_distance * i)
        
        # Smooth drag: move in small increments to simulate human
        steps = max(3, int(step_distance / DRAG_SPEED_PX))
        dx_per_step = step_distance / steps
        for s in range(steps):
            current_x += dx_per_step
            await page.mouse.move(current_x, center_y)
            await asyncio.sleep(0.01)  # tiny delay for smooth drag
        
        # Wait for the 3D model to settle after rotation
        await asyncio.sleep(POST_DRAG_SETTLE)
        
        # Release and re-press if we've moved too far (re-anchor)
        if current_x > vx + vw * 0.9:
            await page.mouse.up()
            await asyncio.sleep(0.1)
            current_x = start_x
            await page.mouse.move(current_x, center_y)
            await page.mouse.down()
            await asyncio.sleep(0.1)
        
        # Capture frame
        frame_path = output_dir / f"frame_{frame_num:03d}.jpg"
        await page.screenshot(
            path=str(frame_path),
            clip={
                "x": max(0, vx + 2),
                "y": max(0, vy + 2),
                "width": vw - 4,
                "height": vh - 4,
            },
            type="jpeg",
            quality=SCREENSHOT_QUALITY,
        )
        saved_frames.append(frame_path)
        
        if frame_num % 6 == 0 or frame_num == num_frames:
            print(f"  Frame {frame_num:03d}/{num_frames:03d} captured")
    
    await page.mouse.up()
    return saved_frames


# ─── Integration Function (for main scraper) ──────────────────────────────

async def extract_360_for_product(
    page,
    product_url: str,
    output_dir: Path,
    num_frames: int = 36,
) -> list[Path]:
    """
    High-level function to extract 360° frames from a product page.
    Used by the main scraper pipeline.
    
    Args:
        page: An already-navigated Playwright page on the product URL
        product_url: The product URL (for logging)
        output_dir: Directory to save frames into
        num_frames: Number of frames to capture
        
    Returns:
        List of saved frame paths (empty if viewer not found or error)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for "Media Not Available" error — main page
    page_text = await page.evaluate("document.body.innerText")
    if page_text and "Real Time Item Media Not Available" in page_text:
        print(f"  ⚠  360° media not available for this product")
        return []
    
    # Check inside iframes (error text is often in a cross-origin iframe)
    try:
        for frame in page.frames:
            try:
                frame_text = await frame.evaluate("document.body ? document.body.innerText : ''")
                if frame_text and "Real Time Item Media Not Available" in frame_text:
                    print(f"  ⚠  360° media not available (detected inside iframe)")
                    return []
            except Exception:
                pass
    except Exception:
        pass
    
    # Find the viewer
    viewer_box = await find_360_viewer(page)
    if not viewer_box:
        print(f"  ⚠  No 360° viewer found on page")
        return []
    
    print(f"  Found 360° viewer via: {viewer_box.get('found_via', 'unknown')}")
    
    # Wait for the 3D model to fully render
    print(f"  Waiting {VIEWER_LOAD_WAIT}s for 3D model to render...")
    await asyncio.sleep(VIEWER_LOAD_WAIT)
    
    # Capture frames
    frames = await capture_360_frames(page, viewer_box, num_frames, output_dir)
    return frames


# ─── Standalone CLI ────────────────────────────────────────────────────────

async def main(product_url: str, output_dir: Path, num_frames: int, headless: bool):
    """Standalone extraction: open browser → navigate → capture → close."""
    print("=" * 60)
    print("  James Allen — 360° Frame Extractor")
    print("=" * 60)
    print(f"  URL:     {product_url}")
    print(f"  Frames:  {num_frames}")
    print(f"  Output:  {output_dir.resolve()}")
    print(f"  Mode:    {'Headless' if headless else 'Visible (for debugging)'}")
    print("=" * 60)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Launch browser
    print("\n[1/4] Launching browser...")
    pw, browser, context, page = await create_stealth_browser(headless=headless)
    
    try:
        # Navigate to product page
        print("[2/4] Loading product page...")
        try:
            await page.goto(product_url, wait_until="load", timeout=60000)
        except Exception as e:
            print(f"  ⚠  Page load warning: {e}")
            print("  Continuing with partial load...")
        
        # Wait for dynamic content to render
        print(f"[3/4] Waiting for page to fully render ({VIEWER_LOAD_WAIT + 4}s)...")
        await asyncio.sleep(4)  # initial React hydration
        
        # Check for "Media Not Available" — main page text
        page_text = await page.evaluate("document.body.innerText")
        if "Real Time Item Media Not Available" in (page_text or ""):
            print("\n  ❌ 360° media is NOT available for this product.")
            print("     The site shows 'Real Time Item Media Not Available!'")
            return
        
        # Check inside iframes (error text is often in a cross-origin iframe)
        try:
            for frame in page.frames:
                try:
                    frame_text = await frame.evaluate("document.body ? document.body.innerText : ''")
                    if frame_text and "Real Time Item Media Not Available" in frame_text:
                        print("\n  ❌ 360° media not available (detected inside iframe).")
                        return
                except Exception:
                    pass
        except Exception:
            pass
        
        # Find the 360 viewer
        viewer_box = await find_360_viewer(page)
        if not viewer_box:
            print("\n  ❌ Could not find the 360° viewer element on this page.")
            print("     Possible reasons:")
            print("     - Bot detection blocked the viewer from loading")
            print("     - This product doesn't have a 360° view")
            print("     - The page layout has changed")
            
            # Take a debug screenshot
            debug_path = output_dir / "debug_page.png"
            await page.screenshot(path=str(debug_path), full_page=True)
            print(f"     Debug screenshot saved: {debug_path}")
            return
        
        print(f"  ✓ Viewer found via: {viewer_box.get('found_via')}")
        print(f"  ✓ Dimensions: {viewer_box['width']:.0f} x {viewer_box['height']:.0f}")
        
        # Wait for 3D model to fully render
        await asyncio.sleep(VIEWER_LOAD_WAIT)
        
        # Capture frames
        print(f"\n[4/4] Capturing {num_frames} rotation frames...")
        frames = await capture_360_frames(page, viewer_box, num_frames, output_dir)
        
        # Save metadata
        meta = {
            "product_url": product_url,
            "product_id": product_id_from_url(product_url),
            "frames_captured": len(frames),
            "viewer_type": viewer_box.get("found_via"),
            "viewer_dimensions": f"{viewer_box['width']:.0f}x{viewer_box['height']:.0f}",
            "capture_date": datetime.now().isoformat(),
            "frame_files": [f.name for f in frames],
        }
        meta_path = output_dir / "360_metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2))
        
        print("\n" + "=" * 60)
        print(f"  ✅ Done! {len(frames)} frames captured")
        print(f"  📁 Location: {output_dir.resolve()}")
        print(f"  📄 Files: frame_001.jpg to frame_{len(frames):03d}.jpg")
        print(f"  📋 Metadata: {meta_path.name}")
        print("=" * 60)
        
    finally:
        await browser.close()
        await pw.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="James Allen 360° Frame Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scraper.360_extractor --url "https://www.jamesallen.com/engagement-rings/..."
  python -m scraper.360_extractor --url "..." --frames 72
  python -m scraper.360_extractor --url "..." --out "./rings/126429/360" --visible
        """,
    )
    parser.add_argument(
        "--url", required=True,
        help="Product page URL",
    )
    parser.add_argument(
        "--frames", type=int, default=DEFAULT_FRAMES,
        help=f"Number of rotation frames to capture (default: {DEFAULT_FRAMES})",
    )
    parser.add_argument(
        "--out", default=None,
        help="Output directory (default: output/product_{item_id}/360)",
    )
    parser.add_argument(
        "--visible", action="store_true",
        help="Run in visible (non-headless) mode for debugging",
    )

    args = parser.parse_args()
    out_dir = Path(args.out) if args.out else default_output_dir(args.url)

    asyncio.run(main(args.url, out_dir, args.frames, headless=not args.visible))
