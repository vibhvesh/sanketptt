"""Offline tests for geometry, storage, extraction, verification and the API."""

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sanket_leads import api
from sanket_leads.extract.contacts import extract_contacts
from sanket_leads.extract.people import extract_people
from sanket_leads.geo import circle_covers, haversine
from sanket_leads.models import Lead, Query
from sanket_leads.pipeline import run_search
from sanket_leads.sources.nominatim import GeoHit
from sanket_leads.sources.websearch import WebHit, _bing_url, _ddg_url
from sanket_leads.storage import Store
from sanket_leads.verify import apply_verification, domain_has_mx

ROOT = Path(__file__).resolve().parents[2]


def test_vadodara_halol_distance_is_inside_100km():
    distance = haversine(22.2973, 73.1943, 22.533, 73.145)
    assert 20 < distance < 40
    assert circle_covers(22.3, 73.2, 100, 22.35, 73.22, 50)


def test_smaller_search_reuses_a_covering_search(tmp_path):
    store = Store(str(tmp_path / "leads.sqlite"))
    wide = Query(
        country_code="IN", country="India", state="Gujarat", city="Vadodara",
        radius_km=100, industry="two_way_radio", query_type="meet",
        lat=22.3, lon=73.19,
    )
    near = Lead(
        name="Near Radio", address="1 Market Road, Vadodara", phone="02652343210",
        lat=22.35, lon=73.2, dedupe_key="osm:near", address_from_osm=True,
    )
    far = Lead(
        name="Far Radio", address="Remote depot", phone="02652343211",
        lat=23.5, lon=73.19, dedupe_key="osm:far", address_from_osm=True,
    )
    store.save_search(wide, [near, far], reused_from=[], warnings=[], log=[], external=True)
    narrow = Query(
        country_code="IN", country="India", state="Gujarat", city="Vadodara",
        radius_km=50, industry="two_way_radio", query_type="meet",
        lat=22.3, lon=73.19,
    )
    cover = store.covering(narrow)
    assert cover is not None
    kept = store.leads_for(cover["id"], narrow)
    assert [lead.name for lead in kept] == ["Near Radio"]


def test_extracts_only_contacts_that_are_on_the_page():
    html = """
    <html><head><title>Contact Us - Nav Wireless</title></head>
    <body>
      <a href="tel:+917048421010">Call</a>
      <a href="mailto:info@navwireless.com">Email</a>
      <p>Address: C5 The First, near Keshav Baug, Ahmedabad, Gujarat 380015</p>
    </body></html>
    """
    found = extract_contacts(html)
    assert found.phones == ("+917048421010",)
    assert found.emails == ("info@navwireless.com",)
    assert "380015" in found.address
    assert "Ahmedabad" in found.address
    empty = extract_contacts("<html><title>About</title><p>No contact details.</p></html>")
    assert empty.phones == ()
    assert empty.emails == ()
    assert empty.address == ""


def test_person_name_must_sit_next_to_a_title():
    hits = extract_people("<p>Priya Shah, Head of Security, leads the plant.</p>")
    assert [(hit.name, hit.title) for hit in hits] == [("Priya Shah", "Head of Security")]
    assert extract_people("<p>Our Head of Security team is hiring.</p>") == []
    assert extract_people("<p>Contact Us, Head of Security</p>") == []


def test_verification_does_not_invent_or_mark_a_blank_email():
    lead = Lead(name="Example", email="", phone="9876543210", phone_on_site=True)
    apply_verification(lead, lookup=lambda domain: True)
    assert lead.verification["email"] == {"value": "", "verified": False, "checks": []}
    assert lead.verification["phone"]["verified"] is True

    listed = Lead(name="Shop", email="sales@example-radio.test", email_on_site=True, phone="111", address="Road 1")
    apply_verification(listed, lookup=lambda domain: False)
    assert listed.verification["email"]["verified"] is False
    assert domain_has_mx("not a domain") is False


def test_search_result_urls_are_decoded_not_guessed():
    raw = base64.urlsafe_b64encode(b"https://dealer.example/contact").decode().rstrip("=")
    assert _bing_url(f"https://www.bing.com/ck/a?u=a1{raw}") == "https://dealer.example/contact"
    assert _ddg_url("https://duckduckgo.com/l/?uddg=https%3A%2F%2Fdealer.example%2Fcontact") == "https://dealer.example/contact"


class _Geo:
    def __init__(self):
        self.geocodes = []
        self.searches = []

    def geocode(self, query, country_code=""):
        self.geocodes.append(query)
        return GeoHit(22.3, 73.19, query, (21.4, 72.2, 23.2, 74.2), {"state": "Gujarat", "country": "India"}, {})

    def search_bounded(self, term, box, country_code, limit=8):
        self.searches.append(term)
        if "wireless" not in term:
            return []
        return [Lead(
            name="Nav Wireless Technologies",
            lat=22.55, lon=73.15,
            address="SH5, Halol, Panchmahal, Gujarat 389350",
            osm_id="node:1",
            category="industrial",
            address_from_osm=True,
            source="OpenStreetMap via Nominatim",
        )]

    def suggest(self, query, country_code="", limit=5):
        return []


class _Empty:
    def search(self, *args, **kwargs):
        return []


class _Web:
    def __init__(self):
        self.calls = 0
        self.queries = []

    def search(self, query, limit=8):
        self.calls += 1
        self.queries.append(query)
        return [WebHit("Nav Wireless Technologies", "https://navwireless.example/contact", "wireless communication Vadodara")]


class _Pages:
    def fetch(self, url):
        html = """
        <html><title>Contact - Nav Wireless Technologies</title>
        <p>Nav Wireless Technologies, Halol.</p>
        <a href="tel:+917048421010">+91 70484 21010</a>
        <a href="mailto:info@navwireless.com">info@navwireless.com</a>
        <p>Address: SH5, Halol, Gujarat 389350</p>
        <p>Priya Shah, Managing Director</p>
        </html>
        """
        return type("Page", (), {"url": url, "html": html, "status": 200})()

    def reachable(self, url):
        return True


def test_meet_search_fills_a_real_phone_and_then_reuses_it(tmp_path):
    geo = _Geo()
    web = _Web()
    from sanket_leads.pipeline import Services
    services = Services(geo, _Empty(), _Empty(), web, _Pages())
    store = Store(str(tmp_path / "live.sqlite"))
    query = Query(
        country_code="IN", country="India", state="Gujarat", city="Vadodara",
        radius_km=100, industry="two_way_radio", query_type="meet",
    )
    saved = run_search(query, store, services)
    names = [lead["name"] for lead in saved["leads"]]
    assert any("Vadodara" in query and "{place}" not in query for query in web.queries)
    assert "Nav Wireless Technologies" in names, saved["log"]
    match = next(lead for lead in saved["leads"] if lead["name"] == "Nav Wireless Technologies")
    assert match["phone"]
    assert match["address"]
    assert match["distance_km"] <= 100
    assert match["email"] == "info@navwireless.com" or match["email"] == ""
    searches_after = list(geo.searches)
    again = run_search(query, store, services)
    assert geo.searches == searches_after
    assert again["reused_from"]
    assert any(lead["name"] == "Nav Wireless Technologies" for lead in again["leads"])


def test_contact_person_search_is_separate(tmp_path):
    geo = _Geo()
    from sanket_leads.pipeline import Services
    services = Services(geo, _Empty(), _Empty(), _Web(), _Pages())
    store = Store(str(tmp_path / "people.sqlite"))
    query = Query(
        country_code="IN", country="India", state="Gujarat", city="Vadodara",
        radius_km=100, industry="two_way_radio", query_type="person",
    )
    saved = run_search(query, store, services)
    assert saved["leads"], saved["log"]
    assert all(lead["contact_name"] for lead in saved["leads"])
    assert any(lead["contact_name"] == "Priya Shah" for lead in saved["leads"])


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LEADS_TOKEN", "secret")
    monkeypatch.setenv("LEADS_DB_PATH", str(tmp_path / "api.sqlite"))
    api.reset()
    return TestClient(api.app)


def test_api_requires_the_token_and_exports_saved_rows(client, monkeypatch):
    assert client.get("/api/health").json()["auth"] == "required"
    assert client.get("/api/health").headers["x-robots-tag"] == "noindex, nofollow"
    assert client.get("/api/meta").status_code == 401

    def fake(query, store, services):
        lead = Lead(
            name="Example Radio",
            address="12 Market Road, Vadodara",
            phone="9876543210",
            distance_km=3.2,
            dedupe_key="osm:example",
            source="test",
        )
        from sanket_leads.verify import apply_verification
        apply_verification(lead, lookup=lambda domain: False)
        lead.dedupe_key = "osm:example"
        return store.save_search(query, [lead], reused_from=[], warnings=[], log=["fake"], external=True)

    monkeypatch.setattr(api, "run_search", fake)
    denied = client.post("/api/searches", json={
        "country_code": "IN", "state": "Gujarat", "city": "Vadodara",
        "radius_km": 100, "industry": "two_way_radio", "query_type": "meet",
    })
    assert denied.status_code == 401
    headers = {"Authorization": "Bearer secret"}
    created = client.post("/api/searches", headers=headers, json={
        "country_code": "IN", "state": "Gujarat", "city": "Vadodara",
        "radius_km": 100, "industry": "two_way_radio", "query_type": "meet",
    })
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["leads"][0]["name"] == "Example Radio"
    assert body["leads"][0]["email"] == ""
    exported = client.get(f"/api/searches/{body['id']}/export.csv", headers=headers)
    assert exported.status_code == 200
    assert "Example Radio" in exported.text
    assert "9876543210" in exported.text
    sheet = client.get(f"/api/searches/{body['id']}/export.xlsx", headers=headers)
    assert sheet.status_code == 200
    assert sheet.content[:2] == b"PK"


def test_missing_token_configuration_is_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("LEADS_TOKEN", "")
    monkeypatch.setenv("LEADS_DB_PATH", str(tmp_path / "closed.sqlite"))
    api.reset()
    closed = TestClient(api.app)
    assert closed.get("/api/meta").status_code == 503


def test_public_site_does_not_link_the_lead_page():
    for relative in ("website/index.html", "website/demo.html", "website/radio-hub.html"):
        text = (ROOT / relative).read_text(errors="ignore")
        assert "/leads" not in text
        assert "leads/" not in text
    page = (ROOT / "website/leads/index.html").read_text()
    assert 'name="robots" content="noindex, nofollow"' in page


def test_leads_page_is_served(client):
    response = client.get("/leads/")
    assert response.status_code == 200
    assert "noindex" in response.text
    assert "Find leads" in response.text
