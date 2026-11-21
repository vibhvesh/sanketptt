"""Run one lead search. Query types share geocoding, then diverge.

Meet in person, email/phone and industry sweep collect places. Contact person
uses a separate pass that only keeps a name found beside a job title.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .extract.contacts import extract_contacts
from .extract.people import TITLES, extract_people
from .geo import circle_box, haversine, round_km
from .industries import Industry, get_industry
from .models import Lead, Query
from .sources.fetch import contact_links
from .storage import Store, fill_blanks, make_key
from .textutil import host_of, norm_name, search_name, squash
from .verify import apply_verification


@dataclass
class Services:
    nominatim: object
    overpass: object
    photon: object
    web: object
    fetcher: object


_BUDGETS = {
    "meet": {"terms": 2, "web": 2, "pages": 4, "enrich": 2},
    "contacts": {"terms": 2, "web": 2, "pages": 5, "enrich": 3},
    "sweep": {"terms": 3, "web": 1, "pages": 3, "enrich": 0},
    "person": {"terms": 1, "web": 3, "pages": 6, "enrich": 0},
}


def run_search(query: Query, store: Store, services: Services) -> dict:
    industry = get_industry(query.industry)
    log: list[str] = []
    warnings: list[str] = []
    _locate(query, services, log)
    reused: list[Lead] = []
    reused_from: list[int] = []
    if query.use_cache:
        cover = store.covering(query)
        if cover is not None:
            reused = store.leads_for(cover["id"], query)
            log.append(
                f"Reused {len(reused)} saved leads from search {cover['id']} (last 24 hours). No new external search."
            )
            return store.save_search(
                query, _sort(query, reused), reused_from=[cover["id"]], warnings=warnings, log=log, external=False
            )
        for row in store.overlapping(query):
            reused_from.append(row["id"])
            for lead in store.leads_for(row["id"], query):
                if all(lead.dedupe_key != existing.dedupe_key for existing in reused):
                    reused.append(lead)
        if reused:
            log.append(f"Starting from {len(reused)} overlapping saved leads. Looking only for new places.")

    known = {lead.dedupe_key for lead in reused}
    fresh = _discover(query, industry, services, log, warnings)
    fresh = [lead for lead in fresh if make_key(lead) not in known]
    if query.query_type == "person":
        fresh = _find_people(query, industry, fresh, services, log, warnings)
    else:
        _enrich_missing_phones(query, fresh, services, log)
        _attach_distance(query, fresh)
    if query.query_type == "contacts":
        _check_sites(fresh, services, log)
    for lead in fresh:
        apply_verification(lead)
        lead.dedupe_key = make_key(lead)
    log.append("Candidates: " + (", ".join(lead.name for lead in fresh[:12]) or "none"))
    combined = _filter(query, industry, reused + fresh)
    if query.query_type == "contacts":
        full = sum(1 for lead in combined if _complete_contact(lead))
        log.append(f"{full} of {len(combined)} leads have email, phone and address.")
    if not combined:
        warnings.append("No public record matched this search. Empty fields are left blank rather than guessed.")
    return store.save_search(
        query,
        combined,
        reused_from=reused_from,
        warnings=warnings,
        log=log,
        external=True,
    )


def _locate(query: Query, services: Services, log: list[str]) -> None:
    if query.query_type == "sweep":
        target = ", ".join(part for part in (query.state, query.country) if part)
    else:
        target = query.place_label
    hit = services.nominatim.geocode(target, query.country_code)
    if hit is None:
        raise LookupError(f"Could not locate {target} on the map.")
    query.lat = hit.lat
    query.lon = hit.lon
    if query.query_type == "sweep" and hit.bbox:
        query.bbox = hit.bbox
    else:
        query.bbox = circle_box(hit.lat, hit.lon, query.radius_km)
    log.append(f"Located {target} at {hit.lat:.4f}, {hit.lon:.4f}.")


def _discover(query, industry: Industry, services: Services, log, warnings) -> list[Lead]:
    budget = _BUDGETS[query.query_type]
    found: list[Lead] = []
    box = query.bbox
    for term in industry.photon_terms[: budget["terms"]]:
        _collect(found, _safe(log, "Photon", lambda term=term: services.photon.search(term, box)))
    for term in industry.nominatim_terms[: budget["terms"]]:
        _collect(
            found,
            _safe(
                log,
                "Nominatim",
                lambda term=term: services.nominatim.search_bounded(term, box, query.country_code),
            ),
        )
    overpass_leads = _safe(log, "Overpass", lambda: services.overpass.search(industry, box))
    if overpass_leads is None:
        warnings.append("Overpass did not answer. OpenStreetMap results came from Nominatim and Photon only.")
    else:
        _collect(found, overpass_leads)
    place = query.area_label
    queries = tuple(item.format(place=place) for item in industry.web_queries[: budget["web"]])
    if query.query_type == "person":
        titles = industry.person_titles[: budget["web"]] or TITLES[: budget["web"]]
        queries = tuple(f'"{title}" {place}' for title in titles)
    pages = 0
    attempts = 0
    for text in queries:
        hits = _safe(log, "Web search", lambda text=text: services.web.search(text, limit=8)) or []
        log.append(f'Web search "{text}" returned {len(hits)} links.')
        for hit in hits:
            if pages >= budget["pages"] or attempts >= 8:
                break
            blob = " ".join((hit.title, hit.snippet, hit.url))
            if query.query_type != "person" and not _relevant_text(industry, blob):
                continue
            attempts += 1
            page = services.fetcher.fetch(hit.url)
            if page is None:
                log.append(f"Skipped {hit.url} (blocked, robots.txt, or no HTML).")
                continue
            pages += 1
            extracted = extract_contacts(page.html)
            lead = Lead(
                name=extracted.name or hit.title,
                address=extracted.address,
                phone="; ".join(extracted.phones),
                email=extracted.emails[0] if extracted.emails else "",
                website=page.url,
                source=page.url,
                notes=hit.snippet,
                phone_on_site=bool(extracted.phones),
                email_on_site=bool(extracted.emails),
                address_on_site=bool(extracted.address),
                website_ok=True,
                country=query.country,
                state=query.state,
            )
            if query.query_type == "person":
                people = extract_people(page.html, industry.person_titles or TITLES)
                if people:
                    lead.contact_name = people[0].name
                    lead.contact_title = people[0].title
                lead.notes = (lead.notes + " " + extracted.text[:400]).strip()
            blob = " ".join((lead.name, extracted.text[:1500], hit.snippet, lead.contact_title))
            if query.query_type == "person" or _relevant_text(industry, blob):
                _collect(found, [lead])
    if query.query_type == "person":
        kept = found
    else:
        kept = [lead for lead in found if _relevant_text(industry, f"{lead.name} {lead.category} {lead.notes}")]
    log.append(f"Collected {len(kept)} relevant places before filtering.")
    return kept


def _enrich_missing_phones(query, leads: list[Lead], services: Services, log) -> None:
    budget = _BUDGETS[query.query_type]["enrich"]
    enriched = 0
    for lead in leads:
        if lead.phone or enriched >= budget:
            continue
        name = search_name(lead.name)
        if len(name) < 4:
            continue
        hint = lead.city or query.city
        company_query = f"{name} {hint} contact".strip()
        hits = _safe(log, "Company search", lambda company_query=company_query: services.web.search(company_query, limit=6)) or []
        log.append(f'Company search "{company_query}" returned {len(hits)} links.')
        for hit in hits:
            if host_of(hit.url) and lead.website and host_of(hit.url) == host_of(lead.website):
                page_url = hit.url
            else:
                page_url = hit.url
            page = services.fetcher.fetch(page_url)
            if page is None:
                continue
            if not _mentions_company(page.html, lead.name):
                log.append(f"Ignored {page.url} because it does not mention {lead.name}.")
                continue
            extracted = extract_contacts(page.html)
            if not extracted.phones and not extracted.emails:
                for extra in contact_links(page.html, page.url)[:1]:
                    extra_page = services.fetcher.fetch(extra)
                    if extra_page:
                        extracted = extract_contacts(extra_page.html)
                        page = extra_page
                        if extracted.phones or extracted.emails:
                            break
            if extracted.phones and not lead.phone:
                lead.phone = "; ".join(extracted.phones)
                lead.phone_on_site = True
            if extracted.emails and not lead.email:
                lead.email = extracted.emails[0]
                lead.email_on_site = True
            if not lead.website:
                lead.website = page.url
                lead.website_ok = True
            if lead.phone or lead.email:
                lead.source = (lead.source + "; " + page.url).strip("; ")
                log.append(f"Filled public contact for {lead.name} from {page.url}.")
                enriched += 1
                break
    _geocode_addresses(query, leads, services, log)


def _find_people(query, industry: Industry, leads, services, log, warnings) -> list[Lead]:
    """Separate from the business search: only a name printed next to a title is kept."""
    people: list[Lead] = []
    for lead in leads:
        if lead.contact_name:
            people.append(lead)
            continue
        if not lead.website:
            continue
        page = services.fetcher.fetch(lead.website)
        if page is None:
            continue
        pages = [page]
        for link in contact_links(page.html, page.url):
            extra = services.fetcher.fetch(link)
            if extra:
                pages.append(extra)
        for fetched in pages:
            hits = extract_people(fetched.html, industry.person_titles or TITLES)
            if not hits:
                continue
            people.append(
                replace(
                    lead,
                    contact_name=hits[0].name,
                    contact_title=hits[0].title,
                    source=fetched.url,
                    notes=f"Name and title found on {fetched.url}",
                )
            )
            break
    if not people:
        warnings.append("No named decision-maker was found on a public page for this search.")
    log.append(f"Contact-person pass kept {len(people)} named people.")
    _geocode_addresses(query, people, services, log)
    _attach_distance(query, people)
    return people


def _geocode_addresses(query, leads, services, log) -> None:
    budget = 4
    used = 0
    for lead in leads:
        if lead.lat is not None or not lead.address or used >= budget:
            continue
        hit = _safe(log, "Address geocode", lambda lead=lead: services.nominatim.geocode(lead.address, query.country_code))
        used += 1
        if not hit:
            continue
        lead.lat = hit.lat
        lead.lon = hit.lon
        if not lead.city:
            lead.city = (hit.address or {}).get("city") or (hit.address or {}).get("town") or ""
        if not lead.state:
            lead.state = (hit.address or {}).get("state") or ""


def _attach_distance(query: Query, leads: list[Lead]) -> None:
    if query.lat is None:
        return
    for lead in leads:
        if lead.lat is None:
            continue
        lead.distance_km = round_km(haversine(query.lat, query.lon, lead.lat, lead.lon))


def _filter(query: Query, industry: Industry, leads: list[Lead]) -> list[Lead]:
    chosen: list[Lead] = []
    seen = set()
    for lead in leads:
        lead.name = squash(lead.name)[:160]
        if not lead.name:
            continue
        lead.dedupe_key = lead.dedupe_key or make_key(lead)
        if lead.dedupe_key in seen:
            continue
        if query.query_type != "person" and not _relevant_text(
            industry, f"{lead.name} {lead.category} {lead.notes} {lead.address}"
        ):
            continue
        if query.query_type == "sweep":
            if query.bbox and lead.lat is not None:
                south, west, north, east = query.bbox
                if not (south <= lead.lat <= north and west <= lead.lon <= east):
                    continue
        elif query.query_type == "person":
            if not lead.contact_name:
                continue
            mentioned = query.city.lower() in f"{lead.address} {lead.notes} {lead.city}".lower() if query.city else False
            in_radius = lead.distance_km is not None and lead.distance_km <= query.radius_km
            if not in_radius and not mentioned:
                continue
        else:
            if lead.distance_km is None or lead.distance_km > query.radius_km:
                continue
            if query.query_type == "meet" and not (lead.address and lead.phone):
                continue
            if query.query_type == "contacts" and not (lead.address and (lead.phone or lead.email)):
                continue
        if not lead.country:
            lead.country = query.country
        seen.add(lead.dedupe_key)
        chosen.append(lead)
    return _sort(query, chosen)


def _check_sites(leads: list[Lead], services: Services, log: list[str]) -> None:
    checked = 0
    for lead in leads:
        if not lead.website or lead.website_ok is not None or checked >= 4:
            continue
        lead.website_ok = bool(services.fetcher.reachable(lead.website))
        checked += 1
        log.append(f"Website {lead.website} reachable: {lead.website_ok}.")


def _sort(query: Query, leads: list[Lead]) -> list[Lead]:
    if query.query_type == "contacts":
        ordered = sorted(
            leads,
            key=lambda lead: (-_verified_score(lead), lead.distance_km if lead.distance_km is not None else 9999),
        )
    elif query.query_type in {"meet", "person"}:
        ordered = sorted(leads, key=lambda lead: (lead.distance_km is None, lead.distance_km or 0))
    else:
        ordered = sorted(leads, key=lambda lead: lead.name.lower())
    for lead in ordered:
        lead.notes = squash(lead.notes)[:400]
    return ordered[:40]


def _verified_score(lead: Lead) -> int:
    score = 0
    for key in ("email", "phone", "address", "website"):
        if (lead.verification.get(key) or {}).get("verified"):
            score += 1
    return score


def _complete_contact(lead: Lead) -> bool:
    return bool(lead.email and lead.phone and lead.address)


_GENERIC_NAME_TOKENS = {
    "technologies", "technology", "services", "service", "systems", "system",
    "solutions", "communications", "communication", "company", "group", "india",
    "private", "limited", "enterprises", "enterprise", "industries", "industry",
}


def _mentions_company(html: str, name: str) -> bool:
    """A contact page only counts when it is actually about this company."""
    from .extract.contacts import visible_text

    tokens = [token for token in norm_name(name).split() if token not in _GENERIC_NAME_TOKENS and len(token) >= 4]
    if not tokens:
        return False
    blob = visible_text(html).lower()
    found = [token for token in tokens if token in blob]
    if not found:
        return False
    distinctive = [token for token in tokens if len(token) >= 6]
    if distinctive:
        return any(token in found for token in distinctive)
    return True


def _has_term(blob: str, term: str) -> bool:
    if not term:
        return False
    if " " in term or "-" in term or len(term) >= 6:
        return term in blob
    return re.search(rf"\b{re.escape(term)}\b", blob) is not None


def _relevant_text(industry: Industry, text: str) -> bool:
    blob = (text or "").lower()
    if any(_has_term(blob, term) for term in industry.reject):
        return False
    if any(_has_term(blob, category) for category in industry.always_categories):
        return True
    return any(_has_term(blob, term) for term in industry.keep)


def _collect(found: list[Lead], incoming: list[Lead] | None) -> None:
    if not incoming:
        return
    for lead in incoming:
        match = _match(found, lead)
        if match is None:
            found.append(lead)
        else:
            fill_blanks(match, lead)


def _match(found: list[Lead], incoming: Lead) -> Lead | None:
    incoming_name = set(norm_name(incoming.name).split()) - {"and", "the", "of"}
    for lead in found:
        if incoming.osm_id and lead.osm_id == incoming.osm_id:
            return lead
        current_name = set(norm_name(lead.name).split()) - {"and", "the", "of"}
        if not incoming_name or not current_name:
            continue
        overlap = len(incoming_name & current_name) / len(incoming_name | current_name)
        if overlap >= 0.5:
            return lead
    return None


def _safe(log: list[str], label: str, fn):
    try:
        return fn()
    except Exception as exc:
        log.append(f"{label} failed ({exc.__class__.__name__}).")
        return None
