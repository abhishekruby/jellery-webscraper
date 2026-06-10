import urllib.request
import time

shapes = ['RND', 'OVL', 'CSH', 'PRN', 'PRNC', 'EMR', 'RAD', 'MQS', 'PER', 'HRT', 'ASS']
metals = [
    ('14K White Gold', 'W_W', 'w14'),
    ('14K Yellow Gold', 'Y_W', 'y14'),
    ('14K Rose Gold', 'R_W', 'r14'),
    ('18K White Gold', 'W_W', 'w18'), # wait, how does image path differ for 18k vs 14k white gold?
    ('18K Yellow Gold', 'Y_W', 'y18'),
    ('Platinum', 'W_W', 'plt'),
]

# Wait, in the client's zip, 14K White Gold and 18K White Gold have DIFFERENT images?
# Actually, the client zip had:
# 14K White Gold: 17346_M1_RND_DIM_wht_0100CT_W_Box2_001_1600X1600.jpg
# 18K White Gold: 17346_M1_RND_DIM_wht_0100CT_W_Box2_003_1600X1600.jpg (Wait, the frame number changed from Box2_001 to Box2_003, probably just a random download choice).
# But James Allen CDN only distinguishes between Band Color (W, Y, R, P for Platinum?) and Prong Color (W).
# W_W means White band, White prong. Y_W means Yellow band, White prong.

def check_url(shape, band_color, prong_color):
    url = f"https://ion.jamesallen.com/sets/Jewelry/Photoshoot/JamesAllen/BrioPackshot/Custom/S01xH01/S01xH01_{shape}/S01xH01_M1_{shape}_DIM_wht_0100CT_{band_color}_{prong_color}/S01xH01_M1_{shape}_DIM_wht_0100CT_{band_color}_{prong_color}.001.jpg"
    try:
        req = urllib.request.Request(url, method='HEAD')
        resp = urllib.request.urlopen(req)
        return True
    except:
        return False

found = []
for shape in shapes:
    for bc in ['W', 'Y', 'R', 'P']:
        for pc in ['W', 'Y', 'R', 'P']:
            if check_url(shape, bc, pc):
                print(f"Found: {shape} / {bc}_{pc}")
                found.append((shape, bc, pc))
                time.sleep(0.1)

print(f"Total found: {len(found)}")
