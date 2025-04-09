import asyncio
import aiohttp
import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor

# Load konfigurasi channel
with open("premium.json", "r") as f:
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
        time.sleep(15)  # tambahkan waktu buffer agar video muncul
        logs = driver.get_log("performance")
        html = driver.page_source

        # Ambil dari log network
        links_from_logs = extract_m3u8_from_logs(logs)

        # Ambil juga dari HTML sebagai cadangan
        links_from_html = re.findall(r'https?://[^\s\'"]+\.m3u8?', html)

        # Gabungkan dan hilangkan duplikat
        all_links = list(set(links_from_logs + links_from_html))
    except Exception as e:
        print(f"[ERROR] Gagal mengambil link dari {url}: {e}")
        all_links = []
    driver.quit()
    return url, all_links


async def is_valid_m3u8(url, headers):
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=10) as response:
                return response.status == 200
    except:
        return False

async def validate_and_format(name, url, headers):
    if await is_valid_m3u8(url, headers):
        return f"#EXTINF:-1 group-title='Premium',{name}\n#EXTVLCOPT:http-referrer={headers['Referer']}\n#EXTVLCOPT:http-user-agent={headers['User-Agent']}\n#KODIPROP:inputstream=inputstream.adaptive\n#KODIPROP:inputstreamaddon=inputstream.adaptive\n#KODIPROP:inputstream.adaptive.manifest_type=hls\n{url}"
    else:
        print(f"  [✗ TIDAK VALID] {url}")
        return None

async def process_all():
    loop = asyncio.get_event_loop()
    results = []
    tasks = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            loop.run_in_executor(executor, get_links_from_url, url)
            for url in channel_config.keys()
        ]
        link_results = await asyncio.gather(*futures)

    for url, links in link_results:
        conf = channel_config[url]
        name = conf["name"]
        headers = {
            "Referer": conf["headers"].get("Referer", ""),
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }

        for i, link in enumerate(links):
            title = f"{name} {i+1}" if len(links) > 1 else name
            tasks.append(validate_and_format(title, link, headers))

    all_results = await asyncio.gather(*tasks)

    with open("premium.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for result in all_results:
            if result:
                f.write(result + "\n")

    print("✅ File premium.m3u berhasil dibuat!")

if __name__ == "__main__":
    asyncio.run(process_all())
