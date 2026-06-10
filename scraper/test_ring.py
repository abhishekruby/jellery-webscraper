import urllib.request
# try to see if a merged ring file exists
url = "https://ion.jamesallen.com/sets/Jewelry/JewelryViewer/3D_models/James_Allen/Rings/Ring_126429_JV_RND_100.gltf"
try:
    req = urllib.request.Request(url, method='HEAD')
    resp = urllib.request.urlopen(req)
    print("Found:", url)
except Exception as e:
    print("Not found:", e)
