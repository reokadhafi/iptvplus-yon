const fs = require("fs");
const { chromium } = require("playwright");

const GROUP = process.argv[2] || "indonesia"; 
// usage: node scanner.js indonesia
//        node scanner.js premium

const CONFIG_FILE = `${GROUP}.json`;
const OUTPUT_FILE = `${GROUP}.m3u`;
const MAX_PARALLEL = 4;

const channels = JSON.parse(fs.readFileSync(CONFIG_FILE, "utf8"));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: "Mozilla/5.0 (X11; Linux x86_64)",
  });

  const entries = Object.entries(channels);
  const results = [];

  async function scanChannel([url, conf]) {
    const page = await context.newPage();
    const m3u8Set = new Set();

    console.log(`📡 ${conf.name}`);

    if (conf.headers?.Referer) {
      await page.setExtraHTTPHeaders({
        referer: conf.headers.Referer,
      });
    }

    page.on("response", async (res) => {
      const u = res.url();
      if (u.includes(".m3u8")) {
        m3u8Set.add(u);
      }
    });

    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(8000);
    } catch (e) {
      console.log(`❌ ${conf.name} error`);
    }

    await page.close();
    return { conf, links: [...m3u8Set] };
  }

  // ---- PARALLEL POOL ----
  for (let i = 0; i < entries.length; i += MAX_PARALLEL) {
    const chunk = entries.slice(i, i + MAX_PARALLEL);
    const res = await Promise.all(chunk.map(scanChannel));
    results.push(...res);
  }

  await browser.close();

  // ---- WRITE M3U ----
  let output = "#EXTM3U\n";

  for (const { conf, links } of results) {
    if (!links.length) continue;

    links.forEach((link, i) => {
      const title = links.length > 1 ? `${conf.name} ${i + 1}` : conf.name;

      output += `#EXTINF:-1 group-title="${GROUP.toUpperCase()}"`;
      if (conf.logo) output += ` tvg-logo="${conf.logo}"`;
      output += `,${title}\n`;

      if (conf.headers?.Referer) {
        output += `#EXTVLCOPT:http-referrer=${conf.headers.Referer}\n`;
      }

      output += `#EXTVLCOPT:http-user-agent=Mozilla/5.0\n`;
      output += `#KODIPROP:inputstream=inputstream.adaptive\n`;
      output += `#KODIPROP:inputstreamaddon=inputstream.adaptive\n`;
      output += `#KODIPROP:inputstream.adaptive.manifest_type=hls\n`;
      output += `${link}\n`;
    });
  }

  fs.writeFileSync(OUTPUT_FILE, output, "utf8");
  console.log(`✅ ${OUTPUT_FILE} selesai`);
})();
