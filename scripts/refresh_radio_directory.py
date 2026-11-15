#!/usr/bin/env python3
"""Refresh the Sanket public radio directory with streams that answer HTTP checks."""
import json, os, urllib.request, urllib.error
from datetime import datetime, timezone

SOURCE = "https://raw.githubusercontent.com/codito/akashvani/master/stations.json"
OUT = "website/data/radio-directory.json"
TOP_IDS = {"bbc-world-service", "npr-news", "vividh-bharati", "fm-gold-delhi", "air-news"}

def fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent":"SanketRadioHealthCheck/1.0","Range":"bytes=0-1023"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read(1024), response.headers.get("Content-Type","")

def main():
    with urllib.request.urlopen(SOURCE, timeout=15) as response:
        raw = json.loads(response.read().decode("utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("stations", raw.get("data", []))
    good, seen = [], set()
    for row in rows:
        name = str(row.get("name") or row.get("station_name") or "").strip()
        url = str(row.get("stream_url") or row.get("url") or "").strip()
        if not name or not url.startswith("https://") or url in seen:
            continue
        seen.add(url)
        try:
            status, body, ctype = fetch(url)
            # Accept an HLS playlist or an audio response; reject HTML error pages.
            valid = status in (200, 206) and bool(body) and (
                b"#EXTM3U" in body[:512] or "audio" in ctype.lower()
                or "mpegurl" in ctype.lower() or "octet-stream" in ctype.lower()
                or url.lower().endswith((".mp3", ".aac", ".m3u8", ".pls"))
            )
            if not valid:
                continue
            good.append({
                "id": "air-" + str(row.get("epg_id") or len(good)+1),
                "name": name,
                "region": str(row.get("state") or row.get("region") or "India"),
                "language": str(row.get("language") or "Various"),
                "url": url,
                "type": "hls" if ".m3u8" in url.lower() or b"#EXTM3U" in body[:512] else "mp3"
            })
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": SOURCE,
               "checked": len(seen), "available": len(good), "stations": good}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Checked {len(seen)} stations; {len(good)} playable endpoints published.")

if __name__ == "__main__":
    main()
