import subprocess
import sys
import time
import os
import webbrowser
import browser_cookie3
import tkinter as tk
import shutil
from tkinter import ttk
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Konfigurasi
TOKEN_FILE = "token.txt"
TARGET_SCRIPT = "NScript.py"
LOGIN_URL = "https://c.mi.com/global"

def get_python_cmd():
    for cmd in ['python3', 'python', 'py']:
        if shutil.which(cmd):
            return cmd
    return 'python3' # Fallback default

py_cmd = get_python_cmd()


def show_prompt(title, msg):
    root = tk.Tk()
    root.title(title)
    root.geometry("400x120")
    root.attributes("-topmost", True)
    ttk.Label(root, text=msg, padding=10, wraplength=350).pack()
    ttk.Button(root, text="OK", command=root.destroy).pack(pady=5)
    root.mainloop()

def get_tokens():
    # Firefox Step
    webbrowser.open(LOGIN_URL)
    show_prompt("Firefox Login", "Login di Firefox, lalu klik OK.")
    os.system("pkill firefox") # Penting di Linux agar database cookie unlock
    time.sleep(2)
    
    f_token = ""
    try:
        cj = browser_cookie3.firefox()
        for c in cj:
            if "new_bbs_serviceToken" in c.name:
                f_token = c.value
    except: pass

    # Chrome Step (Selenium)
    opts = Options()
    driver = webdriver.Chrome(options=opts)
    driver.get(LOGIN_URL)
    show_prompt("Chrome Login", "Login di Chrome, lalu klik OK.")
    c_token = driver.execute_script("var m = document.cookie.match(/popRunToken=([^;]+)/); return m ? m[1] : null;")
    driver.quit()

    return f_token, c_token

if __name__ == "__main__":
    if not os.path.exists(TARGET_SCRIPT):
        print(f"Error: {TARGET_SCRIPT} tidak ada!")
        sys.exit()

    ft, ct = get_tokens()
    
    with open(TOKEN_FILE, "w") as f:
        f.write(f"{ft}\n{ct}\n{ft}\n{ct}")

    print("[+] Token berhasil disimpan. Membuka 4 terminal...")

    # Spawn terminal untuk CachyOS (KDE/Konsole) & Windows
    for i in range(1, 5):
        if os.name == 'nt':
            # Gunakan /c agar terminal tidak langsung tutup jika error
            subprocess.Popen(f'start cmd /k "{py_cmd} {TARGET_SCRIPT}"', shell=True)
        else:
            # Logic Linux (Fish/Konsole)
            command = f"echo {i} | {py_cmd} {TARGET_SCRIPT}; exec fish"
            subprocess.Popen(["konsole", "-e", "fish", "-c", command])
        time.sleep(0.3)