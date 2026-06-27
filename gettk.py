import asyncio
import aiohttp
import time
import os
import random
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import my_pb2
import output_pb2

class FreeFireTokenGetter:
    def __init__(self):
        self.aes_key = b'Yg&tc%DEuh6%Zc^8'
        self.aes_iv = b'6oyZDr22E3ychjM%'
        self.input_file = "accview.txt"
        self.output_file = "view.txt"
        self.max_workers = 10
        self.max_retries = 10
        self.models = ['SM-A125F','SM-A225F','SM-A325M','SM-A515F','SM-A725F','Redmi 9A','Redmi 9C','POCO M3','POCO M4 Pro','moto g(9) play']
        self.android_versions = ['9','10','11','12','13','14']
        self.versions = ['4.0.18P6','4.1.0P3','4.2.1P8','5.0.1B2','5.1.0P1','5.2.5P3','5.3.2P2','5.4.3B2','5.5.2P3']
        self.builds = {
            '9':['PKQ1.190616.001'],'10':['QP1A.190711.020'],'11':['RP1A.200720.011'],
            '12':['SP1A.210812.016'],'13':['TP1A.220624.014'],'14':['UP1A.231005.007']
        }
        self.langs = ['en-US','id-ID','vi-VN']

    def rand_ua_dalvik(self):
        m = random.choice(self.models)
        v = random.choice(self.android_versions)
        b = random.choice(self.builds.get(v, ['QP1A.190711.020']))
        return f"Dalvik/2.1.0 (Linux; U; Android {v}; {m} Build/{b})"

    def rand_ua_garena(self):
        return f"GarenaMSDK/{random.choice(self.versions)}({random.choice(self.models)};Android {random.choice(self.android_versions)};{random.choice(self.langs)};)"

    def encrypt(self, data):
        try:
            c = AES.new(self.aes_key, AES.MODE_CBC, self.aes_iv)
            return c.encrypt(pad(data, AES.block_size))
        except:
            return None

    async def get_oauth(self, session, uid, pwd):
        try:
            async with session.post(
                "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant",
                data={
                    "uid": uid, "password": pwd, "response_type": "token",
                    "client_type": "2", "client_id": "100067",
                    "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
                },
                headers={"User-Agent": self.rand_ua_garena()},
                timeout=10, ssl=False
            ) as r:
                if r.status == 200:
                    j = await r.json()
                    return j.get("access_token"), j.get("open_id")
        except:
            pass
        return None, None

    async def get_major_token(self, session, oauth, oid):
        if not oauth or not oid:
            return None
        gd = my_pb2.GameData()
        gd.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        gd.game_name = "free fire"
        gd.game_version = 1
        gd.version_code = random.choice(["1.108.3", "1.109.1", "1.110.0"])
        gd.os_info = f"Android OS {random.choice(['9','10','11','12'])} / API-{random.randint(28,34)}"
        gd.device_type = "Handheld"
        gd.network_provider = random.choice(["Verizon Wireless", "T-Mobile", "Viettel", "Mobifone"])
        gd.connection_type = random.choice(["WIFI", "4G"])
        gd.screen_width = random.choice([720, 1080, 1280])
        gd.screen_height = random.choice([1280, 1920, 2400])
        gd.dpi = random.choice(["240", "320", "480"])
        gd.cpu_info = random.choice([
            "ARMv7 VFPv3 NEON VMH | 2400 | 4",
            "ARMv8 | 2800 | 8",
            "Qualcomm | 2200 | 6"
        ])
        gd.total_ram = random.randint(3000, 8000)
        gd.gpu_name = random.choice(["Adreno (TM) 640", "Mali-G76", "PowerVR GE8320"])
        gd.open_id = oid
        gd.access_token = oauth
        gd.platform_type = 4
        gd.device_model = random.choice(self.models)
        gd.marketplace = "3rd_party"
        gd.encryption_key = "KqsHT2B4It60T/65PGR5PXwFxQkVjGNi+IMCK3CFBCBfrNpSUA1dZnjaT3HcYchlIFFL1ZJOg0cnulKCPGD3C3h1eFQ="
        gd.total_storage = 111107
        gd.field_97 = 1
        gd.field_98 = 1
        gd.field_99 = "4"
        gd.field_100 = "4"
        try:
            enc = self.encrypt(gd.SerializeToString())
            if not enc: return None
            async with session.post(
                "https://loginbp.ggblueshark.com/MajorLogin",
                data=enc,
                headers={
                    "User-Agent": self.rand_ua_dalvik(),
                    "Content-Type": "application/octet-stream",
                    "X-GA": "v1 1", "ReleaseVersion": "ob54"
                },
                timeout=12, ssl=False
            ) as r:
                if r.status == 200:
                    msg = output_pb2.Garena_420()
                    msg.ParseFromString(await r.read())
                    return msg.token if msg.token else None
        except:
            pass
        return None

    async def try_one(self, session, line):
        if ":" not in line: return None
        uid, pwd = line.strip().split(":", 1)
        for _ in range(self.max_retries):
            oauth, oid = await self.get_oauth(session, uid, pwd)
            if oauth and oid:
                token = await self.get_major_token(session, oauth, oid)
                if token:
                    print(f"[OK] {uid}")
                    return token
            await asyncio.sleep(random.uniform(1.8, 4.2))
        print(f"[X] {uid}")
        return None

    async def run(self):
        if not os.path.exists(self.input_file):
            print(f"Không thấy {self.input_file}")
            return
        with open(self.input_file, encoding="utf-8", errors="ignore") as f:
            accs = [l.strip() for l in f if ":" in l.strip()]
        if not accs:
            print("File rỗng")
            return
        print(f"Get {len(accs)} Acc...")
        connector = aiohttp.TCPConnector(limit=0, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            sem = asyncio.Semaphore(self.max_workers)
            async def bounded(acc):
                async with sem: return await self.try_one(s, acc)
            tasks = [bounded(a) for a in accs]
            tokens = [t for t in await asyncio.gather(*tasks, return_exceptions=True) if isinstance(t, str) and t]
        if tokens:
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(tokens) + "\n")
            print(f"Đã Lưu Vào {self.output_file}")
        else:
            print("Không File Token")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(FreeFireTokenGetter().run())
