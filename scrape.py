from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import re

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

driver.get("https://www.rctiplus.com/tv/rcti")

# Klik tombol play
try:
    play_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class*="vjs-big-play-button"]'))
    )
    play_btn.click()
    print("▶️ Tombol Play diklik.")
except Exception as e:
    print("❌ Gagal klik tombol play:", e)

# Tunggu supaya video benar-benar mulai
time.sleep(15)

# Cek log performance untuk .m3u8
logs = driver.get_log('performance')
found = False
m3u8_urls = []

for log in logs:
    msg = log['message']
    if '.m3u8' in msg:
        urls = re.findall(r'https.*?\.m3u8[^"]*', msg)
        for u in urls:
            m3u8_urls.append(u)
            print("🔗 M3U8 ditemukan:", u)
            found = True

if not found:
    # Cadangan: cek page_source
    html = driver.page_source
    m3u8s = re.findall(r'https.*?\.m3u8[^"]*', html)
    for u in m3u8s:
        m3u8_urls.append(u)
        print("📄 Dari HTML:", u)

# Simpan URL .m3u8 ke dalam file output.txt
with open("output.txt", "w") as f:
    for url in m3u8_urls:
        f.write(url + "\n")

driver.quit()
