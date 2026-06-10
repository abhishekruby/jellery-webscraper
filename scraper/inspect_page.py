"""Inspect the JamesAllen page to find correct selectors for product data."""
from bs4 import BeautifulSoup
import json
import re

with open("page_html.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# 1. Find all JSON-LD scripts
print("=" * 60)
print("JSON-LD DATA")
print("=" * 60)
ld_scripts = soup.find_all("script", type="application/ld+json")
for i, s in enumerate(ld_scripts):
    try:
        data = json.loads(s.string)
        print(f"\n--- JSON-LD [{i}] @type={data.get('@type', 'N/A')} ---")
        print(json.dumps(data, indent=2)[:2000])
    except:
        pass

# 2. Find __NEXT_DATA__ or similar app state
print("\n" + "=" * 60)
print("APP STATE / INLINE DATA")
print("=" * 60)
for s in soup.find_all("script"):
    txt = s.string or ""
    if len(txt) > 100:
        for pattern in ["__NEXT_DATA__", "__INITIAL_STATE__", "window.__data", 
                         "PRELOADED_STATE", "pageProps", "productData",
                         "JewelPageComponent", "ringData", "productInfo",
                         "metalOptions", "metalTypes", "settingPrice"]:
            if pattern in txt:
                print(f"\nFound '{pattern}' in script (length {len(txt)})")
                # Show a snippet around it
                idx = txt.find(pattern)
                snippet = txt[max(0,idx-50):idx+500]
                print(f"  Snippet: ...{snippet[:500]}...")
                break

# 3. Look for metal swatch elements
print("\n" + "=" * 60)
print("METAL / SWATCH ELEMENTS")
print("=" * 60)
# Search for anything related to metal in class names
for el in soup.find_all(attrs={"class": re.compile(r"metal|swatch|color-option|MetalOption", re.I)}):
    tag = el.name
    classes = el.get("class", [])
    aria = el.get("aria-label", "")
    title = el.get("title", "")
    text = el.get_text(strip=True)[:100]
    print(f"  <{tag}> class={' '.join(classes)} aria={aria} title={title} text={text[:60]}")

# 4. Look for price elements
print("\n" + "=" * 60)
print("PRICE ELEMENTS")
print("=" * 60)
for el in soup.find_all(attrs={"class": re.compile(r"price|Price", re.I)}):
    tag = el.name
    classes = el.get("class", [])
    text = el.get_text(strip=True)[:100]
    if text and "$" in text:
        print(f"  <{tag}> class={' '.join(classes)} text={text}")

# 5. Look for product title elements
print("\n" + "=" * 60)
print("TITLE / NAME ELEMENTS")
print("=" * 60)
for el in soup.find_all(attrs={"class": re.compile(r"product.?name|product.?title|ProductName|ProductTitle|ring.?name", re.I)}):
    tag = el.name
    classes = el.get("class", [])
    text = el.get_text(strip=True)[:200]
    print(f"  <{tag}> class={' '.join(classes)} text={text}")

