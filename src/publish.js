/**
 * publish.js — publishes out/pending/ to Instagram feed, then shares to Story.
 *
 * Env:
 *   IG_USER_ID, IG_ACCESS_TOKEN — required
 *   IG_GRAPH_HOST               — graph.instagram.com (Route A) or graph.facebook.com
 *   IMAGE_PUBLIC_URL            — public URL of the post image (release asset)
 *   SHARE_TO_STORY              — "false" to skip the story (default: share)
 */
const fs = require("fs");
const path = require("path");
const { PENDING, PUBLISHED, loadJSON, saveJSON } = require("./lib");

const HOST = process.env.IG_GRAPH_HOST || "graph.facebook.com";
const GRAPH = `https://${HOST}/v21.0`;

async function graph(endpoint, params) {
  const url = new URL(`${GRAPH}/${endpoint}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  const res = await fetch(url, { method: "POST" });
  const data = await res.json();
  if (!res.ok || data.error) {
    throw new Error(`Graph API error on ${endpoint}: ${JSON.stringify(data.error || data)}`);
  }
  return data;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const { IG_USER_ID, IG_ACCESS_TOKEN, IMAGE_PUBLIC_URL } = process.env;
  if (!IG_USER_ID || !IG_ACCESS_TOKEN) throw new Error("Missing IG_USER_ID or IG_ACCESS_TOKEN");
  if (!IMAGE_PUBLIC_URL) throw new Error("Missing IMAGE_PUBLIC_URL");

  const postPath = path.join(PENDING, "post.json");
  if (!fs.existsSync(postPath)) throw new Error("No pending post found in out/pending/");
  const post = loadJSON(postPath);

  console.log(`Image URL: ${IMAGE_PUBLIC_URL}`);

  // ---- 1. feed post ----
  const container = await graph(`${IG_USER_ID}/media`, {
    image_url: IMAGE_PUBLIC_URL,
    caption: post.caption,
    access_token: IG_ACCESS_TOKEN,
  });
  console.log(`Feed container: ${container.id}`);
  await sleep(8000);

  let published;
  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      published = await graph(`${IG_USER_ID}/media_publish`, {
        creation_id: container.id,
        access_token: IG_ACCESS_TOKEN,
      });
      break;
    } catch (e) {
      if (attempt === 4) throw e;
      console.log(`Publish attempt ${attempt} not ready, retrying in 10s...`);
      await sleep(10000);
    }
  }
  console.log(`Published feed post! Media ID: ${published.id}`);

  // ---- 2. share the same image to Story (best-effort; never fails the run) ----
  if (process.env.SHARE_TO_STORY !== "false") {
    try {
      const storyContainer = await graph(`${IG_USER_ID}/media`, {
        media_type: "STORIES",
        image_url: IMAGE_PUBLIC_URL,
        access_token: IG_ACCESS_TOKEN,
      });
      await sleep(8000);
      const story = await graph(`${IG_USER_ID}/media_publish`, {
        creation_id: storyContainer.id,
        access_token: IG_ACCESS_TOKEN,
      });
      console.log(`Shared to Story! Media ID: ${story.id}`);
    } catch (e) {
      console.log(`::warning::Story share failed (feed post is live): ${e.message}`);
    }
  }

  // ---- 3. archive ----
  const stamp = new Date().toISOString().slice(0, 10);
  fs.mkdirSync(PUBLISHED, { recursive: true });
  if (fs.existsSync(path.join(PENDING, "post.png"))) {
    fs.renameSync(path.join(PENDING, "post.png"), path.join(PUBLISHED, `${stamp}.png`));
  }
  post.publishedAt = new Date().toISOString();
  post.mediaId = published.id;
  saveJSON(path.join(PUBLISHED, `${stamp}.json`), post);
  fs.unlinkSync(postPath);
  console.log(`Archived to out/published/${stamp}.*`);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
