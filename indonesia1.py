import json
import time
from urllib.parse import urlparse, parse_qs, unquote

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


CHANNELS = {
    "RCTI": "https://www.rctiplus.com/tv/rcti",
    "MNCTV": "https://www.rctiplus.com/tv/mnctv",
    "GTV": "https://www.rctiplus.com/tv/gtv",
    "iNews": "https://www.rctiplus.com/tv/inews",
}


# =========================
# SETUP CHROME (CI SAFE)
# =========================
def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--remote-debugging-port=9222")
    opts.add_argument("--window-size=1280,800")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--mute-audio")

    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    )

    # Performance log (XHR)
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Network.enable", {})  # WAJIB
    return driver


# =========================
# KLIK PLAY
# =========================
def click_play(driver):
    try:
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".jw-icon-display, .jw-display-icon-container")
            )
        ).click()
    except:
        driver.execute_script("""
            const btn = document.querySelector('.jw-icon-display, .jw-display-icon-container');
            if (btn) btn.click();
        """)

    # Pastikan <video> benar-benar ada
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "video"))
    )


# =========================
# DECODE mu= DARI jwpltx
# =========================
def decode_mu_if_any(url: str):
    """
    Jika URL adalah jwpltx ping.gif dan punya parameter mu= (URL-encoded),
    kembalikan m3u8 ASLI. Kalau tidak, return None.
    """
    if "jwpltx.com" not in url or "mu=" not in url:
        return None

    qs = parse_qs(urlparse(url).query)
    mu = qs.get("mu", [None])[0]
    if not mu:
        return None

    real = unquote(mu)
    return real if ".m3u8" in real else None


# =========================
# PILIH BITRATE TERTINGGI
# =========================
def bitrate_score(u: str) -> int:
    nums = "".join(c if c.isdigit() else " " for c in u).split()
    return max(map(int, nums)) if nums else 0


# =========================
# CARI M3U8 DARI NETWORK
# =========================
def find_m3u8(driver, channel_key):
    found = set()

    # polling ±30 detik
    for _ in range(15):
        logs = driver.get_log("performance")

        for entry in logs:
            msg = json.loads(entry["message"])["message"]
            if msg.get("method") != "Network.requestWillBeSent":
                continue

            url = msg["params"]["request"]["url"]

            # 1) Ambil m3u8 langsung (PRIORITAS)
            if (
                ".m3u8" in url
                and "1s1.rctiplus.id/live" in url
                and channel_key in url
            ):
                found.add(url)
                continue

            # 2) Decode dari jwpltx ping.gif (mu=)
            decoded = decode_mu_if_any(url)
            if decoded and channel_key in decoded and "1s1.rctiplus.id/live" in decoded:
                found.add(decoded)

        if found:
            break

        time.sleep(2)

    if not found:
        return None

    # pilih bitrate tertinggi
    return sorted(found, key=bitrate_score)[-1]


# =========================
# MAIN
# =========================
def main():
    driver = setup_driver()
    results = {}

    try:
        for name, page in CHANNELS.items():
            print(f"📡 {name} ...")
            driver.get(page)
            time.sleep(8)

            click_play(driver)
            time.sleep(3)

            key = name.lower()
            m3u8 = find_m3u8(driver, key)

            if m3u8:
                results[name] = m3u8
                print(f"✅ {name} OK")
            else:
                print(f"❌ {name} gagal")

        if results:
            with open("indonesia1.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch, link in results.items():
                    f.write(
                        f'\n#EXTINF:-1 tvg-id="{ch}" group-title="Indonesia", {ch}\n'
                        "#EXTVLCOPT:http-referrer=https://www.rctiplus.com/\n"
                        "#EXTVLCOPT:http-user-agent=Mozilla/5.0\n"
                        f"{link}\n"
                    )
            print("\n🎉 indonesia1.m3u berhasil dibuat")
        else:
            print("\n⚠️ Tidak ada channel yang berhasil")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
