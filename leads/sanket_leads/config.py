"""Runtime settings. Read from the environment on each call so tests can override them."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    token: str
    db_path: str
    cors_origins: tuple[str, ...]
    user_agent: str
    nominatim_interval: float
    overpass_timeout: float
    nominatim_url: str
    overpass_url: str
    photon_url: str

    @classmethod
    def load(cls) -> "Settings":
        origins = [
            item.strip().rstrip("/")
            for item in os.environ.get(
                "LEADS_CORS_ORIGINS",
                "https://sanketptt.com,https://www.sanketptt.com,http://127.0.0.1:8765,http://localhost:8765",
            ).split(",")
            if item.strip()
        ]
        return cls(
            token=os.environ.get("LEADS_TOKEN", "").strip(),
            db_path=os.environ.get("LEADS_DB_PATH", "./data/leads.sqlite"),
            cors_origins=tuple(origins),
            user_agent=os.environ.get(
                "NOMINATIM_USER_AGENT",
                "SanketLeads/1.0 (+https://sanketptt.com/leads/; internal sales research)",
            ),
            nominatim_interval=float(os.environ.get("NOMINATIM_MIN_INTERVAL", "1.1")),
            overpass_timeout=float(os.environ.get("OVERPASS_TIMEOUT", "8")),
            nominatim_url=os.environ.get(
                "NOMINATIM_URL", "https://nominatim.openstreetmap.org"
            ).rstrip("/"),
            overpass_url=os.environ.get(
                "OVERPASS_URL", "https://overpass-api.de/api/interpreter"
            ),
            photon_url=os.environ.get(
                "PHOTON_URL", "https://photon.komoot.io/api/"
            ),
        )
