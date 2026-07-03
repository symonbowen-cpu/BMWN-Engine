/**
 * generate.js — creates today's post (image + caption) into out/pending/.
 * Does NOT publish. Publishing is a separate step (src/publish.js) so the
 * image can be committed/pushed first (Instagram's API needs a public URL).
 *
 * Env:
 *   ANTHROPIC_API_KEY  — required unless DRY_RUN=1
 *   DRY_RUN=1          — skip the Claude call, use canned copy (for testing)
 */
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");
const { PENDING, themes, state, saveState, saveJSON, buildHTML } = require("./lib");

const MODEL = process.env.CLAUDE_MODEL || "claude-sonnet-4-6";

// ---------- pillar rotation ----------
function pickTopic(cfg, st) {
  const pillar = cfg.pillars[st.pillarIndex % cfg.pillars.length];
  const tIdx = st.topicIndexes[pillar.id] || 0;
  const topic = pillar.topics[tIdx % pillar.topics.length];
  return { pillar, topic, tIdx };
}

// ---------- copywriting via Claude ----------
const SCHEMAS = {
  tip: `{"eyebrow": "2-4 word category label, uppercase feel", "headline": "max 9 words, punchy", "body": "1-2 sentences, max 220 chars", "caption": "...", "hashtags": ["..."], "alt_text": "..."}`,
  stat: `{"eyebrow": "2-4 word label", "stat": "the number itself e.g. 76% or 8 in 10 — max 6 chars ideally", "headline": "max 10 words completing the stat", "body": "1 sentence of context or source framing, max 180 chars", "caption": "...", "hashtags": ["..."], "alt_text": "..."}`,
  myth: `{"myth": "the myth in first person, max 8 words", "fact": "the correction, max 10 words", "body": "1-2 sentences expanding, max 200 chars", "caption": "...", "hashtags": ["..."], "alt_text": "..."}`,
  showcase: `{"category": "plural business type, uppercase feel, 1-2 words", "headline": "max 9 words about the outcome", "mock_url": "example url like victorvillebarber.com", "mock_title": "3-5 word fake business headline", "mock_sub": "one line of what the site offers, max 90 chars", "mock_cta": "2-3 word button label", "caption": "...", "hashtags": ["..."], "alt_text": "..."}`,
};

async function writeCopy(cfg, pillar, topic) {
  if (process.env.DRY_RUN === "1") return cannedCopy(pillar);

  const prompt = `You write Instagram content for ${cfg.brand.name} (${cfg.brand.url}), a web design service for small businesses in ${cfg.brand.region} of California (${cfg.brand.cities.join(", ")}).

NON-NEGOTIABLE FRAMING: Every post is marketing for ${cfg.brand.name}, a company that BUILDS WEBSITES. The reader is a small business owner we want to hire us. Never write copy that sounds like an advertisement for the example business itself (e.g. an HVAC company, a barbershop). We are always the one speaking, and our product is always websites. If a post could be mistaken for another type of business's own ad, it is wrong. The takeaway a reader should always get: "this company builds websites for businesses like mine."

Voice: ${cfg.brand.voice}

Today's post pillar: ${pillar.id}
Goal: ${pillar.goal}
Topic: ${topic}

Rules:
- caption: 3-5 short lines. Hook first line. One concrete takeaway. End with a soft CTA (e.g. "Link in bio" or "DM us 'SITE'"). No emojis except at most 1-2. Never use em dashes.
- hashtags: pick 8-12 from this bank plus 2-3 topical ones: ${cfg.hashtag_bank.join(" ")}
- alt_text: one sentence describing the image for accessibility.
- Never invent fake statistics. If the pillar is "stat", use a real, widely-cited figure and keep the body line honest about it (e.g. "Source: BrightLocal consumer survey").
- Respond with ONLY a JSON object, no markdown fences, matching exactly this shape:
${SCHEMAS[pillar.template]}`;

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": process.env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 1200,
      messages: [{ role: "user", content: prompt }],
    }),
  });

  if (!res.ok) throw new Error(`Claude API ${res.status}: ${await res.text()}`);
  const data = await res.json();
  const text = data.content.filter((b) => b.type === "text").map((b) => b.text).join("\n");
  const clean = text.replace(/```json|```/g, "").trim();
  return JSON.parse(clean);
}

function cannedCopy(pillar) {
  const canned = {
    tip: {
      eyebrow: "LOCAL SEO TIP",
      headline: "Your page title is prime real estate.",
      body: "Put your city and your service in it. \u201CBarber in Victorville\u201D beats \u201CHome\u201D every single time someone searches.",
      caption: "Most local sites waste their most valuable line.\n\nYour page title is what Google reads first. \u201CHome\u201D tells it nothing. \u201CBarbershop in Victorville, CA\u201D tells it everything.\n\n10-second fix, real ranking impact.\n\nDM us \u201CSITE\u201D for a free look at yours.",
      hashtags: ["#HighDesert", "#Victorville", "#SmallBusiness", "#LocalSEO", "#WebDesign", "#ShopLocal", "#Hesperia", "#AppleValley", "#VeteranOwned"],
      alt_text: "Dark desert-themed graphic with a web design tip about page titles above an orange dawn ridgeline.",
    },
    stat: {
      eyebrow: "THE NUMBERS",
      stat: "76%",
      headline: "of people check a business online before visiting.",
      body: "If they can\u2019t find you, they found your competitor. Source: BrightLocal consumer survey.",
      caption: "Three out of four customers look you up before they walk in.\n\nNo website means that search ends somewhere else.\n\nWe build sites for High Desert businesses that show up and convert.\n\nLink in bio.",
      hashtags: ["#SmallBusiness", "#HighDesert", "#LocalSEO", "#Victorville", "#ShopLocal", "#WebDesign", "#Barstow", "#Adelanto"],
      alt_text: "Large orange 76% statistic on a dark desert background about customers searching online.",
    },
    myth: {
      myth: "A Facebook page is enough.",
      fact: "Google barely shows Facebook pages.",
      body: "Local search results favor real websites with real addresses, hours, and service pages. A profile is not a presence.",
      caption: "\u201CI have a Facebook page, I\u2019m good.\u201D\n\nHere\u2019s the problem: when someone Googles \u201Cbarber near me,\u201D Facebook pages rarely make the map pack.\n\nA one-page website fixes that.\n\nDM us \u201CSITE\u201D to see what that looks like for your business.",
      hashtags: ["#SmallBusinessOwner", "#HighDesert", "#Victorville", "#Hesperia", "#WebDesign", "#LocalSEO", "#SupportLocal"],
      alt_text: "Myth versus fact graphic: a Facebook page is not the same as a website, on a dark desert background.",
    },
    showcase: {
      category: "BARBERSHOPS",
      headline: "Turn followers into booked chairs.",
      mock_url: "yourshop.com",
      mock_title: "Fresh Fades, Zero Wait",
      mock_sub: "Book online in 30 seconds. See prices, barbers, and openings.",
      mock_cta: "Book Now",
      caption: "Your Instagram gets the attention. Your website books the chair.\n\nWe build barbershop sites with booking, prices, and your best reviews front and center.\n\nBuilt for the High Desert. Live in days, not months.\n\nLink in bio.",
      hashtags: ["#Barbershop", "#Victorville", "#HighDesert", "#SmallBusiness", "#WebDesign", "#ShopLocal", "#Hesperia"],
      alt_text: "Showcase graphic of a barbershop website mockup in a browser frame on a dark desert background.",
    },
  };
  return canned[pillar.template];
}

// ---------- render ----------
async function renderPNG(templateName, data, outPath) {
  const html = buildHTML(templateName, data);
  const browser = await puppeteer.launch({
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--force-color-profile=srgb"],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1080, height: 1080, deviceScaleFactor: 1 });
    await page.setContent(html, { waitUntil: "networkidle0" });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: outPath, type: "png" });
  } finally {
    await browser.close();
  }
}

// ---------- main ----------
(async () => {
  const cfg = themes();
  const st = state();
  const { pillar, topic, tIdx } = pickTopic(cfg, st);

  console.log(`Pillar: ${pillar.id} | Topic: ${topic}`);
  const copy = await writeCopy(cfg, pillar, topic);

  // brand fields available to every template
  copy.handle = cfg.brand.handle;
  copy.url = cfg.brand.url;

  fs.mkdirSync(PENDING, { recursive: true });
  const imgPath = path.join(PENDING, "post.png");
  await renderPNG(pillar.template, copy, imgPath);

  const caption =
    `${copy.caption}\n\n` +
    `${(copy.hashtags || []).join(" ")}`;

  saveJSON(path.join(PENDING, "post.json"), {
    createdAt: new Date().toISOString(),
    pillar: pillar.id,
    template: pillar.template,
    topic,
    caption,
    alt_text: copy.alt_text || "",
    copy,
  });

  // advance rotation
  st.pillarIndex = (st.pillarIndex + 1) % cfg.pillars.length;
  st.topicIndexes[pillar.id] = tIdx + 1;
  st.postCount += 1;
  saveState(st);

  console.log(`Generated ${imgPath}`);
  console.log(`Caption:\n${caption}`);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
