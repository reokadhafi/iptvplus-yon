import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


CHANNELS = {
    "RCTI": "https://www.rctiplus.com/tv/rcti",
    "MNCTV": "https://www.rctiplus.com/tv/mnctv",
    "GTV": "https://www.rctiplus.com/tv/gtv",
    "iNews": "https://www.rctiplus.com/tv/inews",
}


def setup_driver():
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--mute-audio")
    opts.add_argument("--window-size=1280,800")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    )

    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )

    # PENTING: enable Network logging
    driver.execute_cdp_cmd("Network.enable", {})
    return driver


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

    # tunggu elemen <video> benar-benar ada
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "video"))
    )


def find_m3u8(driver, keyword):
    found = set()

    # polling 15x (±30 detik)
    for _ in range(15):
        logs = driver.get_log("performance")
        for entry in logs:
            msg = json.loads(entry["message"])["message"]

            if msg.get("method") == "Network.requestWillBeSent":
                url = msg["params"]["request"]["url"]

                if (
                    ".m3u8" in url
                    and keyword in url
                    and "ads" not in url
                ):
                    found.add(url)

        if found:
            break

        time.sleep(2)

    if not found:
        return None

    # pilih bitrate tertinggi (angka terbesar)
    return sorted(found, key=lambda x: int("".join(filter(str.isdigit, x))))[-1]


def main():
    driver = setup_driver()
    results = {}

    try:
        for name, url in CHANNELS.items():
            print(f"📡 {name}...")
            driver.get(url)
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
                        "#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)\n"
                        f"{link}\n"
                    )

            print("\n🎉 indonesia1.m3u berhasil dibuat")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
