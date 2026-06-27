from flask import Flask, request, jsonify
import asyncio
import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from protobuf_decoder.protobuf_decoder import Parser
from google.protobuf.json_format import MessageToJson
import binascii
import requests
import json
import uid_generator_pb2
from google.protobuf.message import DecodeError
import os
import random
import urllib3
from datetime import datetime, timedelta
import pytz
import threading
import time
import subprocess
import html
from protobuf import my_message_pb2
from VsTeam import *
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

def token_update_loop():
    while True:
        try:
            print(f"[{datetime.now(VN_TZ).strftime('%Y-%m-%d %H:%M:%S')}]")
            result = subprocess.run(
                ["python", "gettk.py"],
                capture_output=True,
                text=True
            )
            print(f"Hoàn Tất GetToken")
        except Exception as e:
            print(f"Lỗi GetToken: {e}")
        time.sleep(4 * 60 * 60)
threading.Thread(target=token_update_loop, daemon=True).start()

def load_tokensview():
    file_path = "view.txt"
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tokens = [line.strip() for line in f if line.strip()]
        if not tokens:
            return None
        return tokens
    except Exception as e:
        return None

def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encrypting message: {e}")
        return None

token_lock = threading.Lock()

async def send_visit_request_async(encrypted_uid, token, session):
    url = "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
    edata = bytes.fromhex(encrypted_uid)
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'Content-Type': "application/x-www-form-urlencoded",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "ob54"
    }
    try:
        async with session.post(url, data=edata, headers=headers) as response:
            if response.status == 200:
                return True
            return False
    except Exception:
        return False

async def run_multiple_visits(encrypted_uid):
    tokens = load_tokensview()
    if not tokens:
        return 0

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(2000):
            token = tokens[i % len(tokens)]
            tasks.append(send_visit_request_async(encrypted_uid, token, session))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        return success_count

def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena = 1
        return message.SerializeToString()
    except Exception as e:
        return None

def enc(uid):
    protobuf_data = create_protobuf(uid)
    return encrypt_message(protobuf_data) if protobuf_data else None

def get_request(encrypt):
    tokens = load_tokensview()
    if not tokens: return None
    random.shuffle(tokens)
    for token in tokens:
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
                'Connection': "Keep-Alive", 'Accept-Encoding': "gzip",
                'Content-Type': "application/x-www-form-urlencoded", 'Expect': "100-continue",
                'X-Unity-Version': "2018.4.11f1", 'X-GA': "v1 1", 'ReleaseVersion': "ob54"
            }
            r = requests.post("https://clientbp.ggpolarbear.com/GetPlayerPersonalShow", 
                              data=bytes.fromhex(encrypt), headers=headers, verify=False, timeout=10)
            if r.status_code == 200: 
                return VsTeam().parsed_results_to_dict(Parser().parse(r.content.hex()))
        except Exception: continue
    return None

@app.route('/visit', methods=['GET'])
def handle_visit():
    try:
        uid = request.args.get("uid")

        if not uid:
            return app.response_class(
                response=json.dumps(
                    {"status": 3, "message": "Bro, please enter your UID!!"},
                    ensure_ascii=False, indent=2
                ),
                mimetype="application/json"
            ), 400
            
        if not uid.isdigit() or not (8 <= len(uid) <= 13):
            return app.response_class(
                response=json.dumps(
                    {"status": 3, "message": "Are you kidding me? The UID must contain between 8 and 13 digits!"},
                    ensure_ascii=False, indent=2
                ),
                mimetype="application/json"
            ), 400
        encrypted_uid = enc(uid)
        if not encrypted_uid:
            return app.response_class(
                response=json.dumps(
                    {"status": 3, "message": "Encryption Failed"},
                    ensure_ascii=False, indent=2
                ),
                mimetype="application/json"
            ), 500
        
        resp_info = get_request(encrypted_uid)
        player_name = "Unknown"
        level = "Unknown"
        region = "Unknown"
        
        if resp_info:
             player_name = str(resp_info.get(1, {}).get(3, 'Unknown'))
             level = str(resp_info.get(1, {}).get(6, 'Unknown'))
             region = str(resp_info.get(1, {}).get(5, 'Unknown'))
             
        start = time.time()
        success_count = asyncio.run(run_multiple_visits(encrypted_uid))
        end = time.time()
        
        response_data = {
            "status": 0,
            "message": "Visits Sent Successfully",
            "data": {
                "UID": uid,
                "Player Nickname": player_name,
                "Level": level,
                "Region": region,
                "Time Sent": f"{(end - start):.2f} sec",
                "Visits Sent": success_count,
                "Total Requests": 2000
            }
        }

        return app.response_class(
            response=json.dumps(
                response_data,
                ensure_ascii=False,
                indent=2
            ),
            mimetype="application/json"
        ), 200

    except Exception as e:
        app.logger.error(f"Visit Error: {e}")
        return app.response_class(
            response=json.dumps(
                {
                    "status": 3,
                    "error": "ALL",
                    "message": "Oh shit, an error occurred, please report it to TmrVirus immediately!!",
                    "telegram": "@TmrVirus"
                },
                ensure_ascii=False,
                indent=2
            ),
            mimetype="application/json"
        ), 500


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080, use_reloader=False)