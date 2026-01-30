const { chromium } = require("playwright");
const fs = require("fs");

const CHANNELS = {
  RCTI: "https://www.rctiplus.com/tv/rcti",
  MNCTV: "https://www.rctiplus.com/tv/mnctv",
  GTV: "https://www.rctiplus.com/tv/gtv",
  INEWS: "https://www.rctiplus.com/tv/inews",
};

// ambil angka bitrate dari url (600000 > 210000)
function bitrateScore(url) {
  const m = url.match(/avc1_(\d+)/);
  return m ? Number(m[1]) : 0;
}

async function scanChannel(browser, name, url) {
  const page = await browser.newPage();
  let best = null;

  page.on("response", (resp) => {
    const u = resp.url();
    if (u.includes(".m3u8") && u.includes("avc1")) {
      if (!best || bitrateScore(u) > bitrateScore(best)) {
        best = u;
      }
    }
  });

  console.log(`📡 ${name}`);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(7000);

  // paksa play (tanpa render berat)
  await page.evaluate(() => {
    const btn =
      document.querySelector(".jw-icon-display") ||
      document.querySelector(".jw-display-icon-container");
    if (btn) btn.click();

    document.querySelectorAll("video").forEach((v) => {
      v.muted = true;
      v.play().catch(() => {});
    });
  });

  // tunggu playlist muncul & refresh
  await page.waitForTimeout(10000);
  await page.close();

  if (best) {
    console.log(`✅ ${name} OK`);
    return [name, best];
  } else {
    console.log(`❌ ${name} gagal`);
    return [name, null];
  }
}

(async () => {
  console.time("⚡ TOTAL");

  const browser = await chromium.launch({
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
      "--mute-audio",
      "--disable-blink-features=AutomationControlled",
    ],
  });

  const results = {};

  const tasks = Object.entries(CHANNELS).map(([name, url]) =>
    scanChannel(browser, name, url)
  );

  const outputs = await Promise.all(tasks);

  for (const [name, link] of outputs) {
    if (link) results[name] = link;
  }

  await browser.close();
  console.timeEnd("⚡ TOTAL");

  if (!Object.keys(results).length) {
    console.log("⚠️ Tidak ada channel berhasil");
    return;
  }

  let m3u = "#EXTM3U\n";
  for (const [ch, link] of Object.entries(results)) {
    m3u += `
#EXTINF:-1 tvg-id="${ch}" group-title="Indonesia", ${ch}
#EXTVLCOPT:http-referrer=https://www.rctiplus.com/
#EXTVLCOPT:http-user-agent=Mozilla/5.0
${link}
`;
  }

  fs.writeFileSync("indonesia1.m3u", m3u.trim());
  console.log("\n🎉 indonesia1.m3u dibuat");
})();
