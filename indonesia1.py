import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_live_stream():
    chrome_options = Options()
    # WAJIB: Headless harus aktif di GitHub Actions
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1280,800")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    channels = {
        "RCTI": "https://www.rctiplus.com/tv/rcti",
        "MNCTV": "https://www.rctiplus.com/tv/mnctv",
        "GTV": "https://www.rctiplus.com/tv/gtv",
        "iNews": "https://www.rctiplus.com/tv/inews"
    }

    final_m3u8_links = {}

    try:
        for name, url in channels.items():
            print(f"📡 Mencoba akses {name}...")
            driver.get(url)
            time.sleep(10)

            # Paksa klik via JS (Paling aman untuk Headless)
            try:
                driver.execute_script("document.querySelector('.jw-icon-display').click();")
            except:
                pass

            time.sleep(15)

            logs = driver.get_log('performance')
            found_url = None
            
            for entry in logs:
                msg = json.loads(entry['message'])['message']
                if 'params' in msg and 'request' in msg['params']:
                    req_url = msg['params']['request']['url']
                    if ".m3u8" in req_url and "hdntl=" in req_url:
                        if "pubads" not in req_url and "dai.google" not in req_url:
                            found_url = req_url
                            break
            
            if found_url:
                final_m3u8_links[name] = found_url
                print(f"✅ Link didapat: {name}")

        # --- OUTPUT SESUAI WORKFLOW (indonesia1.m3u) ---
        if final_m3u8_links:
            with open("indonesia1.m3u", "w") as f:
                f.write("#EXTM3U\n")
                for n, l in final_m3u8_links.items():
                    f.write(f'\n#EXTINF:-1 tvg-id="{n}" group-title="Indonesia", {n}\n')
                    f.write("#EXTVLCOPT:http-referrer=https://www.rctiplus.com/\n")
                    f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\n")
                    f.write(f"{l}\n")
            print("🎉 File indonesia1.m3u berhasil diperbarui.")

    finally:
        driver.quit()

if __name__ == "__main__":
    get_live_stream()
