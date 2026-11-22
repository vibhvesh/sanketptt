#!/usr/bin/env python3
"""Build Sanket's public, browse-ready radio catalogue from public station indexes.

This is a discovery catalogue, not a guarantee that a stream is live or licensed
for rebroadcast. Playback and rebroadcast permissions must be checked separately.
"""
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

RB_API = "https://de1.api.radio-browser.info"
AIR_SOURCE = "https://raw.githubusercontent.com/codito/akashvani/master/stations.json"
OUT = "website/data/radio-directory.json"
UA = "SanketRadioDirectory/3.0 (public catalogue)"
TAGS = [
    "news", "talk", "folk", "jazz", "classical", "party", "pop", "rock",
    "indian", "bollywood", "devotional", "world", "sports", "culture",
    "dance", "electronic", "oldies", "ambient", "country", "reggae",
    "metal", "hip-hop", "community", "weather"
]
GENRES = {
    "news": ["news", "current affairs"], "talk": ["talk", "talk show", "debate"],
    "folk": ["folk", "traditional"], "jazz": ["jazz"],
    "classical": ["classical", "opera"], "party": ["party", "dance", "club"],
    "indian": ["indian", "bollywood", "hindi"], "devotional": ["devotional", "religious", "bhajan"],
    "sports": ["sports"], "culture": ["culture", "community"],
    "weather": ["weather"], "rock": ["rock"], "pop": ["pop"],
    "electronic": ["electronic", "edm"], "world": ["world", "international"]
}

def get_json(url, timeout=35):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def split_values(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in re.split(r"[,;/|]", str(value or "")) if x.strip()]

def classify(tags, name=""):
    hay = " ".join([str(name).lower()] + [str(x).lower() for x in tags])
    found = []
    for genre, words in GENRES.items():
        if any(word in hay for word in words):
            found.append(genre)
    return found or ["general"]

def normalise_rb(row):
    url = str(row.get("url_resolved") or row.get("url") or "").strip()
    name = str(row.get("name") or "").strip()
    if not name or not url.startswith(("https://", "http://")):
        return None
    tags = split_values(row.get("tags"))
    languages = split_values(row.get("language")) or ["Unknown"]
    station_id = str(row.get("stationuuid") or hashlib.sha256(url.encode()).hexdigest()[:20])
    try:
        lat = float(row.get("geo_lat")) if row.get("geo_lat") not in (None, "") else None
        lon = float(row.get("geo_long")) if row.get("geo_long") not in (None, "") else None
    except (TypeError, ValueError):
        lat, lon = None, None
    return {
        "id": "rb-" + station_id, "station_id": "rb-" + station_id, "name": name,
        "country": str(row.get("country") or "Unknown"),
        "countrycode": str(row.get("countrycode") or "").upper(),
        "region": str(row.get("state") or ""), "city": str(row.get("city") or ""),
        "language": languages, "languages": languages, "type": classify(tags, name), "categories": classify(tags, name), "tags": tags,
        "url": url, "homepage": str(row.get("homepage") or ""),
        "favicon": str(row.get("favicon") or ""), "codec": str(row.get("codec") or ""),
        "bitrate": int(row.get("bitrate") or 0), "geo_lat": lat, "geo_long": lon,
        "clickcount": int(row.get("clickcount") or 0), "votes": int(row.get("votes") or 0),
        "source": "Radio Browser community directory", "verified": "directory-listed",
        "directory_status": "listed", "last_checked": None
    }

def normalise_air(row):
    name = str(row.get("name") or row.get("station_name") or "").strip()
    url = str(row.get("stream_url") or row.get("url") or "").strip()
    if not name or not url.startswith(("https://", "http://")):
        return None
    langs = split_values(row.get("language")) or ["Various"]
    region = str(row.get("state") or row.get("region") or "India")
    tags = ["akashvani", "india", "public service"]
    return {
        "id": "air-" + str(row.get("epg_id") or hashlib.sha256(url.encode()).hexdigest()[:16]),
        "station_id": "air-" + str(row.get("epg_id") or hashlib.sha256(url.encode()).hexdigest()[:16]),
        "name": name, "country": "India", "countrycode": "IN",
        "region": region, "city": str(row.get("city") or ""),
        "language": langs, "languages": langs, "type": classify(tags + langs, name), "categories": classify(tags + langs, name), "tags": tags,
        "url": url, "homepage": "", "favicon": "",
        "codec": "HLS" if ".m3u8" in url.lower() else "",
        "bitrate": 0, "geo_lat": None, "geo_long": None,
        "source": "Akashvani catalogue", "verified": "directory-listed",
        "directory_status": "listed", "last_checked": None
    }

def main():
    stations, sources = {}, {}
    try:
        raw = get_json(AIR_SOURCE)
        rows = raw if isinstance(raw, list) else raw.get("stations", raw.get("data", []))
        for row in rows:
            item = normalise_air(row)
            if item:
                stations[item["url"]] = item
        sources["akashvani_candidates"] = len(rows)
    except Exception as exc:
        sources["akashvani_error"] = str(exc)
        print("Akashvani source unavailable:", exc)

    endpoints = [("topclick", RB_API + "/json/stations/topclick/10000")]
    for tag in TAGS:
        endpoints.append(("tag:" + tag, RB_API + "/json/stations/bytag/" + urllib.parse.quote(tag) + "?limit=500"))
    for label, url in endpoints:
        try:
            rows = get_json(url, timeout=45)
            sources[label] = len(rows)
            for row in rows:
                item = normalise_rb(row)
                if not item:
                    continue
                previous = stations.get(item["url"])
                if previous:
                    # Keep richer metadata from the most recent source without
                    # replacing known Akashvani provenance.
                    for key, value in item.items():
                        if value not in (None, "", [], ["Unknown"]):
                            previous[key] = value
                    previous["source"] = "Akashvani + Radio Browser"
                else:
                    stations[item["url"]] = item
        except Exception as exc:
            sources[label + "_error"] = str(exc)
            print(label, "unavailable:", exc)

    items = sorted(stations.values(), key=lambda x: (x["country"].casefold(), x["region"].casefold(), x["name"].casefold()))
    countries = sorted({x["country"] for x in items if x["country"] and x["country"] != "Unknown"})
    languages = sorted({lang for x in items for lang in x["language"] if lang and lang != "Unknown"})
    regions = sorted({x["region"] for x in items if x["region"]})
    genres = sorted({genre for x in items for genre in x["type"]})
    payload = {
        "schema_version": 4, "generated_at": datetime.now(timezone.utc).isoformat(),
        "directory_name": "Sanket Global Radio Directory",
        "description": "Canonical public station catalogue for all Sanket radio experiences. Discovery index only; stream availability and rebroadcast rights are not guaranteed.",
        "api": {"json": "/data/radio-directory.json", "format": "application/json"},
        "station_fields": ["station_id", "name", "country", "countrycode", "region", "city", "languages", "categories", "tags", "url", "homepage", "favicon", "codec", "bitrate", "geo_lat", "geo_long", "source", "directory_status", "last_checked"],
        "sources": sources, "station_count": len(items), "country_count": len(countries),
        "countries": countries, "languages": languages, "regions": regions, "genres": genres,
        "stations": items
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print("Published", len(items), "catalogue entries across", len(countries), "countries")

if __name__ == "__main__":
    main()
