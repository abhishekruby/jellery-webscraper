"""
Folder Generator for JamesAllen Scraper.
"""

import json
import logging
import shutil
from pathlib import Path
import config

logger = logging.getLogger("scraper")

def create_product_folder(product_id: str, output_dir: Path = None) -> dict:
    output_dir = output_dir or config.OUTPUT_DIR
    product_dir = output_dir / f"product_{product_id}"

    paths = {
        "root": product_dir,
        "images": product_dir / "images",
        "videos": product_dir / "videos",
        "360": product_dir / "360",
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths

def save_product_metadata(product_data: dict, output_dir: Path = None):
    output_dir = output_dir or config.OUTPUT_DIR
    product_id = product_data.get("product_id", "unknown")
    product_dir = output_dir / f"product_{product_id}"
    product_dir.mkdir(parents=True, exist_ok=True)

    clean_data = {
        k: v for k, v in product_data.items()
        if not k.startswith("_") and not isinstance(v, (bytes, list))
    }

    metadata_file = product_dir / "product_data.json"
    metadata_file.write_text(
        json.dumps(clean_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

def print_output_summary():
    logger.info("Output summary printed.")
