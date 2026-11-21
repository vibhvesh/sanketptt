"""Distance and search-area geometry."""

from __future__ import annotations

import math
from typing import Optional


EARTH_KM = 6371.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def circle_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return south, west, north, east for a circle, padded a little for degree math."""
    dlat = radius_km / 111.0
    cos = max(0.2, math.cos(math.radians(lat)))
    dlon = radius_km / (111.0 * cos)
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon


def point_in_box(lat: float, lon: float, box: tuple[float, float, float, float]) -> bool:
    south, west, north, east = box
    return south <= lat <= north and west <= lon <= east


def circle_covers(
    old_lat: float,
    old_lon: float,
    old_radius: float,
    new_lat: float,
    new_lon: float,
    new_radius: float,
    slack_km: float = 0.5,
) -> bool:
    """True when the new circle sits entirely inside the old one."""
    return haversine(old_lat, old_lon, new_lat, new_lon) + new_radius <= old_radius + slack_km


def circles_overlap(
    lat1: float,
    lon1: float,
    r1: float,
    lat2: float,
    lon2: float,
    r2: float,
) -> bool:
    return haversine(lat1, lon1, lat2, lon2) <= (r1 + r2)


def round_km(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 1)
