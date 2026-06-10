"""
Central configuration for JamesAllen Ring Scraper.
All settings, paths, and constants in one place.
"""

import os
import random
from pathlib import Path

# ─── Base URLs ────────────────────────────────────────────────────────────────

BASE_URL = "https://www.jamesallen.com"
FINE_JEWELRY_RINGS_URL = f"{BASE_URL}/fine-jewelry/?ComponentIDs=Ring"

# ─── Output Paths ─────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
LOG_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Output files
PRODUCTS_INDEX_FILE = CHECKPOINT_DIR / "products_index.csv"
PRODUCTS_CSV_FILE = OUTPUT_DIR / "products.csv"
ERRORS_FILE = CHECKPOINT_DIR / "errors.csv"
DISCOVERY_REPORT_FILE = LOG_DIR / "api_discovery_report.txt"

# ─── Scraping Settings ───────────────────────────────────────────────────────

# Delay between page loads (seconds) — randomized to look human
MIN_PAGE_DELAY = 2.0
MAX_PAGE_DELAY = 5.0

# Batch Processing
BATCH_SIZE = 50
BATCH_COOLDOWN = 300  # 5 minutes

# Delay between variation clicks within a product page
MIN_CLICK_DELAY = 0.5
MAX_CLICK_DELAY = 1.5

# Max retries per page/request
MAX_RETRIES = 3

# Concurrent media downloads
MAX_CONCURRENT_DOWNLOADS = 10

# Timeout for page loads (milliseconds)
PAGE_TIMEOUT = 60000  # 60 seconds

# Timeout for element waits (milliseconds)
ELEMENT_TIMEOUT = 15000  # 15 seconds

# ─── Browser Settings ────────────────────────────────────────────────────────

# Viewport to emulate
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Headless mode (set False for debugging / CAPTCHA solving)
HEADLESS = False

# User-Agent rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# ─── Proxy Settings (Optional) ───────────────────────────────────────────────

# Set to None to disable proxy
# Format: "http://user:pass@host:port" or "socks5://user:pass@host:port"
PROXY_SERVER = None

# ─── 360° Capture Settings ───────────────────────────────────────────────────

# Number of horizontal frames per row during 360° rotation
ROTATION_FRAMES = 36  # One frame every 10 degrees

# Vertical tilt rows: fraction of viewer height to drag up(-) or down(+)
# Each row captures a full horizontal 360° rotation at that tilt angle.
#   -0.30 = tilted up (top-down view of the ring)
#    0.00 = eye-level (default straight-on view)
#   +0.30 = tilted down (bottom-up view, seeing inside the band)
VERTICAL_TILT_ROWS = [-0.30, 0.0, 0.30]

# Delay between rotation steps (seconds)
ROTATION_STEP_DELAY = 0.15

# Screenshot format for 360 frames
SCREENSHOT_FORMAT = "jpeg"
SCREENSHOT_QUALITY = 90

# ─── CSV Column Definitions ──────────────────────────────────────────────────

CSV_COLUMNS = [
    "product_id",
    "sku",
    "product_name",
    "category",
    "subcategory",
    "description",
    "base_price",
    "currency",
    "metal_type",
    "all_metal_options",
    "price_14k_white_gold",
    "price_14k_yellow_gold",
    "price_14k_rose_gold",
    "price_18k_white_gold",
    "price_18k_yellow_gold",
    "price_platinum",
    "stone_type",
    "carat",
    "stone_color",
    "stone_clarity",
    "ring_sizes",
    "ring_width",
    "ring_style",
    "image_main_url",
    "all_image_urls",
    "image_local_paths",
    "video_url",
    "video_local_path",
    "360_url",
    "360_local_path",
    "product_url",
    "scrape_date",
]

# ─── Metal Variations ────────────────────────────────────────────────────────

METAL_TYPES = [
    "14K White Gold",
    "14K Yellow Gold",
    "14K Rose Gold",
    "18K White Gold",
    "18K Yellow Gold",
    "Platinum",
]


def get_random_delay(min_delay=MIN_PAGE_DELAY, max_delay=MAX_PAGE_DELAY):
    """Return a random delay between min and max."""
    return random.uniform(min_delay, max_delay)


def get_random_user_agent():
    """Return a random User-Agent string."""
    return random.choice(USER_AGENTS)
