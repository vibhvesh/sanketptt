"""OpenStreetMap Overpass queries for tagged places inside a box.

Public Overpass servers often time out. Callers should treat a failure as
"no extra places" and keep going with the other sources.
"""

from __future__ import annotations

import httpx

from ..industries import Industry
from ..models import Lead


class Overpass:
    def __init__(self, url: str, user_agent: str, timeout: float) -> None:
        self.url = url
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )

    def close(self) -> None:
        self.client.close()

    def search(self, industry: Industry, box: tuple[float, float, float, float]) -> list[Lead]:
        if not industry.overpass_tags:
            return []
        south, west, north, east = box
        lines = [
            f'nwr["{key}"="{value}"]({south},{west},{north},{east});'
            for key, value in industry.overpass_tags
        ]
        query = "[out:json][timeout:%d];(\n%s\n);\nout center tags 25;" % (
            max(5, int(self.timeout) - 1),
            "\n".join(lines),
        )
        response = self.client.post(self.url, data={"data": query})
        response.raise_for_status()
        payload = response.json()
        leads = []
        for element in payload.get("elements") or []:
            lead = _element_to_lead(element)
            if lead:
                leads.append(lead)
        return leads


def _element_to_lead(element: dict) -> Lead | None:
    tags = element.get("tags") or {}
    name = (tags.get("name") or "").strip()
    if not name:
        return None
    center = element.get("center") or {}
    lat = element.get("lat", center.get("lat"))
    lon = element.get("lon", center.get("lon"))
    if lat is None or lon is None:
        return None
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    address = tags.get("addr:full") or ", ".join(part for part in parts if part)
    category = (
        tags.get("shop")
        or tags.get("office")
        or tags.get("amenity")
        or tags.get("industrial")
        or tags.get("tourism")
        or ""
    )
    return Lead(
        name=name,
        lat=float(lat),
        lon=float(lon),
        address=address,
        phone=(tags.get("phone") or tags.get("contact:phone") or "").strip(),
        email=(tags.get("email") or tags.get("contact:email") or "").strip(),
        website=(tags.get("website") or tags.get("contact:website") or "").strip(),
        city=tags.get("addr:city") or "",
        state=tags.get("addr:state") or "",
        source="OpenStreetMap via Overpass",
        osm_id=f"{element.get('type')}:{element.get('id')}",
        category=category,
        address_from_osm=bool(address),
    )
