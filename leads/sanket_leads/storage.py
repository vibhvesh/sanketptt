"""SQLite store for queries, leads and short-lived HTTP caches.

A repeated or overlapping search from the last 24 hours reuses saved leads
and only adds places that were not already stored.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .geo import circle_covers, circles_overlap, haversine, round_km
from .models import Lead, Query
from .textutil import norm_name, phone_key


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat()


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    query_type TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    state TEXT,
                    city TEXT,
                    radius_km REAL,
                    lat REAL,
                    lon REAL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY,
                    dedupe_key TEXT UNIQUE,
                    name TEXT,
                    lat REAL,
                    lon REAL,
                    payload TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS search_leads (
                    search_id INTEGER NOT NULL,
                    lead_id INTEGER NOT NULL,
                    distance_km REAL,
                    PRIMARY KEY (search_id, lead_id)
                );
                CREATE TABLE IF NOT EXISTS http_cache (
                    source TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (source, cache_key)
                );
                CREATE INDEX IF NOT EXISTS searches_lookup
                    ON searches (query_type, industry, country_code, created_at);
                """
            )

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def cached_json(self, source: str, key: str, max_age_hours: float):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload, fetched_at FROM http_cache WHERE source=? AND cache_key=?",
                (source, key),
            ).fetchone()
        if not row:
            return None
        fetched = datetime.fromisoformat(row["fetched_at"])
        if utcnow() - fetched > timedelta(hours=max_age_hours):
            return None
        return json.loads(row["payload"])

    def save_json(self, source: str, key: str, payload) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO http_cache (source, cache_key, payload, fetched_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source, cache_key) DO UPDATE SET
                    payload=excluded.payload, fetched_at=excluded.fetched_at
                """,
                (source, key, json.dumps(payload), iso(utcnow())),
            )

    def covering(self, query: Query):
        for row in self._recent(query):
            # An empty search is not reused. A failed pass should not block the next one.
            if _covers(row, query) and self._lead_count(row["id"]):
                return row
        return None

    def _lead_count(self, search_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM search_leads WHERE search_id=?",
                (search_id,),
            ).fetchone()
        return int(row["n"]) if row else 0

    def overlapping(self, query: Query) -> list[sqlite3.Row]:
        return [row for row in self._recent(query) if _overlaps(row, query)]

    def _recent(self, query: Query) -> list[sqlite3.Row]:
        since = iso(utcnow() - timedelta(hours=24))
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT * FROM searches
                WHERE query_type=? AND industry=? AND country_code=? AND created_at>=?
                ORDER BY id DESC
                """,
                (query.query_type, query.industry, query.country_code, since),
            ).fetchall()

    def leads_for(self, search_id: int, query: Query) -> list[Lead]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT leads.payload FROM search_leads
                JOIN leads ON leads.id = search_leads.lead_id
                WHERE search_leads.search_id=?
                """,
                (search_id,),
            ).fetchall()
        leads = []
        seen = set()
        for row in rows:
            lead = lead_from_payload(json.loads(row["payload"]))
            if lead.dedupe_key in seen:
                continue
            if not _lead_in_query(lead, query):
                continue
            seen.add(lead.dedupe_key)
            leads.append(lead)
        return leads

    def save_search(
        self,
        query: Query,
        leads: list[Lead],
        *,
        reused_from: list[int],
        warnings: list[str],
        log: list[str],
        external: bool,
    ) -> dict:
        moment = iso(utcnow())
        payload = {
            "country": query.country,
            "state": query.state,
            "city": query.city,
            "radius_km": query.radius_km,
            "reused_from": reused_from,
            "warnings": warnings,
            "log": log,
            "external": external,
        }
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO searches (
                    created_at, query_type, industry, country_code, state, city,
                    radius_km, lat, lon, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    moment,
                    query.query_type,
                    query.industry,
                    query.country_code,
                    query.state,
                    query.city,
                    query.radius_km,
                    query.lat,
                    query.lon,
                    json.dumps(payload),
                ),
            )
            search_id = cursor.lastrowid
            for lead in leads:
                lead_id = self._upsert_lead(conn, lead, moment, external)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO search_leads (search_id, lead_id, distance_km)
                    VALUES (?, ?, ?)
                    """,
                    (search_id, lead_id, lead.distance_km),
                )
        return self.get_search(search_id)

    def _upsert_lead(self, conn, lead: Lead, moment: str, external: bool) -> int:
        row = conn.execute(
            "SELECT id, payload FROM leads WHERE dedupe_key=?",
            (lead.dedupe_key,),
        ).fetchone()
        if row and not external:
            return row["id"]
        if row:
            current = lead_from_payload(json.loads(row["payload"]))
            fill_blanks(current, lead)
            current.dedupe_key = lead.dedupe_key
            conn.execute(
                "UPDATE leads SET name=?, lat=?, lon=?, payload=?, last_seen=? WHERE id=?",
                (current.name, current.lat, current.lon, json.dumps(lead_payload(current)), moment, row["id"]),
            )
            return row["id"]
        cursor = conn.execute(
            """
            INSERT INTO leads (dedupe_key, name, lat, lon, payload, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (lead.dedupe_key, lead.name, lead.lat, lead.lon, json.dumps(lead_payload(lead)), moment, moment),
        )
        return cursor.lastrowid

    def get_search(self, search_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM searches WHERE id=?", (search_id,)).fetchone()
            if not row:
                return None
            linked = conn.execute(
                """
                SELECT leads.payload, search_leads.distance_km
                FROM search_leads JOIN leads ON leads.id = search_leads.lead_id
                WHERE search_leads.search_id=?
                ORDER BY search_leads.distance_km IS NULL, search_leads.distance_km, leads.name
                """,
                (search_id,),
            ).fetchall()
        leads = []
        for item in linked:
            lead = lead_from_payload(json.loads(item["payload"]))
            if item["distance_km"] is not None:
                lead.distance_km = item["distance_km"]
            leads.append(lead.public())
        return _search_dict(row, leads)

    def list_searches(self, limit: int = 40) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM searches ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            counts = {
                item["search_id"]: item["n"]
                for item in conn.execute(
                    "SELECT search_id, COUNT(*) AS n FROM search_leads GROUP BY search_id"
                )
            }
        listed = []
        for row in rows:
            item = _search_dict(row, [])
            item["result_count"] = counts.get(row["id"], 0)
            listed.append(item)
        return listed


def lead_payload(lead: Lead) -> dict:
    data = lead.public()
    data.update(
        {
            "lat": lead.lat,
            "lon": lead.lon,
            "osm_id": lead.osm_id,
            "category": lead.category,
            "dedupe_key": lead.dedupe_key,
            "phone_on_site": lead.phone_on_site,
            "email_on_site": lead.email_on_site,
            "address_on_site": lead.address_on_site,
            "address_from_osm": lead.address_from_osm,
            "website_ok": lead.website_ok,
            "mx_ok": lead.mx_ok,
        }
    )
    return data


def lead_from_payload(data: dict) -> Lead:
    known = {field for field in Lead.__dataclass_fields__}
    return Lead(**{key: value for key, value in data.items() if key in known})


def _verified_count(verification: dict) -> int:
    if not isinstance(verification, dict):
        return 0
    return sum(1 for item in verification.values() if isinstance(item, dict) and item.get("verified"))


def fill_blanks(target: Lead, incoming: Lead) -> None:
    for field in ("phone", "email", "website", "address", "contact_name", "contact_title", "city", "state", "source"):
        if not getattr(target, field) and getattr(incoming, field):
            setattr(target, field, getattr(incoming, field))
    if target.lat is None and incoming.lat is not None:
        target.lat = incoming.lat
        target.lon = incoming.lon
    target.phone_on_site = target.phone_on_site or incoming.phone_on_site
    target.email_on_site = target.email_on_site or incoming.email_on_site
    target.address_on_site = target.address_on_site or incoming.address_on_site
    target.address_from_osm = target.address_from_osm or incoming.address_from_osm
    if incoming.website_ok:
        target.website_ok = True
    if _verified_count(incoming.verification) >= _verified_count(target.verification):
        target.verification = incoming.verification


def _covers(row: sqlite3.Row, query: Query) -> bool:
    if query.query_type == "sweep":
        old_state = (row["state"] or "").strip().lower()
        new_state = (query.state or "").strip().lower()
        if new_state and not old_state:
            return True
        return old_state == new_state
    if row["lat"] is None or query.lat is None:
        return False
    return circle_covers(row["lat"], row["lon"], row["radius_km"] or 0, query.lat, query.lon, query.radius_km)


def _overlaps(row: sqlite3.Row, query: Query) -> bool:
    if query.query_type == "sweep":
        old_state = (row["state"] or "").strip().lower()
        new_state = (query.state or "").strip().lower()
        return not old_state or not new_state or old_state == new_state
    if row["lat"] is None or query.lat is None:
        return False
    return circles_overlap(
        row["lat"], row["lon"], row["radius_km"] or 0, query.lat, query.lon, query.radius_km
    )


def _lead_in_query(lead: Lead, query: Query) -> bool:
    if query.query_type == "sweep":
        if query.state and lead.state and norm_name(lead.state) != norm_name(query.state):
            if lead.lat is None or query.bbox is None:
                return False
        if lead.lat is not None and query.bbox is not None:
            south, west, north, east = query.bbox
            return south <= lead.lat <= north and west <= lead.lon <= east
        return True
    if lead.lat is None or query.lat is None:
        return False
    distance = haversine(query.lat, query.lon, lead.lat, lead.lon)
    if distance > query.radius_km:
        return False
    lead.distance_km = round_km(distance)
    return True


def _search_dict(row: sqlite3.Row, leads: list[dict]) -> dict:
    extra = json.loads(row["payload"])
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "query_type": row["query_type"],
        "industry": row["industry"],
        "country_code": row["country_code"],
        "country": extra.get("country") or "",
        "state": row["state"] or "",
        "city": row["city"] or "",
        "radius_km": row["radius_km"],
        "lat": row["lat"],
        "lon": row["lon"],
        "reused_from": extra.get("reused_from") or [],
        "warnings": extra.get("warnings") or [],
        "log": extra.get("log") or [],
        "external": extra.get("external", True),
        "result_count": len(leads),
        "leads": leads,
    }


def make_key(lead: Lead) -> str:
    phone = phone_key(lead.phone)
    name = norm_name(lead.name) or "unknown"
    if lead.osm_id:
        return "osm:" + lead.osm_id
    if phone:
        return "ph:" + phone + ":" + name
    if lead.lat is not None:
        return f"geo:{name}:{lead.lat:.3f}:{lead.lon:.3f}"
    return "name:" + name
