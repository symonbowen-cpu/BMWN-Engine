# BuildMyWebNow Content Engine

Autonomous daily Instagram content for [buildmywebnow.com](https://buildmywebnow.com).

**How it works:** a GitHub Action runs daily → rotates through 5 content pillars →
Claude writes the copy in the BMWN brand voice → Puppeteer renders a branded
1080x1080 card ("digital dawn over the Mojave" design system) → the post is either
published straight to Instagram or sent to a GitHub issue for one-tap approval.

- Setup: see [SETUP.md](SETUP.md)
- Content & voice: `content/themes.json`
- Card designs: `templates/`
- Mode switch: repo variable `AUTO_PUBLISH` (`true` = fully autonomous)

```
daily cron ─► generate.js ─► commit image ─► AUTO_PUBLISH?
                                              ├─ true  ─► publish.js ─► Instagram
                                              └─ false ─► GitHub issue ─► /approve ─► Instagram
```
