"""OpenStreetMap Nominatim geocoder and bounded place search.

Nominatim's usage policy asks for a real User-Agent and at most one request
per second. RateGate enforces the gap. Results are cached so a repeated
search does not ask again.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import httpx

from ..limiter import RateGate
from ..models import Lead


@dataclass
class GeoHit:
    lat: float
    lon: float
    display_name: str
    bbox: Optional[tuple[float, float, float, float]]  # south, west, north, east
    address: dict
    raw: dict


class Nominatim:
    def __init__(self, base_url: str, user_agent: str, gate: RateGate, cache=None) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.gate = gate
        self.cache = cache
        self.client = httpx.Client(
            timeout=20,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )

    def close(self) -> None:
        self.client.close()

    def _get(self, path: str, params: dict) -> list:
        key = path + "?" + json.dumps(params, sort_keys=True)
        if self.cache is not None:
            cached = self.cache.cached_json("nominatim", key, max_age_hours=24 * 7)
            if cached is not None:
                return cached
        self.gate.wait()
        response = self.client.get(f"{self.base_url}{path}", params=params)
        response.raise_for_status()
        data = response.json()
        if self.cache is not None:
            self.cache.save_json("nominatim", key, data)
        return data

    def geocode(self, query: str, country_code: str = "") -> Optional[GeoHit]:
        params = {
            "format": "jsonv2",
            "q": query,
            "limit": 1,
            "addressdetails": 1,
        }
        if country_code:
            params["countrycodes"] = country_code.lower()
        rows = self._get("/search", params)
        if not rows:
            return None
        return self._hit(rows[0])

    def suggest(self, query: str, country_code: str = "", limit: int = 5) -> list[dict]:
        params = {
            "format": "jsonv2",
            "q": query,
            "limit": limit,
            "addressdetails": 1,
        }
        if country_code:
            params["countrycodes"] = country_code.lower()
        rows = self._get("/search", params)
        suggestions = []
        for row in rows:
            address = row.get("address") or {}
            suggestions.append(
                {
                    "label": row.get("display_name") or row.get("name") or "",
                    "name": row.get("name") or "",
                    "city": address.get("city") or address.get("town") or address.get("village") or "",
                    "state": address.get("state") or "",
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                }
            )
        return suggestions

    def search_bounded(
        self,
        term: str,
        box: tuple[float, float, float, float],
        country_code: str,
        limit: int = 8,
    ) -> list[Lead]:
        south, west, north, east = box
        params = {
            "format": "jsonv2",
            "q": term,
            "viewbox": f"{west},{north},{east},{south}",
            "bounded": 1,
            "limit": limit,
            "addressdetails": 1,
            "extratags": 1,
            "countrycodes": country_code.lower(),
        }
        rows = self._get("/search", params)
        leads = []
        for row in rows:
            lead = self._lead(row)
            if lead:
                leads.append(lead)
        return leads

    def _hit(self, row: dict) -> GeoHit:
        south, north, west, east = (float(item) for item in row["boundingbox"])
        return GeoHit(
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            display_name=row.get("display_name") or "",
            bbox=(south, west, north, east),
            address=row.get("address") or {},
            raw=row,
        )

    def _lead(self, row: dict) -> Optional[Lead]:
        name = (row.get("name") or "").strip()
        if not name:
            return None
        tags = row.get("extratags") or {}
        address = row.get("address") or {}
        parts = [
            address.get("house_number"),
            address.get("road"),
            address.get("suburb") or address.get("neighbourhood"),
            address.get("city") or address.get("town") or address.get("village"),
            address.get("state"),
            address.get("postcode"),
            address.get("country"),
        ]
        listed = ", ".join(part for part in parts if part)
        return Lead(
            name=name,
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            address=listed or (row.get("display_name") or ""),
            phone=(tags.get("phone") or tags.get("contact:phone") or "").strip(),
            email=(tags.get("email") or tags.get("contact:email") or "").strip(),
            website=(tags.get("website") or tags.get("contact:website") or "").strip(),
            city=address.get("city") or address.get("town") or address.get("village") or "",
            state=address.get("state") or "",
            country=address.get("country") or "",
            source="OpenStreetMap via Nominatim",
            osm_id=f"{row.get('osm_type')}:{row.get('osm_id')}",
            category=(row.get("type") or ""),
            address_from_osm=bool(listed or row.get("display_name")),
            phone_on_site=False,
            email_on_site=False,
        )
