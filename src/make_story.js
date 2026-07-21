/**
 * make_story.js — builds out/pending/story.png (1080x1920) from the finished
 * out/pending/post.png: the square card centered on a Mojave-night gradient
 * with a dawn glow, so nothing gets cropped when shared to Stories.
 * Requires only Puppeteer (already a dependency). Run after generate.js.
 */
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");

const PENDING = path.join(__dirname, "..", "out", "pending");

(async () => {
  const cardPath = path.join(PENDING, "post.png");
  if (!fs.existsSync(cardPath)) throw new Error("post.png not found — run generate.js first");
  const b64 = fs.readFileSync(cardPath).toString("base64");

  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    * { margin:0; padding:0; }
    body { width:1080px; height:1920px; overflow:hidden; position:relative;
           background: linear-gradient(180deg,#0E1420 0%,#101828 55%,#1A2030 100%); }
    .glow { position:absolute; left:50%; bottom:-420px; transform:translateX(-50%);
            width:1700px; height:760px; border-radius:50%;
            background: radial-gradient(ellipse at center,
              rgba(255,107,44,0.35) 0%, rgba(255,179,71,0.12) 45%, rgba(14,20,32,0) 72%); }
    .card { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
            width:1000px; height:1000px; border-radius:24px; overflow:hidden;
            box-shadow: 0 40px 120px rgba(0,0,0,0.6); }
    .card img { width:100%; height:100%; display:block; }
  </style></head><body>
    <div class="glow"></div>
    <div class="card"><img src="data:image/png;base64,${b64}"></div>
  </body></html>`;

  const browser = await puppeteer.launch({ args: ["--no-sandbox", "--disable-setuid-sandbox"] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
    await page.setContent(html, { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(PENDING, "story.png"), type: "png" });
    console.log("Built out/pending/story.png (1080x1920)");
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
