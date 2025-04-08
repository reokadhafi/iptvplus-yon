from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import re


options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
driver = webdriver.Chrome(options=options)

driver.get("https://www.rctiplus.com/tv/rcti")

# Klik tombol play
try:
    play_btn = WebDriverWait(driver, 20).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.jw-icon.jw-icon-display'))
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

# Simpan juga sebagai playlist M3U (untuk VLC / Kodi)
with open("rcti.m3u", "w") as f:
    f.write("#EXTM3U\n")
    for url in m3u8_urls:
        f.write('#EXTVLCOPT:http-referrer=https://www.rctiplus.com/\n')
        f.write('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36\n')
        f.write('#KODIPROP:inputstream=inputstream.adaptive\n')
        f.write('#KODIPROP:inputstreamaddon=inputstream.adaptive\n')
        f.write('#KODIPROP:inputstream.adaptive.manifest_type=hls\n')
        f.write('#EXTINF:-1 tvg-id="RCTI" tvg-name="RCTI" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/1/17/Logo_RCTI.png" group-title="Indonesia",RCTI\n')
        f.write(url + "\n")


driver.quit()
