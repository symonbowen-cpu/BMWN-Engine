#!/usr/bin/env python3
"""
publish_reel.py - publishes out/reel/reel.mp4 to Instagram as a Reel,
then shares the same video to the Story.

Env:
  IG_USER_ID, IG_ACCESS_TOKEN   - required
  IG_GRAPH_HOST                 - graph.instagram.com (Route A) or graph.facebook.com
  REEL_VIDEO_URL                - public URL of the mp4 (release asset)
  SHARE_TO_STORY                - "false" to skip the story (default: share)
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = os.environ.get("IG_GRAPH_HOST", "graph.facebook.com")
BASE = f"https://{HOST}/v21.0"

def call(method, endpoint, params, fatal=True):
    q = urllib.parse.urlencode(params)
    url = f"{BASE}/{endpoint}"
    req = urllib.request.Request(f"{url}?{q}") if method == "GET" else \
          urllib.request.Request(url, data=q.encode(), method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = f"Graph API error on {endpoint}: {e.read().decode()}"
        if fatal:
            sys.exit(msg)
        print(f"::warning::{msg}")
        return None

def wait_finished(cid, token, tries=30):
    for _ in range(tries):
        time.sleep(10)
        status = call("GET", cid, {"fields": "status_code", "access_token": token}, fatal=False)
        code = status.get("status_code") if status else None
        print(f"  status: {code}")
        if code == "FINISHED":
            return True
        if code == "ERROR":
            return False
    return False

def main():
    uid = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    video_url = os.environ["REEL_VIDEO_URL"]
    meta = json.loads((ROOT / "out" / "reel" / "meta.json").read_text())

    # ---- 1. Reel ----
    print(f"Creating REELS container from {video_url}")
    container = call("POST", f"{uid}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": meta["caption"],
        "share_to_feed": "true",
        "access_token": token,
    })
    cid = container["id"]
    print(f"Container: {cid}")
    if not wait_finished(cid, token):
        sys.exit("Instagram failed to process the reel video.")
    pub = call("POST", f"{uid}/media_publish", {"creation_id": cid, "access_token": token})
    print(f"Published Reel! Media ID: {pub['id']}")

    # ---- 2. Story share (best-effort; never fails the run) ----
    if os.environ.get("SHARE_TO_STORY", "true").lower() != "false":
        story = call("POST", f"{uid}/media", {
            "media_type": "STORIES",
            "video_url": video_url,
            "access_token": token,
        }, fatal=False)
        if story:
            if wait_finished(story["id"], token, tries=18):
                spub = call("POST", f"{uid}/media_publish",
                            {"creation_id": story["id"], "access_token": token}, fatal=False)
                if spub:
                    print(f"Shared to Story! Media ID: {spub['id']}")
            else:
                print("::warning::Story video processing failed (reel is live).")

if __name__ == "__main__":
    main()
