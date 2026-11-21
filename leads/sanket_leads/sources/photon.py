"""Photon (Komoot) place search. It is an OSM geocoder and answers when Overpass is slow."""

from __future__ import annotations

import httpx

from ..models import Lead


class Photon:
    def __init__(self, url: str, user_agent: str) -> None:
        self.url = url
        self.client = httpx.Client(timeout=15, headers={"User-Agent": user_agent})

    def close(self) -> None:
        self.client.close()

    def search(self, term: str, box: tuple[float, float, float, float], limit: int = 8) -> list[Lead]:
        south, west, north, east = box
        response = self.client.get(
            self.url,
            params={
                "q": term,
                "bbox": f"{west},{south},{east},{north}",
                "limit": limit,
                "lang": "en",
            },
        )
        response.raise_for_status()
        leads = []
        for feature in response.json().get("features") or []:
            lead = _feature_to_lead(feature)
            if lead:
                leads.append(lead)
        return leads


def _feature_to_lead(feature: dict) -> Lead | None:
    props = feature.get("properties") or {}
    name = (props.get("name") or "").strip()
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    if not name or len(coords) < 2:
        return None
    lon, lat = float(coords[0]), float(coords[1])
    parts = [
        props.get("housenumber"),
        props.get("street"),
        props.get("district") or props.get("city") or props.get("locality"),
        props.get("state"),
        props.get("postcode"),
        props.get("country"),
    ]
    return Lead(
        name=name,
        lat=lat,
        lon=lon,
        address=", ".join(part for part in parts if part),
        city=props.get("city") or props.get("district") or "",
        state=props.get("state") or "",
        country=props.get("country") or "",
        source="OpenStreetMap via Photon",
        osm_id=f"{props.get('osm_key')}:{props.get('osm_id')}",
        category=props.get("osm_value") or "",
        address_from_osm=any(parts),
    )
