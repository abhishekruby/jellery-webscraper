import asyncio
import aiohttp

async def test_mqs():
    async with aiohttp.ClientSession() as session:
        url = "https://ion.jamesallen.com/sets/Jewelry/Photoshoot/JamesAllen/BrioPackshot/Custom/S02xH01/S02xH01_MQS/S02xH01_M1_MQS_DIM_wht_0100CT_W_W/S02xH01_M1_MQS_DIM_wht_0100CT_W_W.001.jpg"
        async with session.head(url) as resp:
            print(f"MQS M1 0100CT: {resp.status}")
        
        # Try without M1? Maybe MQS is MQ? Heart is HRT? Asscher is ASS?
        url2 = "https://ion.jamesallen.com/sets/Jewelry/Photoshoot/JamesAllen/BrioPackshot/Custom/S02xH01/S02xH01_MQ/S02xH01_M1_MQ_DIM_wht_0100CT_W_W/S02xH01_M1_MQ_DIM_wht_0100CT_W_W.001.jpg"
        async with session.head(url2) as resp:
            print(f"MQ: {resp.status}")
            
        url3 = "https://ion.jamesallen.com/sets/Jewelry/Photoshoot/JamesAllen/BrioPackshot/Custom/S02xH01/S02xH01_MAR/S02xH01_M1_MAR_DIM_wht_0100CT_W_W/S02xH01_M1_MAR_DIM_wht_0100CT_W_W.001.jpg"
        async with session.head(url3) as resp:
            print(f"MAR: {resp.status}")

        url4 = "https://ion.jamesallen.com/sets/Jewelry/Photoshoot/JamesAllen/BrioPackshot/Custom/S02xH01/S02xH01_MQS/S02xH01_M1_MQS_DIM_wht_0100CT_W_W/S02xH01_M1_MQS_DIM_wht_0100CT_W_W.001.jpg"
        async with session.head(url4) as resp:
            print(f"MQS: {resp.status}")

asyncio.run(test_mqs())
