# Mi Community UBL Request Script

Script otomasi pengajuan Unlock Bootloader (UBL) ke server Xiaomi melalui Mi Community API resmi. Script ini membantu mengirim request tepat pada detik reset kuota (00:00 Beijing Time) dengan burst request simultan.

---

## Prasyarat

- Python 3.8 atau lebih baru
- Koneksi internet stabil
- Akun Mi Community yang sudah memenuhi syarat UBL Xiaomi
- Browser Firefox atau Chrome (untuk GetTokens.py)

---

## Instalasi Python

### Windows

1. Download installer dari [python.org](https://www.python.org/downloads/)
2. Centang **"Add Python to PATH"** saat instalasi
3. Verifikasi di Command Prompt:
   ```
   python --version
   ```

### Linux (Debian/Ubuntu/Mint)

```bash
sudo apt update
sudo apt install python3 python3-pip -y
python3 --version
```

### Linux (Arch/CachyOS/Manjaro)

```bash
sudo pacman -S python python-pip
python --version
```

### Linux (Fedora/RHEL)

```bash
sudo dnf install python3 python3-pip -y
python3 --version
```

---

## Instalasi Dependencies

Dependencies diinstall otomatis saat script pertama kali dijalankan. Tapi jika ingin install manual:

### Windows

```
pip install requests ntplib pytz urllib3 icmplib colorama selenium browser-cookie3
```

### Linux

```bash
pip install requests ntplib pytz urllib3 icmplib colorama selenium browser-cookie3 --break-system-packages
```

### Tambahan untuk GetTokens.py — ChromeDriver

GetTokens.py menggunakan Selenium dengan Chrome. Pastikan ChromeDriver terinstall dan versinya sesuai dengan Chrome yang terpasang.

**Windows:** Download dari [chromedriver.chromium.org](https://chromedriver.chromium.org/downloads), letakkan `chromedriver.exe` di folder yang sama dengan script atau tambahkan ke PATH.

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install chromium-driver -y

# Arch/CachyOS
sudo pacman -S chromedriver
```

---

## Struktur File

```
├── GetTokens.py     # Ambil token dari browser (jalankan pertama kali)
├── NScript.py       # Script utama burst request UBL
├── token.txt        # Token hasil GetTokens.py (auto-generated)
├── timeshift.txt    # Offset timing per token (ms)
└── README.md
```

---

## Cara Penggunaan

### Langkah 1 — Ambil Token

Jalankan `GetTokens.py` untuk mengekstrak token sesi dari browser.

**Windows:**
```
python GetTokens.py
```

**Linux:**
```bash
python3 GetTokens.py
```

Alur yang terjadi:
1. Firefox terbuka otomatis ke halaman Mi Community
2. Login akun Mi di Firefox, klik **OK** pada dialog
3. Firefox ditutup otomatis (proses ini memang disengaja untuk membaca cookie)
4. Chrome terbuka via Selenium
5. Login akun Mi di Chrome, klik **OK** pada dialog
6. Token tersimpan ke `token.txt`
7. 4 terminal `NScript.py` terbuka otomatis

> **Catatan:** Jika menggunakan beberapa akun Mi, ulangi proses ini untuk tiap akun. Token tiap akun disimpan per baris di `token.txt`.

---

### Langkah 2 — Jalankan Script Utama

Jika tidak melalui GetTokens.py, jalankan manual:

**Windows:**
```
python NScript.py
```

**Linux:**
```bash
python3 NScript.py
```

Saat dijalankan:
1. Input nomor baris token (1, 2, 3, atau 4 — sesuai urutan akun di `token.txt`)
2. Script mengecek status akun di server Xiaomi
3. Script mengambil waktu Beijing via NTP
4. Script mengukur latency ke server Xiaomi
5. Script menunggu hingga 00:00 Beijing Time
6. Tepat sebelum 00:00, 40 request dikirim simultan
7. Jika berhasil, status akun dicek ulang otomatis

---

## Menjalankan Multi-Akun Secara Bersamaan

Untuk memaksimalkan peluang, jalankan satu instance NScript.py per akun secara bersamaan di terminal berbeda.

**Windows — buka 4 Command Prompt secara manual:**
```
# Terminal 1
python NScript.py  → input: 1

# Terminal 2
python NScript.py  → input: 2

# Terminal 3
python NScript.py  → input: 3

# Terminal 4
python NScript.py  → input: 4
```

**Linux — buka 4 terminal Konsole:**
```bash
konsole -e python3 NScript.py &
```
Ulangi 4 kali, input nomor token berbeda di tiap terminal.

---

## Format token.txt

File ini berisi token per baris. Baris 1 = token akun 1, baris 2 = token akun 2, dst.

```
eyJhbGci...token_akun_1...
eyJhbGci...token_akun_2...
eyJhbGci...token_akun_3...
eyJhbGci...token_akun_4...
```

Token expired setelah sesi browser berakhir. Jalankan ulang `GetTokens.py` jika script melaporkan **"Cookie expired"**.

---

## Troubleshooting

### "Cookie expired" / Code 100004
Token sudah tidak valid. Jalankan ulang `GetTokens.py` dan login ulang di browser.

### ICMP ping gagal di Linux
Script otomatis fallback ke HTTP RTT untuk mengukur latency. Tidak perlu tindakan manual.

### ChromeDriver error
Versi ChromeDriver tidak cocok dengan Chrome yang terinstall. Update ChromeDriver sesuai versi Chrome:
```
chrome://settings/help  ← cek versi Chrome di sini
```

### Script tidak menemukan NScript.py
Pastikan `GetTokens.py` dan `NScript.py` berada di folder yang sama.

### Request selalu Code 3 (kuota habis)
Server Xiaomi menerapkan kuota harian. Tunggu reset 00:00 Beijing Time hari berikutnya.

### Latency terlalu tinggi (> 100ms)
Pertimbangkan menggunakan VPS region Singapore untuk mendapat latency 1–5ms ke server Xiaomi — timing burst jauh lebih presisi.

---

## Notes Penting

- Script ini menggunakan API resmi Mi Community (`sgp-api.buy.mi.com`). Tidak ada eksploitasi atau akses unauthorized.
- Akun Mi harus sudah berumur minimal 30 hari untuk bisa mengajukan UBL.
- Xiaomi membatasi 1 request UBL per akun per hari. Gunakan multi-akun untuk meningkatkan peluang.
- Token bersifat sensitif — jangan bagikan `token.txt` ke siapa pun.
- Waktu reset server menggunakan Beijing Time (UTC+8), bukan WIB (UTC+7). Selisih 1 jam — 00:00 Beijing = 23:00 WIB.
- Hasil request (approved/rejected) sepenuhnya ditentukan oleh server Xiaomi. Script hanya memastikan request terkirim tepat waktu dan dalam jumlah maksimal yang diizinkan.

---

## Kompatibilitas

| OS | Status |
|---|---|
| Windows 10/11 | Fully supported |
| Ubuntu / Debian | Fully supported |
| Arch / CachyOS / Manjaro | Fully supported |
| Fedora | Fully supported |
| macOS | Supported (ICMP fallback aktif) |

---

## Versi Script

`ARU_FHL_v070425`
