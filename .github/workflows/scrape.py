from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://www.rctiplus.com/tv/rcti")

try:
    play_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class*="vjs-big-play-button"]'))
    )
    play_btn.click()
    print("▶️ Tombol Play diklik.")
except Exception as e:
    print("❌ Gagal klik tombol play:", e)

time.sleep(15)

logs = driver.get_log('performance')
found = False
for log in logs:
    msg = log['message']
    if '.m3u8' in msg:
        urls = re.findall(r'https.*?\.m3u8[^"]*', msg)
        for u in urls:
            print("🔗 M3U8 found:", u)
            found = True

if not found:
    html = driver.page_source
    m3u8s = re.findall(r'https.*?\.m3u8[^"]*', html)
    for u in m3u8s:
        print("📄 From HTML:", u)

driver.quit()
