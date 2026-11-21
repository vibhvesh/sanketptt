"""Query and lead records shared by the search modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


RADII = (25, 50, 100, 250)
QUERY_TYPES = ("meet", "contacts", "sweep", "person")


@dataclass
class Query:
    country_code: str
    country: str
    state: str
    city: str
    radius_km: int
    industry: str
    query_type: str
    use_cache: bool = True
    lat: Optional[float] = None
    lon: Optional[float] = None
    bbox: Optional[tuple[float, float, float, float]] = None  # south, west, north, east

    @property
    def place_label(self) -> str:
        parts = [self.city, self.state, self.country]
        return ", ".join(part for part in parts if part)

    @property
    def area_label(self) -> str:
        if self.query_type == "sweep":
            return self.state or self.country or self.place_label
        return self.place_label


@dataclass
class Lead:
    name: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    contact_name: str = ""
    contact_title: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    source: str = ""
    osm_id: str = ""
    notes: str = ""
    category: str = ""
    distance_km: Optional[float] = None
    dedupe_key: str = ""
    phone_on_site: bool = False
    email_on_site: bool = False
    address_on_site: bool = False
    address_from_osm: bool = False
    website_ok: Optional[bool] = None
    mx_ok: Optional[bool] = None
    verification: dict = field(default_factory=dict)

    def public(self) -> dict:
        return {
            "name": self.name,
            "distance_km": self.distance_km,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "contact_name": self.contact_name,
            "contact_title": self.contact_title,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "source": self.source,
            "notes": self.notes,
            "verification": self.verification,
        }
