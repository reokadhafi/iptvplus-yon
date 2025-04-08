import threading
import requests
import time
import re
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
lock = threading.Lock()

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    #options.add_argument("window-size=640x360")
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

def save_playlist(name, logo, referer, urls):
    with lock:
        for m3u8 in urls:
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

def process_channel(name, info):
    driver = setup_driver()
    url = info["url"]
    referer = info["referer"]
    logo = info["logo"]

    driver.get(url)
    print(f"\n📺 Memproses channel: {name.upper()} ({url})")

    # Step 1: Coba cari m3u8 langsung dari log
    m3u8_urls = wait_for_m3u8_log(driver, name)
    if m3u8_urls:
        save_playlist(name, logo, referer, m3u8_urls)
        driver.quit()
        return

    # Step 2: Klik tombol 'Lewati' jika ada
    try:
        skip_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Lewati") or contains(text(), "Skip")]'))
        )
        skip_btn.click()
        print("⏩ Tombol Lewati diklik.")
        time.sleep(2)
    except:
        print("ℹ️ Tidak ada tombol Lewati.")

    # Step 3: Klik tombol 'Play' jika ada
    try:
        if name == "trans7":
            play_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "svg.playback_button_svg"))
            )
        else:
            #play_btn = WebDriverWait(driver, 5).until(
                #EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.jw-icon.jw-icon-display'))
            #)
            play_btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.jw-icon.jw-icon-display.jw-button-color.jw-reset'))
            )
        play_btn.click()
        print("▶️ Tombol Play diklik.")
    except Exception as e:
        print(f"❌ Gagal klik tombol Play: {e}")

    # Step 4: Coba ambil ulang dari log
    m3u8_urls = wait_for_m3u8_log(driver, name)
    if m3u8_urls:
        save_playlist(name, logo, referer, m3u8_urls)
        driver.quit()
        return

    # Step 5: Fallback dari HTML source
    html = driver.page_source
    fallback_urls = re.findall(r'https.*?\.m3u8[^"]*', html)
    if fallback_urls:
        print("📄 M3U8 ditemukan dari HTML fallback.")
        save_playlist(name, logo, referer, fallback_urls)
    else:
        print(f"❌ Tidak menemukan M3U8 untuk {name.upper()}")

    driver.quit()

def load_external_m3u(source):
    if source.startswith("http"):
        try:
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            return response.text.splitlines()
        except Exception as e:
            print(f"❌ Gagal ambil dari {source}: {e}")
            return []
    else:
        try:
            with open(source, "r", encoding="utf-8") as f:
                return f.readlines()
        except UnicodeDecodeError:
            print(f"⚠️ Encoding UTF-8 gagal untuk {source}, coba pakai latin-1...")
            try:
                with open(source, "r", encoding="latin-1") as f:
                    return f.readlines()
            except Exception as e:
                print(f"❌ Gagal baca file lokal {source} (latin-1): {e}")
                return []
        except Exception as e:
            print(f"❌ Gagal baca file lokal {source}: {e}")
            return []

def clean_duplicates(lines):
    seen = set()
    clean = []
    for line in lines:
        if line.strip() and not line.startswith("#EXTM3U"):
            if line not in seen:
                clean.append(line)
                seen.add(line)
    return clean

# Mulai multithread scrape
threads = []
for name, info in channels.items():
    t = threading.Thread(target=process_channel, args=(name, info))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

# Tambah dari sumber eksternal
external_sources = [
    "external1.m3u"  # lokal
]

for src in external_sources:
    print(f"\n➕ Menambahkan eksternal: {src}")
    ext_lines = load_external_m3u(src)
    playlist_entries.extend(ext_lines)

# Bersihkan dan gabungkan
final_playlist = clean_duplicates(playlist_entries)

# Simpan ke file
with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for entry in final_playlist:
        if not entry.endswith("\n"):
            entry += "\n"
        f.write(entry)

print("\n🎉 Semua channel + eksternal berhasil disimpan ke playlist.m3u")
