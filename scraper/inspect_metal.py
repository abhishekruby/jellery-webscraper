"""Inspect metal swatches in detail."""
from bs4 import BeautifulSoup
import re, json

with open("page_html.html", "r") as f:
    html = f.read()
soup = BeautifulSoup(html, "html.parser")

# Find the FIRST metal ul only (there are duplicate blocks)
metal_uls = soup.find_all("ul", class_=re.compile(r"metal"))
if metal_uls:
    ul = metal_uls[0]
    print("=== First metal <ul> ===")
    for i, li in enumerate(ul.find_all("li", recursive=False)):
        classes = " ".join(li.get("class", []))
        # Find inner elements
        inner = li.decode_contents()[:500]
        text = li.get_text(strip=True)
        # Check for color swatch div
        swatch = li.find(attrs={"class": re.compile(r"swatch|circle|color", re.I)})
        swatch_style = swatch.get("style", "") if swatch else ""
        print(f"\n  [{i}] text='{text}' classes={classes}")
        print(f"      swatch_style={swatch_style}")
        print(f"      inner_html={inner[:300]}")

# Find description area
print("\n\n=== DESCRIPTION / INFO AREA ===")
for el in soup.find_all(attrs={"class": re.compile(r"info-table|InfoTable|ringInfo|ring.?information|description", re.I)}):
    tag = el.name
    classes = " ".join(el.get("class", []))
    text = el.get_text(" | ", strip=True)[:300]
    print(f"  <{tag}> class={classes}")
    print(f"    text: {text}")

# Find gallery images specifically
print("\n\n=== GALLERY / PRODUCT IMAGES ===")
gallery_imgs = soup.find_all("img")
product_imgs = []
for img in gallery_imgs:
    src = img.get("src", "") or img.get("data-src", "")
    if "Photoshoot" in src or "BrioPackshot" in src:
        product_imgs.append(src)
        print(f"  PRODUCT IMG: {src}")
    elif "ion.jamesallen.com/sets" in src and "matcap" not in src and "panorama" not in src:
        print(f"  POSSIBLE: {src}")

print(f"\n  Total product images: {len(product_imgs)}")
