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
NEWS_TAGS = ["news", "talk", "current affairs", "politics", "business", "finance", "weather", "sports"]
MUSIC_TAGS = ["music", "pop", "rock", "jazz", "classical", "folk", "country", "dance", "electronic", "edm", "hip-hop", "rnb", "soul", "reggae", "metal", "oldies", "ambient", "world", "bollywood", "indian"]
OTHER_TAGS = ["culture", "community", "devotional", "religious"]
TAGS = list(dict.fromkeys(NEWS_TAGS + MUSIC_TAGS + OTHER_TAGS))
GENRES = {
    "news": ["news", "current affairs", "bulletin"], "talk": ["talk", "talk show", "debate", "interview"],
    "music": ["music", "musical"],
    "folk": ["folk", "traditional"], "jazz": ["jazz"],
    "classical": ["classical", "opera"], "party": ["party", "dance", "club"],
    "indian": ["indian", "bollywood", "hindi"], "devotional": ["devotional", "religious", "bhajan"],
    "sports": ["sports"], "culture": ["culture", "community"],
    "weather": ["weather"], "rock": ["rock"], "pop": ["pop"],
    "electronic": ["electronic", "edm"], "world": ["world", "international"],
    "hip-hop": ["hip-hop", "hip hop", "rap"], "soul": ["soul", "rnb", "r&b"],
    "reggae": ["reggae"], "country": ["country music"], "ambient": ["ambient"],
    "metal": ["metal"], "oldies": ["oldies", "classic hits"]
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
    if not name or len(name) > 180 or not url.startswith(("https://", "http://")) or any(ch in name for ch in "\r\n\x00"):
        return None
    parsed = urllib.parse.urlparse(url)
    if not parsed.hostname or parsed.scheme not in ("http", "https"):
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
        "editorial_priority": 0 if "news" in classify(tags, name) else (1 if any(x in classify(tags, name) for x in ("music", "pop", "rock", "jazz", "classical", "folk", "electronic", "hip-hop")) else 2),
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

    endpoints = []
    # Focused editorial discovery first: news/talk, then music and its genres.
    for tag in NEWS_TAGS + MUSIC_TAGS + OTHER_TAGS:
        endpoints.append(("tag:" + tag, RB_API + "/json/stations/bytag/" + urllib.parse.quote(tag) + "?limit=1000"))
    # Broad popularity crawl supplements the focused feeds; it is not the primary ranking.
    endpoints.append(("topclick", RB_API + "/json/stations/topclick/10000"))
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
                            if key in ("tags", "categories", "type", "languages", "language"):
                                previous[key] = list(dict.fromkeys((previous.get(key) or []) + (value or [])))
                            else:
                                previous[key] = value
                    previous["source"] = "Akashvani + Radio Browser"
                else:
                    stations[item["url"]] = item
        except Exception as exc:
            sources[label + "_error"] = str(exc)
            print(label, "unavailable:", exc)

    clean = {}
    rejected = 0
    for item in stations.values():
        url = str(item.get("url") or "").strip()
        name = str(item.get("name") or "").strip()
        parsed = urllib.parse.urlparse(url)
        if not name or not parsed.hostname or parsed.scheme not in ("http", "https"):
            rejected += 1
            continue
        key = url.casefold()
        if key in clean:
            rejected += 1
            continue
        item["name"] = name
        item["directory_status"] = "listed"
        item.setdefault("last_checked", None)
        clean[key] = item
    items = sorted(clean.values(), key=lambda x: (x.get("editorial_priority", 2), x["country"].casefold(), x["region"].casefold(), x["name"].casefold()))
    # Keep the public payload compact for mobile clients. These are duplicate
    # aliases or crawl-only fields; the UI supports language/type as canonical.
    for item in items:
        item.pop("station_id", None)       # same value as id
        item.pop("languages", None)        # same values as language
        item.pop("categories", None)       # same values as type
        item.pop("editorial_priority", None)  # already applied to sort order
        item["tags"] = list(dict.fromkeys(item.get("tags") or []))[:12]
    countries = sorted({x["country"] for x in items if x["country"] and x["country"] != "Unknown"})
    languages = sorted({lang for x in items for lang in x["language"] if lang and lang != "Unknown"})
    regions = sorted({x["region"] for x in items if x["region"]})
    genres = sorted({genre for x in items for genre in x["type"]})
    data_dir = os.path.dirname(OUT)
    os.makedirs(data_dir, exist_ok=True)

    # Full browse/search data is separate from the tiny first-paint manifest.
    # Mobile clients fetch this only after a search, country filter or Nearby action.
    search_fields = ("id", "name", "country", "countrycode", "region", "city",
                     "language", "type", "tags", "url", "codec", "geo_lat",
                     "geo_long", "clickcount", "votes")
    search_items = [{key: item.get(key) for key in search_fields} for item in items]
    search_path = os.path.join(data_dir, "radio-search-index.json")
    with open(search_path, "w", encoding="utf-8") as output:
        json.dump({"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
                   "station_count": len(search_items), "stations": search_items},
                  output, ensure_ascii=False, separators=(",", ":"))

    top_items = sorted(items, key=lambda x: (-(x.get("clickcount") or 0),
                                               -(x.get("votes") or 0),
                                               x["name"].casefold()))[:10]
    payload = {
        "schema_version": 5, "crawl_focus": ["news", "music"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "directory_name": "Sanket Global Radio Directory",
        "description": "Canonical public station catalogue. The small manifest loads first; full station search data loads only on demand.",
        "api": {"json": "/data/radio-directory.json", "search": "/data/radio-search-index.json",
                "format": "application/json"},
        "sources": sources, "rejected_bad_or_duplicate_entries": rejected,
        "station_count": len(items), "country_count": len(countries),
        "countries": countries, "languages": languages, "regions": regions, "genres": genres,
        "top_stations": top_items, "search_index": "radio-search-index.json"
    }
    with open(OUT, "w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, separators=(",", ":"))
        output.write("\\n")
    print("Published manifest for", len(items), "stations across", len(countries),
          "countries; search index:", os.path.getsize(search_path), "bytes")
