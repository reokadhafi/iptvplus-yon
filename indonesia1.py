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
from selenium.webdriver.common.action_chains import ActionChains

def get_live_stream():
    chrome_options = Options()
    # Matikan headless sementara (ubah ke headless=new jika sudah lancar)
    # chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("window-size=1280,800")
    
    # Menyamarkan bot agar tidak diblokir
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
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
            
            # Tunggu halaman stabil
            time.sleep(10)

            # SCRIPT KLIK AGRESIF
            try:
                # Cari tombol play (berdasarkan HTML jw-icon-display Anda)
                wait = WebDriverWait(driver, 15)
                play_btn = wait.until(EC.presence_of_element_to_be_clickable((By.CSS_SELECTOR, ".jw-icon-display, .jw-display-icon-container")))
                
                # Gunakan ActionChains untuk pindahkan mouse dan klik (lebih manusiawi)
                actions = ActionChains(driver)
                actions.move_to_element(play_btn).click().perform()
                print(f"▶️ Berhasil klik Play untuk {name}")
            except:
                # Jika gagal klik manual, paksa lewat JS
                driver.execute_script("document.querySelector('.jw-icon-display').click();")
                print(f"⚡ Mencoba paksa klik via JS untuk {name}")

            # Tunggu stream dipanggil (agak lama karena iklan)
            print("⏳ Menunggu link m3u8 muncul di network...")
            time.sleep(20)

            # AMBIL LOG NETWORK
            logs = driver.get_log('performance')
            found_url = None
            
            for entry in logs:
                msg = json.loads(entry['message'])['message']
                if 'params' in msg and 'request' in msg['params']:
                    req_url = msg['params']['request']['url']
                    
                    # Filter link m3u8 asli (biasanya ada token hdntl)
                    if ".m3u8" in req_url and "hdntl=" in req_url:
                        # Abaikan link iklan (dai.google / ads)
                        if "pubads" not in req_url and "dai.google" not in req_url:
                            found_url = req_url
                            break
            
            if found_url:
                final_m3u8_links[name] = found_url
                print(f"✅ Link didapat: {name}")
            else:
                print(f"❌ Gagal mendapatkan token untuk {name}")

        # Tulis ke M3U
        if final_m3u8_links:
            with open("indonesia1.m3u", "w") as f:
                f.write("#EXTM3U\n")
                for n, l in final_m3u8_links.items():
                    f.write(f'\n#EXTINF:-1 tvg-id="{n}" group-title="Indonesia", {n}\n')
                    f.write("#EXTVLCOPT:http-referrer=https://www.rctiplus.com/\n")
                    f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\n")
                    f.write(f"{l}\n")
            print("\n🎉 Sukses! Cek file 'indonesia1.m3u'")

    finally:
        driver.quit()

if __name__ == "__main__":
    get_live_stream()
