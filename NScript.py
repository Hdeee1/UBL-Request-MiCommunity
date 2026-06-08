import subprocess
import sys
import os
import platform

# Server lists
ntp_servers = [
"ntp.aliyun.com", # Alibaba Cloud
"ntp.tencent.com", # Tencent Cloud
"cn.pool.ntp.org", # China NTP Pool
"edu.ntp.org.cn", # China Education Network
"time.apple.com", # Apple
"time.google.com", # Google
"pool.ntp.org" # Main NTP Pool
]

MI_SERVERS = ['161.117.96.161', '20.157.18.26']

# Installation of dependencies
def install_package(package):
    if os.name == 'nt':
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    else:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--break-system-packages"])

required_packages = ["requests", "ntplib", "pytz", "urllib3", "icmplib", "colorama", "linecache"]
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        print(f"Installing package {package}...")
        install_package(package)

os.system('cls' if os.name == 'nt' else 'clear')

import hashlib
import linecache
import random
import time
from datetime import datetime, timezone, timedelta
import ntplib
import pytz
import urllib3
import json
import statistics
from icmplib import ping
from colorama import init, Fore, Style
import threading
from concurrent.futures import ThreadPoolExecutor
import requests

# Color settings
init(autoreset=True)
col_g = Fore.GREEN #green
col_gb = Style.BRIGHT + Fore.GREEN #bright green
col_b = Fore.BLUE #blue
col_bb = Style.BRIGHT + Fore.BLUE #bright blue
col_y = Fore.YELLOW #yellow
col_yb = Style.BRIGHT + Fore.YELLOW #bright yellow
col_r = Fore.RED #red
col_rb = Style.BRIGHT + Fore.RED #bright red

# Version and token number
token_number = int(input(col_g + f"[Token row number]: " + Fore.RESET))
os.system('cls' if os.name == 'nt' else 'clear')
#token_number = 1
scriptversion = "ARU_FHL_v070425"

# Konfigurasi Baru
BURST_COUNT = 40  # Jumlah request per burst
RETRY_WINDOW = 5  # Tetap mencoba selama 5 detik setelah jam 00:00
XIAOMI_SERVER = '161.117.96.161'

# Variables globales
print(col_yb + f"{scriptversion}_token_#{token_number}:")
print (col_y + f"Checking account status" + Fore.RESET)
token = linecache.getline("token.txt" , token_number).strip ()
cookie_value = token

# Generates a unique device identifier
def generate_device_id():
    random_data = f"{random.random()}-{time.time()}"
    device_id = hashlib.sha1(random_data.encode('utf-8')).hexdigest().upper()
    return device_id

# Get the current Beijing time from NTP
def get_initial_beijing_time():
    client = ntplib.NTPClient()
    beijing_tz = pytz.timezone("Asia/Shanghai")
    for server in ntp_servers:
        try:
            print(col_y + f"\nGetting current time in Beijing" + Fore.RESET)
            response = client.request(server, version=3)
            ntp_time = datetime.fromtimestamp(response.tx_time, timezone.utc)
            beijing_time = ntp_time.astimezone(beijing_tz)
            print(col_g + f"[Time in Beijing]: " + Fore.RESET +  f"{beijing_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
            return beijing_time
        except Exception as e:
            print(f"Error connecting to {server}: {e}")
    print(f"Cant't connect with any server NTP.")
    return None

# Synchronize Beijing time
def get_synchronized_beijing_time(start_beijing_time, start_timestamp):
    elapsed = time.time() - start_timestamp
    current_time = start_beijing_time + timedelta(seconds=elapsed)
    return current_time

def get_network_latency():
    try:
        # Ping 4 kali untuk rata-rata RTT
        host = ping(XIAOMI_SERVER, count=4, interval=0.2)
        avg_rtt = host.avg_ms / 1000 # Convert ke detik
        print(col_g + f"[+] Rata-rata Latensi: {host.avg_ms:.2f}ms (Offset: {avg_rtt/2:.4f}s)" + Fore.RESET)
        return avg_rtt / 2
    except:
        return 0.1 # Default fallback 100ms

def send_apply_request(session, url, headers, data):
    try:
        start_node = time.perf_counter()
        resp = session.post(url, headers=headers, data=data, timeout=5)
        res_json = resp.json()
        code = res_json.get('code')
        
        if code == 0:
            print(col_g + f"[*] BERHASIL! | {res_json.get('message')}" + Fore.RESET)
            return True
        elif code == 3:
            print(col_y + f"[!] Kuota Habis (Code 3), mencoba lagi..." + Fore.RESET)
        else:
            print(col_r + f"[?] Server: {res_json.get('message')} (Code: {code})" + Fore.RESET)
    except Exception as e:
        pass
    return False

def start_burst(session, url, headers, data):
    print(col_yb + f"\n[!] MELEPASKAN {BURST_COUNT} REQUEST..." + Fore.RESET)
    with ThreadPoolExecutor(max_workers=BURST_COUNT) as executor:
        # Kirim massal secara simultan
        futures = [executor.submit(send_apply_request, session, url, headers, data) for _ in range(BURST_COUNT)]
        for f in futures:
            if f.result(): return True
    return False

# Check if account unlocking is possible via API
def check_unlock_status(session, cookie_value, device_id):
    try:
        url = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
        headers = {
            "Cookie": f"new_bbs_serviceToken={cookie_value};versionCode=500411;versionName=5.4.11;deviceId={device_id};"
        }
       
        response = session.make_request('GET', url, headers=headers)
        if response is None:
            print(f"[Error] Unlock status unavailable.")
            return False

        response_data = json.loads(response.data.decode('utf-8'))
        response.release_conn()

        if response_data.get("code") == 100004:
            print(f"[Error] Cookie expired, need an updated one.")
            input(f"Press Enter to close...")
            exit()

        data = response_data.get("data", {})
        is_pass = data.get("is_pass")
        button_state = data.get("button_state")
        deadline_format = data.get("deadline_format", "")

        if is_pass == 4:
            if button_state == 1:
                    print(col_g + f"[Account status]: " + Fore.RESET + f"It is possible to send the request..")
                    return True

            elif button_state == 2:
                print(col_g + f"[Account status]: " + Fore.RESET + f"Blocked to send requests until " f"{deadline_format} (Month/Day).")
                status_2 = (input(f"Continue (" + col_b + f"Yes/No" +Fore.RESET + f")?: ") )
                if (status_2 == 'y' or status_2 == 'Y' or status_2 == 'yes' or status_2 == 'Yes' or status_2 == 'YES'):
                    return True
                else:
                    input(f"Press Enter to close...")
                    exit()
            elif button_state == 3:
                print(col_g + f"[Account status]: " + Fore.RESET + f"The account was created less than 30 days ago..")
                status_3 = (input(f"Continue (" + col_b + f"Yes/No" +Fore.RESET + f")?: ") )
                if (status_3 == 'y' or status_3 == 'Y' or status_3 == 'yes' or status_3 == 'Yes' or status_3 == 'YES'):
                    return True
                else:
                    input(f"Press Enter to close...")
                    exit()
        elif is_pass == 1:
            print(col_g + f"[Account status]: " + Fore.RESET + f"The request was approved, unlocking is possible until " f"{deadline_format}.")
            input(f"Press Enter to close...")
            exit()
        else:
            print(col_g + f"[Account status]: " + Fore.RESET + f"Status unknown.")
            input(f"Press Enter to close...")
            exit()
    except Exception as e:
        print(f"[Status check error ] {e}")
        return False

# Container for working with HTTP requests
class HTTP11Session:
    def __init__(self):
        self.http = urllib3.PoolManager(
            maxsize=10,
            retries=True,
            timeout=urllib3.Timeout(connect=2.0, read=15.0),
            headers={}
        )

    def make_request(self, method, url, headers=None, body=None):
        try:
            request_headers = {}
            if headers:
                request_headers.update(headers)
                request_headers['Content-Type'] = 'application/json; charset=utf-8'
           
            if method == 'POST':
                if body is None:
                    body = '{"is_retry":true}'.encode('utf-8')
                request_headers['Content-Length'] = str(len(body))
                request_headers['Accept-Encoding'] = 'gzip, deflate, br'
                request_headers['User-Agent'] = 'okhttp/4.12.0'
                request_headers['Connection'] = 'keep-alive'
           
            response = self.http.request(
                method,
                url,
                headers=request_headers,
                body=body,
                preload_content=False
            )
           
            return response
        except Exception as e:
            print(f"[Network error] {e}")
            return None
 
def main():
       
    device_id = generate_device_id()
    session = HTTP11Session()

    if check_unlock_status(session, cookie_value, device_id):
        start_beijing_time = get_initial_beijing_time()
        if start_beijing_time is None:
            print(f"Failed to set start time. Press Enter to close...")
            input()
            exit()

        latency_offset = get_network_latency()
        
        next_day = start_beijing_time + timedelta(days=1)
        target_datetime = next_day.replace(hour=0, minute=0, second=0, microsecond=0)
        
        time_until_target = (target_datetime - start_beijing_time).total_seconds()
        
        start_perf = time.perf_counter()
        target_hit = start_perf + time_until_target
        
        print(col_y + f"\nRequest to unlock bootloader" + Fore.RESET)
        print (col_g + f"[Offset]: " + Fore.RESET + f"{latency_offset:.4f} s.")
        print(col_g + f"[Waiting until]: " + Fore.RESET + f"{target_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')} - Latency")
        print(f"Don't close this window...")
        
        while time.perf_counter() < (target_hit - latency_offset):
            remaining = (target_hit - latency_offset) - time.perf_counter()
            if remaining > 1:
                time.sleep(remaining - 0.5)
            else:
                time.sleep(0.001)  
                
        url = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
        req_headers = {
            "Cookie": f"new_bbs_serviceToken={cookie_value};versionCode=500411;versionName=5.4.11;deviceId={device_id};",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "XiaomiCommunity/5.4.11",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        data = '{"is_retry":true}'.encode('utf-8')
        
        req_session = requests.Session()
        
        end_time = time.perf_counter() + RETRY_WINDOW
        while time.perf_counter() < end_time:
            if start_burst(req_session, url, req_headers, data):
                check_unlock_status(session, cookie_value, device_id)
                break
            time.sleep(0.3)
            
        print(col_g + f"\n[*] Selesai mengirim burst request." + Fore.RESET)
        input(f"Press Enter to close...")

if __name__ == "__main__":
    main()