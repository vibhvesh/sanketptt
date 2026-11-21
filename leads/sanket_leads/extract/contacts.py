"""Pull address, phone and email out of a public HTML page."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..textutil import phone_key, squash


EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
TEL_RE = re.compile(r"""href=["']tel:([^"'<>]+)["']""", re.I)
MAILTO_RE = re.compile(r"""href=["']mailto:([^"'?<>]+)["']""", re.I)
PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[\s\-]?)?(?:\(?0?\d{2,5}\)?[\s\-]?)?\d{3,5}[\s\-]?\d{4,6}"
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.I | re.S)

JUNK_EMAIL_HOSTS = {
    "example.com",
    "email.com",
    "domain.com",
    "sentry.io",
    "wixpress.com",
    "schema.org",
    "godaddy.com",
}
JUNK_EMAIL_PREFIXES = ("noreply", "no-reply", "donotreply", "sentry")


@dataclass
class PageContacts:
    name: str = ""
    address: str = ""
    phones: tuple[str, ...] = ()
    emails: tuple[str, ...] = ()
    text: str = ""


def visible_text(html: str) -> str:
    cleaned = SCRIPT_RE.sub(" ", html or "")
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.I)
    cleaned = re.sub(r"</(p|div|li|tr|h\d|td)>", "\n", cleaned, flags=re.I)
    cleaned = TAG_RE.sub(" ", cleaned)
    cleaned = cleaned.replace("&nbsp;", " ").replace("&amp;", "&")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s+", "\n", cleaned)
    return cleaned


def _clean_email(value: str) -> str:
    email = value.strip().strip(".").lower()
    if "@" not in email or email.count("@") != 1:
        return ""
    local, host = email.split("@", 1)
    if not local or not host or "." not in host:
        return ""
    if host in JUNK_EMAIL_HOSTS or any(local.startswith(prefix) for prefix in JUNK_EMAIL_PREFIXES):
        return ""
    if host.endswith((".png", ".jpg", ".svg", ".webp", ".js", ".css")):
        return ""
    return email


def _clean_phone(value: str) -> str:
    text = squash(value).strip(" .)")
    digits = re.sub(r"\D", "", text)
    if len(digits) < 8 or len(digits) > 15:
        return ""
    # Years and postcodes are not phones.
    if len(digits) == 4 or (len(digits) == 6 and not text.startswith(("+", "0"))):
        return ""
    return text


def _unique_phones(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    kept: list[str] = []
    for value in values:
        key = phone_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(value)
        if len(kept) == 3:
            break
    return tuple(kept)


def _address_from_text(text: str) -> str:
    labeled = re.search(
        r"Address\s*[:\-]\s*(.{12,220})",
        text,
        re.I,
    )
    if labeled:
        chunk = re.split(r"\b(Contact|Phone|Email|Tel|Mobile)\b", labeled.group(1), maxsplit=1)[0]
        return squash(chunk)[:220]

    pin = re.search(
        r"((?:Ground Floor|Plot|Shop|C[\-\s]?\d|No\.?\s*\d|\d{1,4}[,\s]).{8,160}?\b\d{6}\b)",
        text,
        re.I,
    )
    if pin:
        return squash(pin.group(1))[:220]

    region = re.search(
        r"([A-Z0-9][^|\n]{10,140}?\b(?:Gujarat|India)\b[^|\n]{0,20}\b\d{6}\b)",
        text,
    )
    if region:
        return squash(region.group(1))[:220]
    return ""


def _page_name(html: str) -> str:
    match = H1_RE.search(html) or TITLE_RE.search(html)
    if not match:
        return ""
    title = squash(TAG_RE.sub(" ", match.group(1)))
    title = re.sub(r"\s*[\|\-–—:].*$", "", title)
    title = re.sub(r"^(contact us|contact|home)\b", "", title, flags=re.I).strip(" -|")
    if len(title) < 3 or title.lower() in {"contact", "contact us", "home"}:
        return ""
    return title[:160]


def extract_contacts(html: str) -> PageContacts:
    text = visible_text(html)
    emails = []
    for raw in MAILTO_RE.findall(html or "") + EMAIL_RE.findall(text):
        cleaned = _clean_email(raw)
        if cleaned and cleaned not in emails:
            emails.append(cleaned)
    phones = []
    for raw in TEL_RE.findall(html or ""):
        cleaned = _clean_phone(raw)
        if cleaned:
            phones.append(cleaned)
    # Directory pages list dozens of numbers. Don't guess which one belongs
    # to the company when the page is a big listing.
    found = [_clean_phone(item) for item in PHONE_RE.findall(text)]
    found = [item for item in found if item]
    if len({phone_key(item) for item in found}) <= 6:
        phones.extend(found)
    address = _address_from_text(text)
    return PageContacts(
        name=_page_name(html or ""),
        address=address,
        phones=_unique_phones(phones),
        emails=tuple(emails[:3]),
        text=text[:4000],
    )
