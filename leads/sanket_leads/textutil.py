"""Small text helpers used by extraction, dedupe and storage."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


_WS = re.compile(r"\s+")
_LEGAL = re.compile(
    r"\b(pvt\.?|ltd\.?|private|limited|llc|inc\.?|co\.?|company|corporation)\b",
    re.I,
)


def squash(value: str) -> str:
    return _WS.sub(" ", (value or "").replace("\xa0", " ")).strip()


def norm_name(value: str) -> str:
    text = value.split("&")[0]
    text = _LEGAL.sub(" ", text.lower())
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return squash(text)


def search_name(value: str) -> str:
    """A shorter name that still finds the company, without legal suffixes."""
    return norm_name(value).title()


def host_of(url: str) -> str:
    if not url:
        return ""
    try:
        host = urlsplit(url if "://" in url else "https://" + url).netloc.lower()
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def phone_key(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def same_phone(left: str, right: str) -> bool:
    a, b = phone_key(left), phone_key(right)
    return bool(a) and a == b
