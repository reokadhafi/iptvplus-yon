import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Load konfigurasi channel
with open("indonesia.json", "r") as f:
    channel_config = json.load(f)

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=640x360")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=options)

def extract_m3u8_from_logs(logs):
    m3u8_links = []
    for entry in logs:
        try:
            log = json.loads(entry["message"])["message"]
            if (
                log["method"] == "Network.responseReceived"
                and "url" in log["params"]["response"]
                and ".m3u8" in log["params"]["response"]["url"]
            ):
                url = log["params"]["response"]["url"]
                if url not in m3u8_links:
                    m3u8_links.append(url)
        except:
            continue
    return m3u8_links

def get_links_from_url(url):
    driver = setup_driver()
    print(f"[MENGAKSES] {url}")
    try:
        driver.get(url)
        time.sleep(20)  # Tambahkan waktu agar log lengkap
        logs = driver.get_log("performance")
        html = driver.page_source

        # Ambil dari log dan HTML
        links_from_logs = extract_m3u8_from_logs(logs)
        links_from_html = re.findall(r'https?://[^\s\'"]+\.m3u8?', html)

        all_links = list(set(links_from_logs + links_from_html))
        print(f"  [✓] Ditemukan {len(all_links)} link .m3u8")
    except Exception as e:
        print(f"[ERROR] Gagal mengambil link dari {url}: {e}")
        all_links = []
    driver.quit()
    return url, all_links

async def process_all():
    loop = asyncio.get_event_loop()
    tasks = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            loop.run_in_executor(executor, get_links_from_url, url)
            for url in channel_config.keys()
        ]
        link_results = await asyncio.gather(*futures)

    with open("indonesia2.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for url, links in link_results:
            conf = channel_config[url]
            name = conf["name"]
            logo = conf.get("logo", "")
            headers = conf.get("headers", {})
            referer = headers.get("Referer", "")
            user_agent = "Mozilla/5.0 (X11; Linux x86_64)"

            for i, link in enumerate(links):
                title = f"{name} {i+1}" if len(links) > 1 else name
                extinf_line = f"#EXTINF:-1 group-title=\"Indonesia\""
                if logo:
                    extinf_line += f" tvg-logo=\"{logo}\""
                extinf_line += f",{title}\n"

                entry = (
                    f"{extinf_line}"
                    f"#EXTVLCOPT:http-referrer={referer}\n"
                    f"#EXTVLCOPT:http-user-agent={user_agent}\n"
                    f"#KODIPROP:inputstream=inputstream.adaptive\n"
                    f"#KODIPROP:inputstreamaddon=inputstream.adaptive\n"
                    f"#KODIPROP:inputstream.adaptive.manifest_type=hls\n"
                    f"{link}\n"
                )
                f.write(entry)

    print("✅ File indonesia2.m3u berhasil dibuat tanpa validasi!")

if __name__ == "__main__":
    asyncio.run(process_all())
