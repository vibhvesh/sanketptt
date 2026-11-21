"""HTTP API and, when the static page is present, the /leads/ UI."""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from pydantic import BaseModel, Field

from .config import Settings
from .industries import INDUSTRIES, industry_options
from .limiter import RateGate, WindowLimiter
from .models import QUERY_TYPES, RADII, Query as SearchQuery
from .pipeline import Services, run_search
from .places import cities, countries, country_name, states
from .sources.fetch import PageFetcher
from .sources.nominatim import Nominatim
from .sources.overpass import Overpass
from .sources.photon import Photon
from .sources.websearch import WebSearch
from .storage import Store

app = FastAPI(title="Sanket lead finder", docs_url=None, redoc_url=None)

_store: Store | None = None
_services: Services | None = None
search_limiter = WindowLimiter(8, 10 * 60)
suggest_limiter = WindowLimiter(30, 60)

_PAGE = Path(__file__).resolve().parents[2] / "website" / "leads"


class SearchIn(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    state: str = ""
    city: str = ""
    radius_km: int = 100
    industry: str
    query_type: str
    use_cache: bool = True


def reset() -> None:
    """Drop cached clients. Tests use this after changing environment variables."""
    global _store, _services
    if _services is not None:
        for client in (
            _services.nominatim,
            _services.overpass,
            _services.photon,
            _services.web,
            _services.fetcher,
        ):
            close = getattr(client, "close", None)
            if close:
                close()
    _store = None
    _services = None
    search_limiter.clear()
    suggest_limiter.clear()


def get_store() -> Store:
    global _store
    settings = Settings.load()
    if _store is None or _store.path != settings.db_path:
        _store = Store(settings.db_path)
    return _store


def get_services() -> Services:
    global _services
    if _services is None:
        settings = Settings.load()
        gate = RateGate(settings.nominatim_interval)
        store = get_store()
        _services = Services(
            nominatim=Nominatim(settings.nominatim_url, settings.user_agent, gate, store),
            overpass=Overpass(settings.overpass_url, settings.user_agent, settings.overpass_timeout),
            photon=Photon(settings.photon_url, settings.user_agent),
            web=WebSearch(settings.user_agent),
            fetcher=PageFetcher(settings.user_agent),
        )
    return _services


def token_ok(provided: str, expected: str) -> bool:
    if not provided or not expected:
        return False
    return hmac.compare_digest(
        hashlib.sha256(provided.encode()).digest(),
        hashlib.sha256(expected.encode()).digest(),
    )


def require_token(
    authorization: str | None = Header(None),
    x_leads_token: str | None = Header(None),
) -> str:
    settings = Settings.load()
    if not settings.token:
        raise HTTPException(status_code=503, detail="LEADS_TOKEN is not configured")
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_leads_token:
        token = x_leads_token.strip()
    if not token_ok(token, settings.token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token


def _configure() -> None:
    settings = Settings.load()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins) or ["http://127.0.0.1:8765"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Leads-Token"],
    )


_configure()


@app.middleware("http")
async def private_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "auth": "required"}


@app.post("/api/session")
def session(_: str = Depends(require_token)) -> dict:
    return {"ok": True}


@app.get("/api/meta")
def meta(_: str = Depends(require_token)) -> dict:
    return {
        "industries": industry_options(),
        "query_types": [
            {"id": "meet", "label": "Meet in person"},
            {"id": "contacts", "label": "Email / phone contacts"},
            {"id": "sweep", "label": "Industry sweep"},
            {"id": "person", "label": "Contact person"},
        ],
        "radii": list(RADII),
        "countries": countries(),
    }


@app.get("/api/places/states")
def place_states(country: str, _: str = Depends(require_token)) -> dict:
    return {"states": states(country)}


@app.get("/api/places/cities")
def place_cities(country: str, state: str = "", _: str = Depends(require_token)) -> dict:
    return {"cities": cities(country, state)}


@app.get("/api/places/suggest")
def place_suggest(
    q: str,
    country: str,
    state: str = "",
    token: str = Depends(require_token),
) -> dict:
    if not suggest_limiter.allow(_limit_key(token)):
        raise HTTPException(status_code=429, detail="Too many place lookups. Wait a minute.")
    text = q.strip()
    if len(text) < 2:
        return {"suggestions": []}
    label = ", ".join(part for part in (text, state, country_name(country)) if part)
    try:
        suggestions = get_services().nominatim.suggest(label, country)
    except Exception:
        suggestions = []
    return {"suggestions": suggestions}


@app.get("/api/searches")
def list_searches(_: str = Depends(require_token)) -> dict:
    return {"searches": get_store().list_searches()}


@app.get("/api/searches/{search_id}")
def read_search(search_id: int, _: str = Depends(require_token)) -> dict:
    found = get_store().get_search(search_id)
    if not found:
        raise HTTPException(status_code=404, detail="Search not found")
    return found


@app.post("/api/searches")
def create_search(body: SearchIn, token: str = Depends(require_token)) -> dict:
    if not search_limiter.allow(_limit_key(token)):
        raise HTTPException(status_code=429, detail="Too many searches. Wait a few minutes and try again.")
    query = _to_query(body)
    try:
        return run_search(query, get_store(), get_services())
    except LookupError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/searches/{search_id}/export.csv")
def export_csv(search_id: int, _: str = Depends(require_token)) -> Response:
    found = _require_search(search_id)
    return Response(
        _csv_bytes(found["leads"]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sanket-leads-{search_id}.csv"'},
    )


@app.get("/api/searches/{search_id}/export.xlsx")
def export_xlsx(search_id: int, _: str = Depends(require_token)) -> Response:
    found = _require_search(search_id)
    return Response(
        _xlsx_bytes(found["leads"]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="sanket-leads-{search_id}.xlsx"'},
    )


def _require_search(search_id: int) -> dict:
    found = get_store().get_search(search_id)
    if not found:
        raise HTTPException(status_code=404, detail="Search not found")
    return found


def _to_query(body: SearchIn) -> SearchQuery:
    code = body.country_code.upper()
    name = country_name(code)
    if not name:
        raise ValueError("Choose a country from the list")
    if body.industry not in INDUSTRIES:
        raise ValueError("Choose an industry from the list")
    if body.query_type not in QUERY_TYPES:
        raise ValueError("Choose a query type from the list")
    if body.radius_km not in RADII:
        raise ValueError("Choose a radius from the list")
    city = body.city.strip()
    state = body.state.strip()
    if body.query_type != "sweep" and not city:
        raise ValueError("Choose a city or spot")
    return SearchQuery(
        country_code=code,
        country=name,
        state=state,
        city=city,
        radius_km=body.radius_km,
        industry=body.industry,
        query_type=body.query_type,
        use_cache=body.use_cache,
    )


def _limit_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:16]


_COLUMNS = [
    ("name", "Name"),
    ("distance_km", "Distance km"),
    ("address", "Address"),
    ("phone", "Phone"),
    ("email", "Email"),
    ("website", "Website"),
    ("contact_name", "Contact name"),
    ("contact_title", "Contact title"),
    ("city", "City"),
    ("state", "State"),
    ("country", "Country"),
    ("source", "Source"),
    ("notes", "Notes"),
]


def _flat_row(lead: dict) -> list:
    row = [lead.get(key) if lead.get(key) is not None else "" for key, _label in _COLUMNS]
    verification = lead.get("verification") or {}
    for key in ("phone", "email", "address", "website"):
        item = verification.get(key) or {}
        flag = "yes" if item.get("verified") else ("listed" if item.get("checks") else "")
        row.append(flag)
    return row


def _headers() -> list[str]:
    return [label for _key, label in _COLUMNS] + [
        "Phone verified",
        "Email verified",
        "Address verified",
        "Website verified",
    ]


def _csv_bytes(leads: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_headers())
    for lead in leads:
        writer.writerow(_flat_row(lead))
    return buffer.getvalue().encode("utf-8-sig")


def _xlsx_bytes(leads: list[dict]) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Leads"
    sheet.append(_headers())
    for lead in leads:
        sheet.append(_flat_row(lead))
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


@app.get("/sanket-mark.svg")
def brand_mark() -> FileResponse:
    path = _PAGE.parent / "sanket-mark.svg"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Missing mark")
    return FileResponse(path, media_type="image/svg+xml")


if _PAGE.is_dir():
    app.mount("/leads", StaticFiles(directory=_PAGE, html=True), name="leads-page")
