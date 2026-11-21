"""Find a named decision-maker next to a job title on a public page.

Names are returned only when the page text places a person-like name beside a
title. A title with no name produces nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .contacts import visible_text
from ..textutil import squash


TITLES = (
    "Head of Security",
    "Chief Security Officer",
    "Security Manager",
    "Plant Head",
    "Plant Manager",
    "Works Manager",
    "Operations Director",
    "Director of Operations",
    "Ops Director",
    "Operations Manager",
    "General Manager",
    "Managing Director",
    "Mine Manager",
    "Warehouse Manager",
    "Medical Superintendent",
    "Superintendent of Police",
    "Project Director",
    "Project Manager",
)

_STOP = {
    "the", "our", "this", "contact", "email", "phone", "head", "plant",
    "security", "director", "manager", "india", "office", "team", "click",
    "view", "home", "about", "mr", "mrs", "ms", "dr",
}


@dataclass(frozen=True)
class PersonHit:
    name: str
    title: str


def _title_pattern() -> str:
    ordered = sorted(TITLES, key=len, reverse=True)
    return "|".join(re.escape(title) for title in ordered)


def _good_name(value: str) -> bool:
    words = squash(value).split()
    if not 2 <= len(words) <= 4:
        return False
    if words[0].lower().strip(".") in _STOP:
        return False
    for word in words:
        if not re.match(r"^[A-Z][a-zA-Z'.-]{1,20}$", word):
            return False
        if word.lower() in _STOP:
            return False
    return True


def extract_people(html: str, titles: tuple[str, ...] | None = None) -> list[PersonHit]:
    text = squash(visible_text(html).replace("\n", " "))
    if not text:
        return []
    allowed = {title.lower() for title in (titles or TITLES)}
    title_re = _title_pattern()
    patterns = (
        rf"([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){{1,3}})\s*[,–\-]\s*({title_re})\b",
        rf"({title_re})\s*[:\-–]\s*([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){{1,3}})",
    )
    found: list[PersonHit] = []
    seen: set[tuple[str, str]] = set()
    for index, pattern in enumerate(patterns):
        for match in re.finditer(pattern, text):
            if index == 0:
                name, title = match.group(1), match.group(2)
            else:
                title, name = match.group(1), match.group(2)
            if title.lower() not in allowed or not _good_name(name):
                continue
            key = (name.lower(), title.lower())
            if key in seen:
                continue
            seen.add(key)
            found.append(PersonHit(name=squash(name), title=title))
    return found
