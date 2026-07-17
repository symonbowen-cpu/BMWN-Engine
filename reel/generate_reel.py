#!/usr/bin/env python3
"""
generate_reel.py - creates today's Instagram Reel into out/reel/.
No voiceover: kinetic text cards paced to reading speed, with sound design
(pop on hook, whoosh on transitions, riser into the CTA) over a music bed.

Pipeline:
  1. Pick next pillar/topic (content/reel_state.json rotation)
  2. Claude writes hook + 3 beats + CTA + caption
  3. Each part renders as a 1080x1920 branded slide (cairosvg, oversized for zoom)
  4. ffmpeg: Ken Burns motion per slide, fades, progress bar
  5. Audio: assets/music track (looped, faded) + assets/sfx hits at slide starts

Env:
  ANTHROPIC_API_KEY  - required unless DRY_RUN=1
  DRY_RUN=1          - canned script, no Claude call
"""
import json, os, subprocess, sys, textwrap, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
PENDING = ROOT / "out" / "reel"
SFX = ROOT / "assets" / "sfx"
MUSIC = ROOT / "assets" / "music"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

INK, DUSK = "#0E1420", "#1B2436"
DAWN1, DAWN2 = "#FF6B2C", "#FFB347"
SAND, FAINT = "#EDE6D8", "#8B93A5"

def load(p): return json.loads(Path(p).read_text())
def save(p, obj): Path(p).write_text(json.dumps(obj, indent=2) + "\n")

def pick_topic(cfg, st):
    pillars = cfg["pillars"]
    pillar = pillars[st["pillarIndex"] % len(pillars)]
    t_idx = st["topicIndexes"].get(pillar["id"], 0)
    topic = pillar["topics"][t_idx % len(pillar["topics"])]
    return pillar, topic, t_idx

# ---------------- script via Claude ----------------
def write_script(cfg, pillar, topic):
    if os.environ.get("DRY_RUN") == "1":
        return {
            "hook": "You're losing customers to a 10-minute fix.",
            "beats": [
                "Google your business name right now. What shows up is what every customer sees first.",
                "Wrong hours, no photos, no reviews? People assume you're closed and call the next shop.",
                "Claim your free Google Business Profile. Photos, hours, reviews.",
            ],
            "cta": "Follow for one free tool every day.",
            "caption": "The free 10-minute fix that wins customers.\n\nGoogle your business right now. If the hours are wrong or there are no photos, you're handing customers to the shop next door.\n\nFollow for a free tool every day.\n\n#HighDesert #SmallBusiness #Victorville #LocalSEO #WebDesign #ShopLocal",
        }

    brand = cfg["brand"]
    prompt = f"""You write Instagram Reels scripts for {brand['name']} ({brand['url']}), a web design service for small businesses in {brand['region']} of California ({', '.join(brand['cities'])}).

NON-NEGOTIABLE FRAMING: Every Reel is marketing for {brand['name']}, a company that BUILDS WEBSITES. The viewer is a small business owner we want to hire us. Never write copy that sounds like an advertisement for some other business. Never invent fake tools, stats, or prices.

Voice: {brand['voice']}

Today's pillar: {pillar['id']}
Goal: {pillar['goal']}
Topic: {topic}

This Reel is TEXT-ON-SCREEN with no narration, so every line must read fast. Rules:
- hook: max 8 words, stops the scroll. No greetings.
- beats: exactly 3 lines, each max 16 words, one idea each. Punchy. No emojis, no em dashes.
- cta: max 7 words (follow / DM us SITE / link in bio - vary it).
- caption: 3-4 short lines for the post caption. Hook first, soft CTA last. Then 8-12 hashtags drawn from: {' '.join(cfg.get('hashtag_bank', []))} plus 1-2 topical ones.
Respond ONLY with a JSON object: {{"hook": "...", "beats": ["...","...","..."], "cta": "...", "caption": "..."}}"""

    import urllib.request
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": MODEL, "max_tokens": 1000,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"content-type": "application/json",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
    return json.loads(text.replace("```json", "").replace("```", "").strip())

# ---------------- slides ----------------
def esc(s): return html.escape(s, quote=True)

def slide_svg(kind, text, brand):
    W, H = 1080, 1920
    ridge = f'''
      <path d="M0,1770 L150,1740 L300,1764 L470,1726 L620,1758 L780,1720 L920,1752 L1080,1734 L1080,1920 L0,1920 Z" fill="#151D2C"/>
      <path d="M0,1770 L150,1740 L300,1764 L470,1726 L620,1758 L780,1720 L920,1752 L1080,1734" fill="none" stroke="url(#dawn)" stroke-width="4"/>
      <text x="90" y="1868" font-family="JetBrains Mono" font-size="30" fill="{SAND}" letter-spacing="2">{esc(brand['handle'])}</text>
      <text x="990" y="1868" font-family="JetBrains Mono" font-size="30" fill="{DAWN2}" letter-spacing="2" text-anchor="end">{esc(brand['url'])}</text>'''

    if kind == "hook":
        lines = textwrap.wrap(text, 14)
        fs, lh, y0 = 118, 140, 800 - (len(lines) - 1) * 70
        color = SAND
        eyebrow = f'<text x="90" y="380" font-family="JetBrains Mono" font-size="36" fill="{DAWN2}" letter-spacing="10">DAILY TOOL</text>'
    elif kind == "cta":
        lines = textwrap.wrap(text, 18)
        fs, lh, y0 = 96, 116, 900 - (len(lines) - 1) * 58
        color = DAWN2
        eyebrow = ""
    else:
        lines = textwrap.wrap(text, 20)
        fs, lh, y0 = 80, 108, 880 - (len(lines) - 1) * 54
        color = SAND
        eyebrow = ""

    tspans = "".join(
        f'<text x="90" y="{y0 + i*lh}" font-family="Archivo Black" font-size="{fs}" fill="{color}">{esc(l)}</text>'
        for i, l in enumerate(lines)
    )
    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0E1420"/><stop offset="0.6" stop-color="#101828"/><stop offset="1" stop-color="#1A2030"/>
  </linearGradient>
  <linearGradient id="dawn" x1="0" y1="0" x2="1080" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{DAWN1}"/><stop offset="0.5" stop-color="{DAWN2}"/><stop offset="1" stop-color="{DAWN1}"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.5" cy="0.95" r="0.6">
    <stop offset="0" stop-color="{DAWN1}" stop-opacity="0.40"/>
    <stop offset="0.45" stop-color="{DAWN2}" stop-opacity="0.14"/>
    <stop offset="0.75" stop-color="{INK}" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#sky)"/>
<ellipse cx="540" cy="1920" rx="820" ry="500" fill="url(#glow)"/>
{eyebrow}
{tspans}
{ridge}
</svg>'''

def render_slides(script, brand, outdir):
    import cairosvg
    parts = [("hook", script["hook"])] + [("beat", b) for b in script["beats"]] + [("cta", script["cta"])]
    paths = []
    for i, (kind, text) in enumerate(parts):
        p = outdir / f"slide_{i:02d}.png"
        cairosvg.svg2png(bytestring=slide_svg(kind, text, brand).encode(),
                         write_to=str(p), output_width=1350, output_height=2400)
        paths.append(p)
    return parts, paths

# ---------------- pacing (reading speed, no narration) ----------------
def part_duration(kind, text):
    words = len(text.split())
    base = 0.9 + words * 0.34            # ~3 words/sec reading + settle time
    if kind == "hook":
        base += 0.4                       # let the hook breathe
    return max(1.8, min(base, 6.0))

# ---------------- assembly ----------------
def assemble(parts, paths, out_mp4):
    FPS = 30
    work = out_mp4.parent
    durs = [part_duration(k, t) for k, t in parts]
    total = sum(durs)

    # video: Ken Burns per slide + fades + progress bar
    clips = []
    for i, (p, d) in enumerate(zip(paths, durs)):
        frames = max(int(round(d * FPS)), FPS)
        zexpr = f"1+0.10*on/{frames}" if i % 2 == 0 else f"1.10-0.10*on/{frames}"
        fade_out_start = max(d - 0.28, 0.1)
        vf = (f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s=1080x1920:fps={FPS},"
              f"fade=t=in:st=0:d=0.22,fade=t=out:st={fade_out_start:.2f}:d=0.28,"
              f"format=yuv420p")
        clip = work / f"clip_{i:02d}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(p),
                        "-vf", vf, "-frames:v", str(frames),
                        "-c:v", "libx264", "-preset", "fast", str(clip)],
                       check=True, capture_output=True)
        clips.append(clip)

    # ---- audio bed: SFX synced to slide starts + optional music ----
    # offsets in ms for adelay
    offsets, t = [], 0.0
    for d in durs:
        offsets.append(int(t * 1000))
        t += d

    sfx_plan = []  # (file, offset_ms, volume)
    if (SFX / "pop.wav").exists():
        sfx_plan.append((SFX / "pop.wav", offsets[0], 0.9))            # hook lands
    whoosh = SFX / "whoosh.wav"
    thud = SFX / "thud.wav"
    for i in range(1, len(parts) - 1):                                  # each beat transition
        if whoosh.exists():
            sfx_plan.append((whoosh, max(offsets[i] - 150, 0), 0.8))
        if thud.exists():
            sfx_plan.append((thud, offsets[i] + 60, 0.7))
    if (SFX / "riser.wav").exists():                                    # into the CTA
        sfx_plan.append((SFX / "riser.wav", max(offsets[-1] - 500, 0), 0.7))

    tracks = sorted([p for ext in ("*.mp3", "*.m4a", "*.wav") for p in MUSIC.glob(ext)]) if MUSIC.exists() else []

    inputs, filters, mix_labels = [], [], []
    idx = 0
    if tracks:
        inputs += ["-stream_loop", "-1", "-i", str(tracks[0])]
        filters.append(f"[{idx}:a]volume=0.35,afade=t=in:d=0.6,"
                       f"afade=t=out:st={max(total-1.4,0):.2f}:d=1.4,"
                       f"atrim=0:{total:.2f}[m]")
        mix_labels.append("[m]")
        idx += 1
    for j, (f, off, vol) in enumerate(sfx_plan):
        inputs += ["-i", str(f)]
        filters.append(f"[{idx}:a]volume={vol},adelay={off}|{off}[s{j}]")
        mix_labels.append(f"[s{j}]")
        idx += 1

    audio = work / "bed.m4a"
    if mix_labels:
        filt = ";".join(filters) + ";" + "".join(mix_labels) + \
               f"amix=inputs={len(mix_labels)}:duration=longest:normalize=0,atrim=0:{total:.2f}[aout]"
        subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", filt,
                        "-map", "[aout]", "-c:a", "aac", str(audio)],
                       check=True, capture_output=True)
    else:  # no assets at all: near-silent bed so the container still has audio
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-t", f"{total:.2f}", "-c:a", "aac", str(audio)],
                       check=True, capture_output=True)

    # concat video + attach audio + progress bar
    n = len(clips)
    cin = []
    for c in clips:
        cin += ["-i", str(c)]
    vconcat = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vcat];"
    bar = f"[vcat]drawbox=x=0:y=ih-12:w='iw*t/{total:.2f}':h=12:color=0xFF6B2C@0.9:t=fill[vout]"
    subprocess.run(["ffmpeg", "-y", *cin, "-i", str(audio),
                    "-filter_complex", vconcat + bar,
                    "-map", "[vout]", "-map", f"{n}:a",
                    "-c:v", "libx264", "-r", str(FPS), "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", "-movflags", "+faststart",
                    str(out_mp4)], check=True, capture_output=True)
    return total

# ---------------- main ----------------
def main():
    cfg = load(CONTENT / "themes.json")
    st = load(CONTENT / "reel_state.json")
    pillar, topic, t_idx = pick_topic(cfg, st)
    print(f"Pillar: {pillar['id']} | Topic: {topic}")

    script = write_script(cfg, pillar, topic)
    PENDING.mkdir(parents=True, exist_ok=True)

    parts, slide_paths = render_slides(script, cfg["brand"], PENDING)
    out_mp4 = PENDING / "reel.mp4"
    total = assemble(parts, slide_paths, out_mp4)

    caption = script.get("caption") or (script["hook"] + "\n\n" + script["cta"])
    meta = {"caption": caption, "pillar": pillar["id"], "topic": topic,
            "duration_s": round(total, 1), "script": script}
    save(PENDING / "meta.json", meta)

    st["pillarIndex"] = (st["pillarIndex"] + 1) % len(cfg["pillars"])
    st["topicIndexes"][pillar["id"]] = t_idx + 1
    st["postCount"] = st.get("postCount", 0) + 1
    save(CONTENT / "reel_state.json", st)

    print(f"Built {out_mp4} ({total:.1f}s, no voiceover, SFX bed)")
    print(f"Caption: {caption[:80]}...")

if __name__ == "__main__":
    main()
