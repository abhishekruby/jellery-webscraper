import requests
import xml.etree.ElementTree as ET

def test_sitemap():
    url = 'https://www.jamesallen.com/sitemap.xml'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    print(f"Fetching {url}...")
    resp = requests.get(url, headers=headers)
    print("Status:", resp.status_code)
    
    if resp.status_code == 200:
        try:
            root = ET.fromstring(resp.text)
            print(f"Found {len(root)} sitemaps.")
            for child in root[:5]: # print first 5
                print(child[0].text)
        except Exception as e:
            print("Failed to parse XML:", e)
            print("Content start:", resp.text[:200])
    else:
        print("Response:", resp.text[:200])

if __name__ == '__main__':
    test_sitemap()
