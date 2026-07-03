# BuildMyWebNow Content Engine — Setup Guide

One-time setup is about 30–45 minutes. After that, the engine runs itself.

---

## Part 1 — Instagram & Meta (the manual part)

### 1. Create the Instagram account
1. Create the account (suggested handle: **@buildmywebnow**) in the Instagram app.
2. Fill out the profile: logo as avatar, bio ("Websites for High Desert small businesses. Veteran-owned. Live in days, not months."), link to buildmywebnow.com.
3. **Profile → Settings → Account type and tools → Switch to professional account → Business.**

### 2. Choose your route
Since Meta's 2024 update there are two ways to get publishing access:

| | Route A: No Facebook Page | Route B: Facebook Page linked |
|---|---|---|
| Login product | Business Login for Instagram | Facebook Login for Business |
| API host | `graph.instagram.com` | `graph.facebook.com` (default) |
| Token life | ~60 days, auto-refreshed by the included `refresh-token.yml` workflow | **Never expires** (System User token) |
| Extra setup | One GitHub PAT secret for token refresh | Create + link a Facebook Page (~10 min) |

Route B is the most set-and-forget. Route A avoids Facebook entirely. Both are fully supported by this engine.

---

#### Route A (no Facebook Page)
1. Go to **developers.facebook.com** → My Apps → **Create App** → Business type.
2. In the app dashboard add the **Instagram** product → **API setup with Instagram login**.
3. Under **Generate access tokens**, add your Instagram account and generate a token with `instagram_business_basic` and `instagram_business_content_publish`. Copy it — this is **IG_ACCESS_TOKEN**. The same screen shows your account's ID — that's **IG_USER_ID**.
4. In the repo, set an Actions **variable** `IG_GRAPH_HOST` = `graph.instagram.com` (used by publish.js).
5. Create a GitHub **fine-grained PAT** for this repo with *Secrets: read & write*, save it as secret `REPO_ADMIN_TOKEN`. The included `refresh-token.yml` workflow then refreshes your token every 3 weeks automatically — it never lapses.
6. Skip to Part 2.

#### Route B (Facebook Page — never-expiring token)
1. Create a Facebook Page named "BuildMyWebNow" (facebook.com/pages/create).
2. In Instagram: **Settings → Business tools and controls → Connect a Facebook Page** → select it.
3. Delete `.github/workflows/refresh-token.yml` — you won't need it.
4. Continue with steps 3–5 below.

### 3. Create a Meta developer app (Route B)
1. Go to **developers.facebook.com** → My Apps → **Create App**.
2. Choose the **Business** app type. Name it anything (e.g. "BMWN Publisher").
3. In the app dashboard, add the **Instagram Graph API** product (and **Facebook Login for Business** if prompted).

### 4. Get a never-expiring access token (Route B: System User)
This avoids the 60-day token expiry problem entirely.
1. Go to **business.facebook.com → Settings (Business Settings) → Users → System Users**.
2. Create a system user (Admin role).
3. Click **Add Assets** → assign your Facebook Page and your app to this system user with full control.
4. Click **Generate New Token** → select your app → set expiration to **Never** → check these permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
5. Copy the token somewhere safe. This is your **IG_ACCESS_TOKEN**.

> Alternative if System Users aren't available to you: generate a user token in the Graph API Explorer with the same permissions, then exchange it for a long-lived token (60 days). It works, but you'll need to re-generate it every ~2 months. The System User route is set-and-forget.

### 5. Get your Instagram User ID (Route B)
In the **Graph API Explorer** (developers.facebook.com/tools/explorer), with your token selected, run:

```
GET me/accounts                        → copy your Page's "id"
GET {page-id}?fields=instagram_business_account
```

The number returned under `instagram_business_account.id` is your **IG_USER_ID**.

### 6. Warm the account (important)
Post the first **5 or so posts manually** over the first week before turning the engine on. Brand-new accounts that start API-posting on day one can get flagged. Use the engine's generated images if you like — run it in approval mode and post the drafts by hand.

---

## Part 2 — GitHub (the 10-minute part)

### 1. Create the repo
1. Create a **public** repo (e.g. `bmwn-content-engine`). Public matters: Instagram fetches the post image from `raw.githubusercontent.com`, which requires the file to be publicly readable.
   - If you want the repo private instead, host the image on your Vercel site: have the workflow copy `post.png` into your website repo's `/public/ig/` folder and set the `IMAGE_PUBLIC_URL` env in the workflow accordingly.
2. Push this folder to it:

```bash
cd bmwn-content-engine
git init && git add -A && git commit -m "content engine v1"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/bmwn-content-engine.git
git push -u origin main
```

### 2. Add secrets
Repo → **Settings → Secrets and variables → Actions → Secrets** → add:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your key from console.anthropic.com |
| `IG_USER_ID` | From Part 1, step 5 |
| `IG_ACCESS_TOKEN` | From Part 1, step 4 |

### 3. Set the mode
Repo → **Settings → Secrets and variables → Actions → Variables** → add:

| Variable | Value |
|---|---|
| `AUTO_PUBLISH` | `false` to start (approval mode) |

Flip it to `true` when you're ready for full autonomy.

### 4. Enable Actions & test
1. Repo → **Actions** tab → enable workflows if prompted.
2. Open **Daily Instagram Post** → **Run workflow** (manual trigger).
3. In approval mode you'll get a GitHub **issue** with the image preview and caption.
   - Comment `/approve` → it publishes to Instagram and closes the issue.
   - Comment `/skip` → it discards the draft.
4. Install the **GitHub mobile app** — you'll get a push notification for each daily issue and can approve from your phone in ~5 seconds.

---

## Daily operation

| Mode | What happens every day at 9 AM PT |
|---|---|
| Approval (`AUTO_PUBLISH=false`) | Engine generates image + caption → opens a GitHub issue → you comment `/approve` or `/skip` from your phone |
| Full auto (`AUTO_PUBLISH=true`) | Engine generates and publishes. You do nothing. |

## Customizing

- **Content:** edit `content/themes.json` — add/remove pillars, topics, hashtags, or tweak the brand voice line. The engine rotates through pillars in order and through each pillar's topics in order, so nothing repeats until the whole list cycles.
- **Design:** edit `templates/*.html` and `templates/_base.html`. Colors live in the `:root` CSS variables.
- **Schedule:** edit the cron line in `.github/workflows/daily-post.yml`. Want 3 posts/week instead of daily? Use `0 16 * * 1,3,5`.
- **Test locally without posting:** `npm install && npm run generate:dry` renders a card with canned copy into `out/pending/` (requires Chrome; Puppeteer downloads it automatically on a normal machine).

## Costs

- GitHub Actions: free tier covers this easily (~3 min/day).
- Claude API: one small call per day — a few cents per month.
- Instagram API: free.

## Troubleshooting

- **Publish fails with "media not ready"** — the retry loop usually handles it; if not, the image URL may not be public. Confirm the repo is public and the raw URL opens in an incognito browser.
- **Token errors after ~60 days** — you used a long-lived user token instead of a System User token. Do Part 1 step 4 the System User way.
- **Rate limits** — Instagram allows up to 50 API-published posts per 24h. One per day is nowhere near it.
