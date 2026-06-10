"""
CSV Generator for JamesAllen Scraper.

Generates the master CSV file from scraped product data,
formatted for WordPress/WooCommerce import with Variable Products.
"""

import csv
import logging
from pathlib import Path

import config

logger = logging.getLogger("scraper")

EXPORT_COLUMNS = [
    "Type",
    "SKU",
    "Name",
    "Parent",
    "Description",
    "Regular price",
    "Categories",
    "Attribute 1 name",
    "Attribute 1 value(s)",
    "Attribute 1 visible",
    "Attribute 1 global",
    "Attribute 2 name",
    "Attribute 2 value(s)",
    "Attribute 2 visible",
    "Attribute 2 global",
    "Attribute 3 name",
    "Attribute 3 value(s)",
    "Attribute 3 visible",
    "Attribute 3 global",
    "Attribute 4 name",
    "Attribute 4 value(s)",
    "Attribute 4 visible",
    "Attribute 4 global",
    "Images",
    "360_Viewer_Path",
    "Video_Path"
]

def _clean_text(text):
    if not isinstance(text, str):
        return ""
    text = " ".join(text.split())
    return text.replace("\r\n", " ").replace("\n", " ")

def _process_product_variations(product):
    """Convert a single product dict into a list of WooCommerce rows (Parent + Variations)"""
    rows = []
    parent_sku = product.get("sku", "")
    
    # 1. Parent Row
    description = _clean_text(product.get("description", ""))
    
    # Add shortcode to description
    if description:
        description += "\n\n[ring_360]"
    else:
        description = "[ring_360]"
    
    parent_image = _clean_text(product.get("image_main_url", ""))
    if parent_image:
        filename = parent_image.split("/")[-1]
        parent_image = f"http://localhost:8000/wp-content/uploads/raw_images/{filename}"

    parent_row = {
        "Type": "variable",
        "SKU": parent_sku,
        "Name": _clean_text(product.get("product_name", "")),
        "Parent": "",
        "Description": description,
        "Regular price": _clean_text(product.get("base_price", "")),
        "Categories": _clean_text(product.get("category", "")),
        "Attribute 1 name": "Shape",
        "Attribute 1 value(s)": "Round, Oval, Cushion, Princess, Emerald, Radiant, Marquise, Pear, Heart, Asscher",
        "Attribute 1 visible": "1",
        "Attribute 1 global": "1",
        "Attribute 2 name": "Metal",
        "Attribute 2 value(s)": "14K White Gold, 14K Yellow Gold, 14K Rose Gold, 18K White Gold, 18K Yellow Gold, 18K Rose Gold, Platinum",
        "Attribute 2 visible": "1",
        "Attribute 2 global": "1",
        "Attribute 3 name": "Size",
        "Attribute 3 value(s)": _clean_text(product.get("ring_sizes", "")) or "3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0",
        "Attribute 3 visible": "1",
        "Attribute 3 global": "1",
        "Attribute 4 name": "Carat / Type",
        "Attribute 4 value(s)": _clean_text(product.get("carat", "")),
        "Attribute 4 visible": "1",
        "Attribute 4 global": "1",
        "Images": parent_image,
        "360_Viewer_Path": _clean_text(product.get("360_local_path", "")),
        "Video_Path": _clean_text(product.get("video_local_path", ""))
    }
    rows.append(parent_row)
    
    # 2. Variation Rows
    found_variants = product.get("_found_variants", [])
    
    if not found_variants:
        return rows

    # Map metal labels to their price column keys (must match detail_scraper._metal_to_column)
    METAL_PRICE_MAP = {
        "14K White Gold": "price_14k_white_gold",
        "14K Yellow Gold": "price_14k_yellow_gold",
        "14K Rose Gold": "price_14k_rose_gold",
        "18K White Gold": "price_18k_white_gold",
        "18K Yellow Gold": "price_18k_yellow_gold",
        "18K Rose Gold": "price_18k_rose_gold",
        "Platinum": "price_platinum",
    }
        
    for shape, metal in found_variants:
        # Look up the per-metal price, fall back to base_price
        price_key = METAL_PRICE_MAP.get(metal, "")
        price = product.get(price_key, "") if price_key else ""
        if not price:
            price = product.get("base_price", "")
            
        image_paths = product.get("image_local_paths", "")
        # Get just the filenames and construct absolute placeholder URLs
        variant_images = []
        for img in image_paths.split(" | "):
            img = img.replace("\\", "/")
            if f"images/{shape}/{metal}" in img:
                filename = img.split("/")[-1]
                variant_images.append(f"http://localhost:8000/wp-content/uploads/raw_images/{filename}")
                
        variant_images_str = ", ".join(variant_images)
        
        var_row = {
            "Type": "variation",
            "SKU": f"{parent_sku}-{shape[:3]}-{metal.replace(' ', '')[:4]}",
            "Name": f"{parent_row['Name']} - {shape} - {metal}",
            "Parent": parent_sku,
            "Description": "",
            "Regular price": _clean_text(price),
            "Categories": "",
            "Attribute 1 name": "Shape",
            "Attribute 1 value(s)": shape,
            "Attribute 1 visible": "0",
            "Attribute 1 global": "1",
            "Attribute 2 name": "Metal",
            "Attribute 2 value(s)": metal,
            "Attribute 2 visible": "0",
            "Attribute 2 global": "1",
            "Attribute 3 name": "Size",
            "Attribute 3 value(s)": "",
            "Attribute 3 visible": "0",
            "Attribute 3 global": "1",
            "Attribute 4 name": "Carat / Type",
            "Attribute 4 value(s)": "",
            "Attribute 4 visible": "0",
            "Attribute 4 global": "1",
            "Images": variant_images_str,
            "360_Viewer_Path": "",
            "Video_Path": ""
        }
        rows.append(var_row)
        
    return rows

def generate_csv(products: list[dict], output_path: Path = None) -> Path:
    output_path = output_path or config.PRODUCTS_CSV_FILE
    if not products:
        logger.warning("No products to export!")
        return output_path
    all_rows = []
    for p in products:
        all_rows.extend(_process_product_variations(p))
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    logger.info(f"[bold green]CSV generated:[/bold green] {output_path}")
    logger.info(f"Total products (incl variations): {len(all_rows)}")
    return output_path

def append_to_csv(product: dict, output_path: Path = None):
    output_path = output_path or config.PRODUCTS_CSV_FILE
    file_exists = output_path.exists()
    rows = _process_product_variations(product)
    with open(output_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
