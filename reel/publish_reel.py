#!/usr/bin/env python3
"""
publish_reel.py - publishes out/reel/reel.mp4 to Instagram as a Reel.

The video must already be at a PUBLIC url (the workflow uploads it as a GitHub
release asset and passes REEL_VIDEO_URL).

Env:
  IG_USER_ID, IG_ACCESS_TOKEN   - same secrets as the feed engine
  IG_GRAPH_HOST                 - graph.instagram.com (Route A) or graph.facebook.com
  REEL_VIDEO_URL                - public URL of the mp4
"""
import json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = os.environ.get("IG_GRAPH_HOST", "graph.facebook.com")
BASE = f"https://{HOST}/v21.0"

def call(method, endpoint, params):
    q = urllib.parse.urlencode(params)
    url = f"{BASE}/{endpoint}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{q}")
    else:
        req = urllib.request.Request(url, data=q.encode(), method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Graph API error on {endpoint}: {e.read().decode()}")

def main():
    uid = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    video_url = os.environ["REEL_VIDEO_URL"]
    meta = json.loads((ROOT / "out" / "reel" / "meta.json").read_text())

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

    # poll until Instagram finishes processing the video
    for attempt in range(30):
        time.sleep(10)
        status = call("GET", cid, {"fields": "status_code", "access_token": token})
        code = status.get("status_code")
        print(f"  status: {code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            sys.exit("Instagram failed to process the video (check format/duration).")
    else:
        sys.exit("Timed out waiting for video processing.")

    pub = call("POST", f"{uid}/media_publish", {"creation_id": cid, "access_token": token})
    print(f"Published Reel! Media ID: {pub['id']}")

if __name__ == "__main__":
    main()
