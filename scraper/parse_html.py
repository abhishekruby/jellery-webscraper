from bs4 import BeautifulSoup
import json
import re

with open("page_html.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
title = soup.title.string if soup.title else "No title"
print(f"Title: {title}")

# Try to find json-ld
ld_json_scripts = soup.find_all("script", type="application/ld+json")
for i, script in enumerate(ld_json_scripts):
    try:
        data = json.loads(script.string)
        print(f"\n--- JSON-LD {i} ---")
        if "@type" in data and data["@type"] == "Product":
            print(f"Product Name: {data.get('name')}")
            print(f"Description: {data.get('description')}")
            print(f"Price: {data.get('offers', {}).get('price')}")
    except:
        pass

# Try to find next.js or similar state
scripts = soup.find_all("script")
for s in scripts:
    content = s.string
    if content and ("__INITIAL_STATE__" in content or "window.__data" in content or "PRELOADED_STATE" in content or "pageProps" in content):
        print(f"\n--- Found potential state script: length {len(content)} ---")
        # Extract json if possible
        match = re.search(r'({.*})', content, re.DOTALL)
        if match:
             print("Found json object inside script")
