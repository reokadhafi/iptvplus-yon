from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# Setup Chrome
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("window-size=640x360")
options.add_argument("--autoplay-policy=no-user-gesture-required")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
driver = webdriver.Chrome(options=options)

# Channel list dan logonya
channels = {
    "rcti": {
        "slug": "rcti",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/1/17/Logo_RCTI.png"
    },
    "gtv": {
        "slug": "gtv",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Logo_GTV_2017.png"
    },
    "mnctv": {
        "slug": "mnctv",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/6/6c/Logo_MNCTV_2020.png"
    },
    "inews": {
        "slug": "inews",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/8/83/Logo_iNews.png"
    }
}

playlist_entries = []

# Fungsi ambil log Chrome dengan retry
def get_chrome_logs(driver, retries=3, delay=5):
    for i in range(retries):
        try:
            return driver.get_log('performance')
        except Exception as e:
            print(f"⏳ Retry ({i+1}/{retries}) - gagal ambil log: {e}")
            time.sleep(delay)
    print("❌ Gagal ambil log Chrome setelah beberapa percobaan.")
    return []

# Proses tiap channel
for name, info in channels.items():
    slug = info["slug"]
    logo = info["logo"]
    url = f"https://www.rctiplus.com/tv/{slug}"
    driver.get(url)
    print(f"\n📺 Memproses channel: {name.upper()}")

    try:
        time.sleep(2)
        skip_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Lewati") or contains(text(), "Skip")]'))
        )
        skip_btn.click()
        print("⏩ Tombol Lewati diklik.")
        time.sleep(2)
    except Exception:
        print("ℹ️ Tidak ada tombol Lewati, lanjut ke Play...")

    try:
        play_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.jw-icon.jw-icon-display'))
        )
        play_btn.click()
        print("▶️ Tombol Play diklik.")
    except Exception as e:
        print("❌ Gagal klik tombol Play:", e)

    time.sleep(15)

    logs = get_chrome_logs(driver)
    m3u8_urls = []
    seen_urls = set()
    found = False
    domain_pattern = rf"https:\/\/{re.escape(name)}-linier\.rctiplus\.id\/hdntl[^\s\"]*"

    for log in logs:
        msg = log['message']
        if '.m3u8' in msg:
            urls = re.findall(domain_pattern, msg)
            urls = [u for u in urls if re.search(r'\.m3u8(\?|$)', u)]
            for u in set(urls):
                if u not in seen_urls:
                    seen_urls.add(u)
                    m3u8_urls.append(u)
                    print("🔗 M3U8 ditemukan:", u)
                    found = True

    # Fallback jika tidak ada dari log
    if not found:
        html = driver.page_source
        fallback_urls = re.findall(r'https.*?\.m3u8[^"]*', html)
        for u in fallback_urls:
            if u not in seen_urls:
                seen_urls.add(u)
                m3u8_urls.append(u)
                print("📄 Dari HTML:", u)

    # Tambahkan ke playlist
    for url in m3u8_urls:
        entry = (
            f'#EXTINF:-1 tvg-id="{name.upper()}" tvg-name="{name.upper()}" tvg-logo="{logo}" group-title="Indonesia",{name.upper()}\n'
            '#EXTVLCOPT:http-referrer=https://www.rctiplus.com/\n'
            '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36\n'
            '#KODIPROP:inputstream=inputstream.adaptive\n'
            '#KODIPROP:inputstreamaddon=inputstream.adaptive\n'
            '#KODIPROP:inputstream.adaptive.manifest_type=hls\n'
            f'{url}\n'
        )
        playlist_entries.append(entry)

    print(f"✅ Selesai memproses channel: {name.upper()}")

# Simpan ke file .m3u
with open("playlist.m3u", "w") as f:
    f.write("#EXTM3U\n")
    for entry in playlist_entries:
        f.write(entry)

driver.quit()
print("\n🎉 Semua channel berhasil disimpan ke playlist.m3u")
