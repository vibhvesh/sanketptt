#!/usr/bin/env python3
"""Build the public Sanket radio catalogue from Akashvani and Radio Browser."""
import json, os, re, hashlib, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

AIR_SOURCE = "https://raw.githubusercontent.com/codito/akashvani/master/stations.json"
RB_API = "https://de1.api.radio-browser.info"
OUT = "website/data/radio-directory.json"
UA = "SanketGlobalRadioDirectory/2.0 (public catalogue)"

def get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def normalise_air(row):
    name = str(row.get("name") or row.get("station_name") or "").strip()
    url = str(row.get("stream_url") or row.get("url") or "").strip()
    if not name or not url.startswith(("https://", "http://")): return None
    return {"id": "air-" + str(row.get("epg_id") or hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]),
            "name": name, "country": "India",
            "region": str(row.get("state") or row.get("region") or "India"),
            "language": [x.strip() for x in re.split(r"[,;/]", str(row.get("language") or "Various")) if x.strip()],
            "type": ["Radio"], "tags": ["akashvani", "india"],
            "url": url, "homepage": "", "codec": "HLS" if ".m3u8" in url else "",
            "bitrate": 0, "geo_lat": None, "geo_long": None,
            "source": "Akashvani catalogue", "verified": "catalogue-listed"}

def normalise_rb(s):
    url = str(s.get("url_resolved") or s.get("url") or "").strip()
    name = str(s.get("name") or "").strip()
    if not name or not url.startswith(("https://", "http://")): return None
    tags = [x.strip().lower() for x in str(s.get("tags") or "").split(",") if x.strip()]
    languages = [x.strip() for x in str(s.get("language") or "").split(",") if x.strip()]
    lat = s.get(" geo_lat") or s.get("geo_lat")
    lon = s.get("geo_long")
    try: lat = float(lat) if lat not in (None, "") else None
    except (TypeError, ValueError): lat = None
    try: lon = float(lon) if lon not in (None, "") else None
    except (TypeError, ValueError): lon = None
    return {"id": "rb-" + str(s.get("stationuuid") or abs(hash(url))),
            "name": name, "country": str(s.get("country") or "Unknown"),
            "countrycode": str(s.get("countrycode") or "").upper(),
            "region": str(s.get("state") or ""), "city": "",
            "language": languages or ["Unknown"], "type": tags or ["General"],
            "tags": tags, "url": url, "homepage": str(s.get("homepage") or ""),
            "favicon": str(s.get("favicon") or ""), "codec": str(s.get("codec") or ""),
            "bitrate": int(s.get("bitrate") or 0), "geo_lat": lat, "geo_long": lon,
            "clickcount": int(s.get("clickcount") or 0), "votes": int(s.get("votes") or 0),
            "source": "Radio Browser community directory",
            "verified": "directory-listed"}

def main():
    stations = {}
    sources = {}
    try:
        raw = get_json(AIR_SOURCE)
        rows = raw if isinstance(raw, list) else raw.get("stations", raw.get("data", []))
        for row in rows:
            item = normalise_air(row)
            if item: stations[item["url"]] = item
        sources["akashvani_candidates"] = len(rows)
    except Exception as e:
        print("Akashvani source unavailable:", e)
        sources["akashvani_error"] = str(e)

    # Radio Browser's top-click feed gives a broad, global public snapshot.
    try:
        global_rows = get_json(RB_API + "/json/stations/topclick/10000")
        sources["radio_browser_candidates"] = len(global_rows)
        for row in global_rows:
            item = normalise_rb(row)
            if item:
                old = stations.get(item["url"])
                if old:
                    old.update({k:v for k,v in item.items() if v not in (None, "", [], ["Unknown"])})
                    old["source"] = "Akashvani + Radio Browser"
                else:
                    stations[item["url"]] = item
    except Exception as e:
        print("Radio Browser source unavailable:", e)
        sources["radio_browser_error"] = str(e)

    all_items = sorted(stations.values(), key=lambda x: (x.get("country",""), x.get("name","").casefold()))
    payload = {"schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(),
               "directory_name": "Sanket Global Radio Directory",
               "description": "Public catalogue snapshot. Stream availability changes; verify at tune time.",
               "sources": sources, "station_count": len(all_items),
               "countries": len({x.get("country") for x in all_items}),
               "stations": all_items}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Published", len(all_items), "stations across", payload["countries"], "countries")

if __name__ == "__main__":
    main()
