#!/usr/bin/env python3
"""
generate_reel.py - creates today's Instagram Reel into out/pending/.

Pipeline:
  1. Pick next pillar/topic (round-robin via content/state.json)
  2. Claude writes a script: hook + 3-4 beats + CTA, plus title/description/tags
  3. Each beat is rendered as a vertical 1080x1920 branded slide (cairosvg)
  4. Each beat is voiced with edge-tts (free Microsoft neural voices)
  5. ffmpeg assembles slides timed to narration into out/pending/short.mp4

Env:
  ANTHROPIC_API_KEY  - required unless DRY_RUN=1
  DRY_RUN=1          - canned script, no Claude call
  SILENT_TTS=1       - replace TTS with silence (for testing without network TTS)
"""
import json, os, subprocess, sys, textwrap, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
PENDING = ROOT / "out" / "reel"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
VOICE = os.environ.get("TTS_VOICE", "en-US-ChristopherNeural")  # deep, confident male

INK, DUSK = "#0E1420", "#1B2436"
DAWN1, DAWN2 = "#FF6B2C", "#FFB347"
SAND, FAINT = "#EDE6D8", "#8B93A5"

# ---------------- rotation ----------------
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
                "Claim your free Google Business Profile. Add photos, fix your hours, reply to reviews.",
            ],
            "cta": "Follow for one free tool for your business every day.",
            "caption": "The free 10-minute fix that wins customers.\n\nGoogle your business right now. If the hours are wrong or there are no photos, you're handing customers to the shop next door.\n\nFollow for a free tool every day.",
        }

    brand = cfg["brand"]
    prompt = f"""You write Instagram Reels scripts for {brand['name']} ({brand['url']}), a web design service for small businesses in {brand['region']} of California ({', '.join(brand['cities'])}).

NON-NEGOTIABLE FRAMING: Every Reel is marketing for {brand['name']}, a company that BUILDS WEBSITES. The viewer is a small business owner we want to hire us. Never write copy that sounds like an advertisement for some other business. Never invent fake tools, stats, or prices.

Voice: {brand['voice']}

Today's pillar: {pillar['id']}
Goal: {pillar['goal']}
Topic: {topic}

Write a 20-35 second Reel script. Rules:
- hook: one line, max 10 words, stops the scroll. No greetings.
- beats: exactly 3 short paragraphs, each max 26 spoken words, one idea each. Plain speech, contractions fine, no emojis, no em dashes.
- cta: one short line (follow / DM us SITE / link in bio - vary it).
- caption: 3-4 short lines for the post caption. Hook first. End with a soft CTA. Then 8-12 hashtags drawn from: {' '.join(cfg.get('hashtag_bank', []))} plus 1-2 topical ones.
Respond ONLY with a JSON object: {{"hook": "...", "beats": ["...","...","..."], "cta": "...", "caption": "..."}}"""

    import urllib.request
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": MODEL, "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
    return json.loads(text.replace("```json", "").replace("```", "").strip())

# ---------------- slide rendering ----------------
def esc(s): return html.escape(s, quote=True)

def wrap_lines(text, width):
    return textwrap.wrap(text, width=width)

def slide_svg(kind, text, brand):
    """1080x1920 vertical slide. kind: hook|beat|cta"""
    W, H = 1080, 1920
    ridge = f'''
      <path d="M0,1770 L150,1740 L300,1764 L470,1726 L620,1758 L780,1720 L920,1752 L1080,1734 L1080,1920 L0,1920 Z" fill="#151D2C"/>
      <path d="M0,1770 L150,1740 L300,1764 L470,1726 L620,1758 L780,1720 L920,1752 L1080,1734" fill="none" stroke="url(#dawn)" stroke-width="4"/>
      <text x="90" y="1868" font-family="JetBrains Mono" font-size="30" fill="{SAND}" letter-spacing="2">{esc(brand['handle'])}</text>
      <text x="990" y="1868" font-family="JetBrains Mono" font-size="30" fill="{DAWN2}" letter-spacing="2" text-anchor="end">{esc(brand['url'])}</text>'''

    if kind == "hook":
        lines = wrap_lines(text, 16)
        fs, lh, color, y0 = 108, 128, SAND, 760 - (len(lines) - 1) * 64
        eyebrow = '<text x="90" y="360" font-family="JetBrains Mono" font-size="34" fill="#FFB347" letter-spacing="10">DAILY TOOL</text>'
    elif kind == "cta":
        lines = wrap_lines(text, 22)
        fs, lh, color, y0 = 72, 92, SAND, 860 - (len(lines) - 1) * 46
        eyebrow = f'<circle cx="540" cy="560" r="110" fill="url(#dawnfill)"/><path d="M400,660 L520,600 L640,655 L760,595" fill="none" stroke="{INK}" stroke-width="0" /><path d="M430,668 L540,610 L650,668" fill="none" stroke="{INK}" stroke-width="14" stroke-linecap="round"/>'
    else:  # beat
        lines = wrap_lines(text, 22)
        fs, lh, color, y0 = 68, 96, SAND, 880 - (len(lines) - 1) * 48
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
  <linearGradient id="dawnfill" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{DAWN2}"/><stop offset="1" stop-color="{DAWN1}"/>
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
        # rendered 1.25x oversized (1350x2400) so the Ken Burns zoom stays sharp
        cairosvg.svg2png(bytestring=slide_svg(kind, text, brand).encode(),
                         write_to=str(p), output_width=1350, output_height=2400)
        paths.append(p)
    return parts, paths

# ---------------- TTS ----------------
def tts_segments(parts, outdir):
    """Voice each part; returns list of (audio_path, duration_s)."""
    segs = []
    for i, (_, text) in enumerate(parts):
        mp3 = outdir / f"voice_{i:02d}.mp3"
        if os.environ.get("SILENT_TTS") == "1":
            dur = max(2.2, len(text.split()) / 2.6)  # ~2.6 words/sec
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                            "-t", f"{dur:.2f}", "-q:a", "9", str(mp3)],
                           check=True, capture_output=True)
        else:
            subprocess.run([sys.executable, "-m", "edge_tts", "--voice", VOICE,
                            "--text", text, "--write-media", str(mp3)],
                           check=True, capture_output=True)
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", str(mp3)], capture_output=True, text=True, check=True)
        segs.append((mp3, float(probe.stdout.strip())))
    return segs

# ---------------- assembly (motion version) ----------------
def assemble(paths, segs, out_mp4):
    """Ken Burns zoom on every slide, fade-through-dark transitions, synced
    narration, and a dawn-orange progress bar along the bottom."""
    PAUSE = 0.35
    FPS = 30
    work = out_mp4.parent

    # 1) concat narration with breathing room
    inputs = []
    for mp3, _ in segs:
        inputs += ["-i", str(mp3)]
    n = len(segs)
    filt = "".join(f"[{i}:a]apad=pad_dur={PAUSE}[a{i}];" for i in range(n))
    filt += "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[aout]"
    audio = work / "voice_full.m4a"
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", filt,
                    "-map", "[aout]", "-c:a", "aac", str(audio)], check=True, capture_output=True)

    # optional background music: first mp3/m4a/wav in assets/music, looped,
    # ducked under the voice, faded out at the end
    music_dir = ROOT / "assets" / "music"
    tracks = sorted([p for ext in ("*.mp3", "*.m4a", "*.wav") for p in music_dir.glob(ext)]) if music_dir.exists() else []
    if tracks:
        total_guess = sum(d for _, d in segs) + PAUSE * len(segs)
        mixed = work / "voice_music.m4a"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(audio),
            "-stream_loop", "-1", "-i", str(tracks[0]),
            "-filter_complex",
            f"[1:a]volume=0.12,afade=t=out:st={max(total_guess-1.2,0):.2f}:d=1.2[m];"
            f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[aout]",
            "-map", "[aout]", "-c:a", "aac", str(mixed),
        ], check=True, capture_output=True)
        audio = mixed

    # 2) one motion clip per slide: alternating slow zoom in/out + fades
    clips = []
    for i, (p, (_, dur)) in enumerate(zip(paths, segs)):
        d = dur + PAUSE
        frames = max(int(round(d * FPS)), FPS)
        if i % 2 == 0:
            zexpr = f"1+0.10*on/{frames}"          # slow push in
        else:
            zexpr = f"1.10-0.10*on/{frames}"       # slow pull out
        fade_out_start = max(d - 0.30, 0.1)
        vf = (
            f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s=1080x1920:fps={FPS},"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out_start:.2f}:d=0.30,"
            f"format=yuv420p"
        )
        clip = work / f"clip_{i:02d}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(p),
                        "-vf", vf, "-frames:v", str(frames),
                        "-c:v", "libx264", "-preset", "fast", str(clip)],
                       check=True, capture_output=True)
        clips.append((clip, d))

    # 3) concat clips + audio + progress bar
    total = sum(d for _, d in clips)
    cin = []
    for c, _ in clips:
        cin += ["-i", str(c)]
    vconcat = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vcat];"
    bar = (f"[vcat]drawbox=x=0:y=ih-12:w='iw*t/{total:.2f}':h=12:"
           f"color=0xFF6B2C@0.9:t=fill[vout]")
    subprocess.run(["ffmpeg", "-y", *cin, "-i", str(audio),
                    "-filter_complex", vconcat + bar,
                    "-map", "[vout]", "-map", f"{n}:a",
                    "-c:v", "libx264", "-r", str(FPS), "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", "-movflags", "+faststart",
                    str(out_mp4)], check=True, capture_output=True)

# ---------------- main ----------------
def main():
    cfg = load(CONTENT / "themes.json")
    st = load(CONTENT / "reel_state.json")
    pillar, topic, t_idx = pick_topic(cfg, st)
    print(f"Pillar: {pillar['id']} | Topic: {topic}")

    script = write_script(cfg, pillar, topic)
    PENDING.mkdir(parents=True, exist_ok=True)

    parts, slide_paths = render_slides(script, cfg["brand"], PENDING)
    segs = tts_segments(parts, PENDING)
    out_mp4 = PENDING / "reel.mp4"
    assemble(slide_paths, segs, out_mp4)

    total = sum(d for _, d in segs) + 0.35 * len(segs)
    caption = script.get("caption") or (script["hook"] + "\n\n" + script["cta"])
    meta = {
        "caption": caption,
        "pillar": pillar["id"], "topic": topic,
        "duration_s": round(total, 1),
        "script": script,
    }
    save(PENDING / "meta.json", meta)

    st["pillarIndex"] = (st["pillarIndex"] + 1) % len(cfg["pillars"])
    st["topicIndexes"][pillar["id"]] = t_idx + 1
    st["postCount"] = st.get("postCount", 0) + 1
    save(CONTENT / "reel_state.json", st)

    print(f"Built {out_mp4} ({total:.1f}s)")
    print(f"Caption: {meta['caption'][:80]}...")

if __name__ == "__main__":
    main()
