"""Fetch a public company page when robots.txt allows it."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx


@dataclass
class FetchedPage:
    url: str
    html: str
    status: int


class PageFetcher:
    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self.client = httpx.Client(
            timeout=12,
            headers={"User-Agent": user_agent, "Accept": "text/html"},
            follow_redirects=True,
        )
        self._robots: dict[str, RobotFileParser | None] = {}

    def close(self) -> None:
        self.client.close()

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            return False
        key = f"{parts.scheme}://{parts.netloc}"
        if key not in self._robots:
            self._robots[key] = self._load_robots(key)
        parser = self._robots[key]
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, url)

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        try:
            response = self.client.get(origin + "/robots.txt")
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        # parse() alone leaves last_checked at 0, and can_fetch then refuses every URL.
        parser.last_checked = time.time()
        return parser

    def fetch(self, url: str) -> FetchedPage | None:
        if not self.allowed(url):
            return None
        try:
            response = self.client.get(url)
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type and "text" not in content_type and content_type:
            return None
        return FetchedPage(url=str(response.url), html=response.text[:1_500_000], status=response.status_code)

    def reachable(self, url: str) -> bool:
        if not url or not self.allowed(url):
            return False
        try:
            response = self.client.head(url)
            if response.status_code in {405, 403}:
                response = self.client.get(url)
        except httpx.HTTPError:
            return False
        return response.status_code < 400


def contact_links(html: str, base_url: str) -> list[str]:
    found = []
    for href in re.findall(r"""href=["']([^"'#]+)["']""", html or "", flags=re.I):
        if not re.search(r"contact|about|team|leadership|our-team", href, re.I):
            continue
        absolute = urljoin(base_url, href)
        if urlsplit(absolute).netloc != urlsplit(base_url).netloc:
            continue
        if absolute not in found:
            found.append(absolute)
        if len(found) == 2:
            break
    return found
