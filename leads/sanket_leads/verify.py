"""Check that a contact is real: MX for email, HTTP for the site, and where it was found.

Nothing here invents a value. A blank field stays blank and is not marked verified.
"""

from __future__ import annotations

from typing import Callable, Optional

import dns.resolver

from .models import Lead


MxLookup = Callable[[str], bool]


def domain_has_mx(domain: str, lookup: Optional[MxLookup] = None) -> bool:
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain or "." not in domain or " " in domain:
        return False
    if lookup is not None:
        return bool(lookup(domain))
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5.0)
    except Exception:
        return False
    return any(getattr(item, "preference", None) is not None for item in answers)


def apply_verification(lead: Lead, lookup: Optional[MxLookup] = None) -> Lead:
    email = (lead.email or "").strip()
    mx = False
    if email and "@" in email:
        mx = domain_has_mx(email.split("@", 1)[1], lookup)
    lead.mx_ok = mx if email else None

    def field(value: str, verified: bool, checks: list[str]) -> dict:
        if not value:
            return {"value": "", "verified": False, "checks": []}
        return {"value": value, "verified": bool(verified), "checks": checks}

    email_checks = []
    if email and lead.email_on_site:
        email_checks.append("found_on_site")
    if email and mx:
        email_checks.append("mx")

    phone_checks = []
    if lead.phone and lead.phone_on_site:
        phone_checks.append("found_on_site")
    elif lead.phone and lead.address_from_osm and not lead.phone_on_site:
        phone_checks.append("listed_on_osm")

    address_checks = []
    if lead.address and lead.address_on_site:
        address_checks.append("found_on_site")
    if lead.address and lead.address_from_osm:
        address_checks.append("listed_on_osm")

    site_checks = []
    if lead.website and lead.website_ok:
        site_checks.append("http_ok")

    lead.verification = {
        "email": field(email, bool(email) and lead.email_on_site and mx, email_checks),
        "phone": field(lead.phone, bool(lead.phone) and lead.phone_on_site, phone_checks),
        "address": field(
            lead.address,
            bool(lead.address) and (lead.address_on_site or lead.address_from_osm),
            address_checks,
        ),
        "website": field(lead.website, bool(lead.website) and bool(lead.website_ok), site_checks),
    }
    return lead
