import subprocess, sys, os, platform, hashlib, linecache, random, time, json, statistics, threading
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

def install_package(package):
    cmd = [sys.executable, "-m", "pip", "install", package]
    if os.name != 'nt':
        cmd.append("--break-system-packages")
    subprocess.check_call(cmd)

for pkg in ["requests", "ntplib", "pytz", "urllib3", "icmplib", "colorama"]:
    try:
        __import__(pkg)
    except ImportError:
        install_package(pkg)

os.system('cls' if os.name == 'nt' else 'clear')

import ntplib, pytz, urllib3, requests
from icmplib import ping
from colorama import init, Fore, Style

init(autoreset=True)
G  = Fore.GREEN
GB = Style.BRIGHT + Fore.GREEN
Y  = Fore.YELLOW
YB = Style.BRIGHT + Fore.YELLOW
R  = Fore.RED
RB = Style.BRIGHT + Fore.RED
B  = Fore.BLUE
RST = Fore.RESET

NTP_SERVERS = [
    "ntp.aliyun.com", "ntp.tencent.com", "cn.pool.ntp.org",
    "edu.ntp.org.cn", "time.apple.com", "time.google.com", "pool.ntp.org"
]
XIAOMI_SERVER    = '161.117.96.161'
BURST_COUNT      = 40
RETRY_WINDOW     = 5
SCRIPTVERSION    = "ARU_FHL_v070425"
TOKEN_FILE       = "token.txt"
STATUS_URL       = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
APPLY_URL        = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"


def generate_device_id() -> str:
    raw = f"{random.random()}-{time.time()}"
    return hashlib.sha1(raw.encode()).hexdigest().upper()


def load_token(line_number: int) -> str:
    token = linecache.getline(TOKEN_FILE, line_number).strip()
    if not token:
        print(RB + f"[!] Token baris {line_number} kosong atau file tidak ditemukan.")
        sys.exit(1)
    return token


def get_ntp_beijing_time():
    client = ntplib.NTPClient()
    tz = pytz.timezone("Asia/Shanghai")
    for server in NTP_SERVERS:
        try:
            print(Y + f"[NTP] Mencoba {server}..." + RST)
            resp = client.request(server, version=3)
            utc = datetime.fromtimestamp(resp.tx_time, timezone.utc)
            beijing = utc.astimezone(tz)
            print(G + f"[Beijing Time] {beijing.strftime('%Y-%m-%d %H:%M:%S.%f')}" + RST)
            return beijing
        except Exception as e:
            print(R + f"[NTP Error] {server}: {e}" + RST)
    return None


def measure_latency() -> float:
    """
    Coba ICMP ping dulu. Jika gagal (permission/block), fallback ke HTTP HEAD
    ke server Xiaomi untuk estimasi RTT.
    """
    try:
        host = ping(XIAOMI_SERVER, count=4, interval=0.2, privileged=False)
        if host.is_alive:
            rtt = host.avg_ms / 1000
            print(G + f"[Latency ICMP] {host.avg_ms:.2f}ms | Offset: {rtt/2:.4f}s" + RST)
            return rtt / 2
    except Exception:
        pass

    # HTTP RTT fallback
    try:
        samples = []
        s = requests.Session()
        for _ in range(4):
            t0 = time.perf_counter()
            s.head(f"http://{XIAOMI_SERVER}", timeout=3)
            samples.append(time.perf_counter() - t0)
            time.sleep(0.2)
        avg = statistics.mean(samples)
        print(Y + f"[Latency HTTP] {avg*1000:.2f}ms | Offset: {avg/2:.4f}s" + RST)
        return avg / 2
    except Exception:
        print(Y + "[Latency] Tidak bisa mengukur, pakai default 50ms" + RST)
        return 0.05  # 50ms lebih realistis dari 100ms


def build_headers(cookie_value: str, device_id: str) -> dict:
    return {
        "Cookie": f"new_bbs_serviceToken={cookie_value};versionCode=500411;versionName=5.4.11;deviceId={device_id};",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "XiaomiCommunity/5.4.11",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }


def check_unlock_status(cookie_value: str, device_id: str) -> bool:
    headers = build_headers(cookie_value, device_id)
    try:
        resp = requests.get(STATUS_URL, headers=headers, timeout=10)
        data = resp.json()

        if data.get("code") == 100004:
            print(RB + "[!] Cookie expired. Perbarui token." + RST)
            input("Tekan Enter untuk keluar...")
            sys.exit(1)

        d = data.get("data", {})
        is_pass = d.get("is_pass")
        button_state = d.get("button_state")
        deadline = d.get("deadline_format", "N/A")

        state_map = {
            1: (G, f"Request sudah diapprove. Unlock tersedia sampai {deadline}."),
        }

        if is_pass == 4:
            if button_state == 1:
                print(G + "[Status] Siap mengirim request." + RST)
                return True
            elif button_state == 2:
                print(Y + f"[Status] Diblokir sampai {deadline}." + RST)
                ans = input("Lanjutkan tetap? (yes/no): ").strip().lower()
                return ans in ('y', 'yes')
            elif button_state == 3:
                print(Y + "[Status] Akun < 30 hari." + RST)
                ans = input("Lanjutkan tetap? (yes/no): ").strip().lower()
                return ans in ('y', 'yes')
        elif is_pass == 1:
            print(G + f"[Status] Sudah diapprove sampai {deadline}." + RST)
            input("Tekan Enter untuk keluar...")
            sys.exit(0)
        else:
            print(Y + f"[Status] Unknown is_pass={is_pass}" + RST)

    except Exception as e:
        print(R + f"[Status Error] {e}" + RST)

    return False


def send_single_request(session: requests.Session, headers: dict, data: bytes, success_event: threading.Event) -> bool:
    if success_event.is_set():
        return False
    try:
        resp = session.post(APPLY_URL, headers=headers, data=data, timeout=5)
        result = resp.json()
        code = result.get('code')
        msg  = result.get('message', '')

        if code == 0:
            if not success_event.is_set():
                success_event.set()
                print(GB + f"[BERHASIL] {msg}" + RST)
            return True
        elif code == 3:
            print(Y + f"[Kuota Habis] Code 3, retry..." + RST)
        # code lain: diam saja, tidak spam output
    except Exception:
        pass
    return False


def run_burst(session: requests.Session, headers: dict, data: bytes) -> bool:
    print(YB + f"[!] Burst {BURST_COUNT} request simultan..." + RST)
    success_event = threading.Event()

    with ThreadPoolExecutor(max_workers=BURST_COUNT) as ex:
        futures = {
            ex.submit(send_single_request, session, headers, data, success_event)
            for _ in range(BURST_COUNT)
        }
        for f in as_completed(futures):
            if success_event.is_set():
                # Batalkan yang belum jalan (Python tidak bisa kill thread aktif,
                # tapi success_event akan membuat mereka skip logika utama)
                break

    return success_event.is_set()


def wait_until_target(target_perf: float, latency_offset: float):
    fire_at = target_perf - latency_offset
    while True:
        remaining = fire_at - time.perf_counter()
        if remaining <= 0:
            break
        elif remaining > 1.0:
            time.sleep(remaining - 0.5)
        elif remaining > 0.01:
            time.sleep(0.001)
        # busy-wait di bawah 10ms untuk akurasi maksimal


def main():
    try:
        token_number = int(input(G + "[Token row number]: " + RST))
    except ValueError:
        print(R + "Input tidak valid." + RST)
        sys.exit(1)

    os.system('cls' if os.name == 'nt' else 'clear')
    print(YB + f"{SCRIPTVERSION}_token_#{token_number}")

    cookie_value = load_token(token_number)
    device_id    = generate_device_id()

    if not check_unlock_status(cookie_value, device_id):
        sys.exit(0)

    beijing_time = get_ntp_beijing_time()
    if beijing_time is None:
        print(R + "Gagal mendapat waktu NTP." + RST)
        input()
        sys.exit(1)

    latency = measure_latency()
    mono_start = time.perf_counter()

    next_day = beijing_time + timedelta(days=1)
    target_dt = next_day.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_until = (target_dt - beijing_time).total_seconds()
    target_perf = mono_start + seconds_until

    headers = build_headers(cookie_value, device_id)
    data    = b'{"is_retry":true}'

    print(G + f"[Target Beijing] {target_dt.strftime('%Y-%m-%d %H:%M:%S')}" + RST)
    print(G + f"[Offset latensi] {latency:.4f}s" + RST)
    print(Y + "Jangan tutup window ini..." + RST)

    wait_until_target(target_perf, latency)

    session = requests.Session()
    end_time = time.perf_counter() + RETRY_WINDOW
    success = False

    while time.perf_counter() < end_time and not success:
        success = run_burst(session, headers, data)
        if not success:
            time.sleep(0.1)  # lebih cepat dari 0.3

    if success:
        print(G + "\n[*] Request berhasil. Cek status akun..." + RST)
        check_unlock_status(cookie_value, device_id)
    else:
        print(Y + "\n[*] Burst selesai tanpa konfirmasi sukses dari server." + RST)

    input("Tekan Enter untuk keluar...")


if __name__ == "__main__":
    main()
