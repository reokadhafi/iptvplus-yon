import re
import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

channels = {
    "rcti": {
        "slug": "rcti",
        "url": "https://www.rctiplus.com/tv/rcti",
        "referer": "https://www.rctiplus.com/",
        "logo": "https://github.com/riotryulianto/iptv-playlists/blob/main/icons/rcti.png?raw=true"
    },
    "gtv": {
        "slug": "gtv",
        "url": "https://www.rctiplus.com/tv/gtv",
        "referer": "https://www.rctiplus.com/",
        "logo": "https://github.com/riotryulianto/iptv-playlists/blob/main/icons/gtv.png?raw=true"
    },
    "mnctv": {
        "slug": "mnctv",
        "url": "https://www.rctiplus.com/tv/mnctv",
        "referer": "https://www.rctiplus.com/",
        "logo": "https://github.com/riotryulianto/iptv-playlists/blob/main/icons/mnctv.png?raw=true"
    },
    "inews": {
        "slug": "inews",
        "url": "https://www.rctiplus.com/tv/inews",
        "referer": "https://www.rctiplus.com/",
        "logo": "https://github.com/riotryulianto/iptv-playlists/blob/main/icons/inews.png?raw=true"
    }
}

playlist_entries = []

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=640x360")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=options)

def get_chrome_logs(driver, retries=3, delay=5):
    for i in range(retries):
        try:
            return driver.get_log('performance')
        except Exception as e:
            print(f"⏳ Retry ({i+1}/{retries}) - gagal ambil log: {e}")
            time.sleep(delay)
    return []

def wait_for_m3u8_log(driver, name, timeout=20):
    start = time.time()
    seen_urls = set()
    m3u8_urls = []
    domain_pattern = rf"https:\/\/{re.escape(name)}-linier\.rctiplus\.id\/hdntl[^\s\"]*"

    while time.time() - start < timeout:
        logs = get_chrome_logs(driver)
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
        if m3u8_urls:
            break
        time.sleep(1)
    return m3u8_urls

def extract_token(m3u8_url):
    match = re.search(r'(hdntl=[^/]+)', m3u8_url)
    if match:
        return match.group(1)
    return None


def save_playlist(name, logo, referer, m3u8):
    entry = (
        f'#EXTINF:-1 tvg-id="{name.upper()}" tvg-name="{name.upper()}" tvg-logo="{logo}" group-title="Indonesia",{name.upper()}\n'
        f'#EXTVLCOPT:http-referrer={referer}\n'
        '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36\n'
        '#KODIPROP:inputstream=inputstream.adaptive\n'
        '#KODIPROP:inputstreamaddon=inputstream.adaptive\n'
        '#KODIPROP:inputstream.adaptive.manifest_type=hls\n'
        f'{m3u8}\n'
    )
    playlist_entries.append(entry)

def generate_from_token(token):
    print(f"\n🧪 Membuat playlist dari token: {token}\n")
    for name, info in channels.items():
        slug = info["slug"]
        referer = info["referer"]
        logo = info["logo"]
        url = f"https://{slug}-linier.rctiplus.id/{token}/{slug}-sdi-avc1_800000=9-mp4a_96000=1.m3u8"
        save_playlist(name, logo, referer, url)

def process_channel(name, info):
    driver = setup_driver()
    url = info["url"]
    referer = info["referer"]

    print(f"\n📺 Mencoba channel: {name.upper()}")
    driver.get(url)

    m3u8_urls = wait_for_m3u8_log(driver, name)
    if not m3u8_urls:
        # Klik tombol Lewati (jika ada)
        try:
            skip_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Lewati") or contains(text(), "Skip")]'))
            )
            skip_btn.click()
            print("⏩ Tombol Lewati diklik.")
            time.sleep(2)
        except:
            print("ℹ️ Tidak ada tombol Lewati.")

        # Klik tombol Play (jika ada)
        try:
            play_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.jw-icon.jw-icon-display'))
            )
            play_btn.click()
            print("▶️ Tombol Play diklik.")
        except Exception as e:
            print(f"❌ Gagal klik tombol Play: {e}")

        # Coba ulang ambil log
        m3u8_urls = wait_for_m3u8_log(driver, name)

    driver.quit()

    if m3u8_urls:
        token = extract_token(m3u8_urls[0])
        if token:
            print(f"✅ Token ditemukan: {token}")
            generate_from_token(token)
            return True
    print(f"❌ Gagal mendapatkan token dari channel {name.upper()}")
    return False

def clean_duplicates(lines):
    entries = []
    seen_keys = set()
    buffer = []

    for line in lines:
        if line.startswith("#EXTINF"):
            if buffer:
                key = buffer[0]  # gunakan EXTINF sebagai kunci
                if key not in seen_keys:
                    entries.extend(buffer)
                    seen_keys.add(key)
                buffer = []
        buffer.append(line)

    if buffer:
        key = buffer[0]
        if key not in seen_keys:
            entries.extend(buffer)

    return entries


def load_external_m3u(source):
    try:
        with open(source, "r", encoding="utf-8") as f:
            return f.readlines()
    except:
        print(f"❌ Gagal membaca file {source}")
        return []

# === MAIN START ===
success = False
for name, info in channels.items():
    if process_channel(name, info):
        success = True
        break

# Simpan hasil scrape jika sukses
if success:
    combined_lines = []
    for entry in playlist_entries:
        combined_lines.extend(entry.strip().splitlines())

    # Bersihkan duplikat
    final_playlist = clean_duplicates(combined_lines)

    # Simpan ke file
    with open("indonesia1.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for line in final_playlist:
            if not line.endswith("\n"):
                line += "\n"
            f.write(line)

    print("\n🎉 Playlist berhasil disimpan ke indonesia1.m3u")
else:
    print("\n🚫 Gagal mendapatkan token dari semua channel.")
