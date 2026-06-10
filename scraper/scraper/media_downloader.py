"""
Media Downloader for JamesAllen Scraper.

Handles async downloading of variant images and 3D WebGL assets
into the per-product folder structure.
"""

import asyncio
import logging
import re
import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
import aiofiles

import config
from utils.retry import retry

logger = logging.getLogger("scraper")

# JamesAllen Shapes and their codes
SHAPE_CODES = {
    'RND': 'Round',
    'OVL': 'Oval',
    'CSH': 'Cushion',
    'PRN': 'Princess',
    'EMR': 'Emerald',
    'RAD': 'Radiant',
    'MQS': 'Marquise',
    'PER': 'Pear',
    'HRT': 'Heart',
    'ASS': 'Asscher'
}

# Metal variants to check for Images
# James Allen uses Band_Prong color codes (W_W, Y_W, R_W).
METAL_CODES = [
    ('14K White Gold', 'W_W'),
    ('14K Yellow Gold', 'Y_W'),
    ('14K Rose Gold', 'R_W'),
    ('18K White Gold', 'W_W'),
    ('18K Yellow Gold', 'Y_W'),
    ('18K Rose Gold', 'R_W'),
    ('Platinum', 'W_W'),
]

class MediaDownloader:
    """Downloads and organizes media files for scraped products."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=60, connect=15)
            headers = {
                "User-Agent": config.get_random_user_agent(),
                "Accept": "image/webp,image/*,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.jamesallen.com/",
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session

    async def download_product_media(self, product_data: dict) -> dict:
        """
        Download all media for a single product and organize into folders.
        """
        product_id = product_data.get("product_id", "unknown")
        product_dir = self.output_dir / f"product_{product_id}"

        # Create directory structure
        images_dir = product_dir / "images"
        videos_dir = product_dir / "videos"
        rotation_dir = product_dir / "360"
        assets_dir = rotation_dir / "assets"

        images_dir.mkdir(parents=True, exist_ok=True)
        videos_dir.mkdir(parents=True, exist_ok=True)
        rotation_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)

        # 1. DOWNLOAD VARIANT IMAGES
        # Find the base SKU prefix from intercepted images to bruteforce variations
        base_prefix = None
        all_possible_urls = product_data.get("all_image_urls", "").split(" | ") + product_data.get("_all_intercepted_images", [])
        for url in all_possible_urls:
            if "BrioPackshot" in url and "Custom" in url:
                # https://ion.jamesallen.com/.../Custom/S01xH01/S01xH01_RND/S01xH01_M1_RND_DIM_...
                match = re.search(r'Custom/([^/]+)/', url)
                if match:
                    base_prefix = match.group(1)
                    break
        
        variant_image_paths = []
        found_variants = []

        if base_prefix:
            logger.info(f"  Discovered SKU Prefix: {base_prefix}. bruteforcing variants...")
            tasks = []
            
            async def check_and_download(shape_code, shape_name, metal_name, color_code):
                # Construct URL format: S01xH01_M1_RND_DIM_wht_0100CT_W_W.001.jpg
                for frame in range(1, 4):
                    url = f"https://ion.jamesallen.com/sets/Jewelry/Photoshoot/JamesAllen/BrioPackshot/Custom/{base_prefix}/{base_prefix}_{shape_code}/{base_prefix}_M1_{shape_code}_DIM_wht_0100CT_{color_code}/{base_prefix}_M1_{shape_code}_DIM_wht_0100CT_{color_code}.{frame:03d}.jpg"
                    
                    variant_dir = images_dir / shape_name / metal_name
                    filename = f"{shape_code}_{color_code}_{frame:03d}.jpg"
                    filepath = variant_dir / filename
                    
                    try:
                        session = await self._get_session()
                        async with session.head(url) as resp:
                            if resp.status == 200:
                                variant_dir.mkdir(parents=True, exist_ok=True)
                                res = await self._download_file(url, filepath)
                                if isinstance(res, Path):
                                    variant_image_paths.append(str(res.relative_to(self.output_dir)))
                                    if (shape_name, metal_name) not in found_variants:
                                        found_variants.append((shape_name, metal_name))
                    except Exception:
                        pass
            
            for shape_code, shape_name in SHAPE_CODES.items():
                for metal_name, color_code in METAL_CODES:
                    tasks.append(check_and_download(shape_code, shape_name, metal_name, color_code))
            
            await asyncio.gather(*tasks)
            logger.info(f"  Downloaded images for {len(found_variants)} shape/metal variations.")

        product_data["_found_variants"] = found_variants
        product_data["image_local_paths"] = " | ".join(variant_image_paths)

        # 2. DOWNLOAD 3D WEBGL ASSETS
        gltf_urls = product_data.get("_all_intercepted_3d_assets", [])
        if gltf_urls:
            logger.info(f"  Downloading {len(gltf_urls)} 3D WebGL assets...")
            for url in gltf_urls:
                filename = url.split("/")[-1].split("?")[0]
                filepath = assets_dir / filename
                await self._download_file(url, filepath)
            
            product_data["360_local_path"] = str(assets_dir.relative_to(self.output_dir))
            
            # Copy client 360 viewer scaffold if it exists locally
            client_360_dir = Path("/home/abhishek/Downloads/product/360")
            if client_360_dir.exists():
                logger.info("  Copying client custom 360 viewer HTML/JS...")
                for item in client_360_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, rotation_dir / item.name)
                    elif item.is_dir() and item.name == "draco":
                        dst = rotation_dir / "draco"
                        if not dst.exists():
                            shutil.copytree(item, dst)
                    elif item.is_dir() and item.name == "assets":
                        dst = rotation_dir / "assets"
                        dst.mkdir(parents=True, exist_ok=True)
                        for asset_file in item.iterdir():
                            if asset_file.is_file() and not asset_file.name.startswith("Ring_"):
                                shutil.copy2(asset_file, dst / asset_file.name)
                
                # Write asset_list.json so main.js knows what components exist
                assets_out = rotation_dir / "assets"
                if assets_out.exists():
                    import json
                    downloaded_assets = [f.name for f in assets_out.iterdir() if f.is_file()]
                    with open(assets_out / "asset_list.json", "w") as f:
                        json.dump(downloaded_assets, f)

        else:
            product_data["360_local_path"] = ""

        # 3. DOWNLOAD VIDEOS
        video_urls = product_data.get("video_url", "").split(" | ")
        video_urls = [u.strip() for u in video_urls if u.strip()]
        intercepted_videos = product_data.get("_all_intercepted_videos", [])
        for url in intercepted_videos:
            if url not in video_urls:
                video_urls.append(url)

        video_paths = []
        if video_urls:
            logger.info(f"  Downloading {len(video_urls)} videos...")
            for i, url in enumerate(video_urls):
                ext = self._get_extension(url, default=".mp4")
                filename = f"video_{i+1:03d}{ext}"
                filepath = videos_dir / filename
                result = await self._download_file(url, filepath)
                if isinstance(result, Path):
                    video_paths.append(str(result.relative_to(self.output_dir)))

        product_data["video_local_path"] = " | ".join(video_paths)
        return product_data

    async def _download_file(self, url: str, filepath: Path) -> Path | Exception:
        """Download a single file."""
        if filepath.exists() and filepath.stat().st_size > 0:
            return filepath

        try:
            session = await self._get_session()
            async with self.semaphore:
                async with session.get(url) as response:
                    response.raise_for_status()
                    async with aiofiles.open(filepath, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
            return filepath
        except Exception as e:
            return e

    def _get_extension(self, url: str, default: str) -> str:
        """Extract file extension from URL."""
        path = urlparse(url).path
        ext = Path(path).suffix.lower()
        if not ext or len(ext) > 5:
            return default
        return ext

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

