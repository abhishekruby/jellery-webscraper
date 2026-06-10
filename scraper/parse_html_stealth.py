from bs4 import BeautifulSoup
import json
import re

with open("page_html_stealth.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
title = soup.title.string if soup.title else "No title"
print(f"Title: {title}")

# Try to find json-ld
ld_json_scripts = soup.find_all("script", type="application/ld+json")
for i, script in enumerate(ld_json_scripts):
    try:
        data = json.loads(script.string)
        if "@type" in data and data["@type"] == "Product":
            print(f"\n--- JSON-LD Product ---")
            print(f"Product Name: {data.get('name')}")
            print(f"Description: {data.get('description')}")
            print(f"Price: {data.get('offers', {}).get('price')}")
            print(f"Material: {data.get('material')}")
    except:
        pass

# Try to find metal variation buttons or links
metal_elements = soup.select('div[class*="metal"], div[class*="Metal"], ul[class*="metal"] li')
print(f"\n--- Found {len(metal_elements)} potential metal elements ---")
for el in metal_elements[:10]:
    print(el.text.strip())

# Look for next data script
scripts = soup.find_all("script")
for s in scripts:
    content = s.string
    if content and "__NEXT_DATA__" in content:
        print("\n--- Found __NEXT_DATA__ script ---")
        try:
            data = json.loads(content)
            # Find pricing or variants in next data
            print("Next.js data keys:", data.keys())
        except:
            pass

