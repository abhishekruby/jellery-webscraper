import urllib.request

def check_url(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        resp = urllib.request.urlopen(req)
        print(f"OK: {url}")
    except Exception as e:
        print(f"Fail: {url} -> {e}")

check_url("https://ion.jamesallen.com/sets/Jewelry/Photoshoot/JamesAllen/BrioPackshot/Custom/S01xH01/S01xH01_PRNC/S01xH01_M1_PRNC_DIM_wht_0100CT_P_W/S01xH01_M1_PRNC_DIM_wht_0100CT_P_W.001.jpg")
check_url("https://ion.jamesallen.com/sets/Jewelry/Photoshoot/JamesAllen/BrioPackshot/Custom/S01xH01/S01xH01_CSH/S01xH01_M1_CSH_DIM_wht_0100CT_P_W/S01xH01_M1_CSH_DIM_wht_0100CT_P_W.001.jpg")
