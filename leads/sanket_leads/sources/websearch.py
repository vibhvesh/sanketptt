"""Free public web search. DuckDuckGo's HTML endpoint first, Bing as a fallback.

Results are links and snippets only. Contacts are taken later from the pages
themselves, never from a guess about what a snippet might mean.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import parse_qs, unquote, urlsplit

import httpx


@dataclass(frozen=True)
class WebHit:
    title: str
    url: str
    snippet: str


# People-search brokers and social networks. We do not scrape them.
SKIP_HOSTS = {
    "duckduckgo.com",
    "bing.com",
    "google.com",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "rocketreach.co",
    "contactout.com",
    "zoominfo.com",
    "lusha.com",
    "apollo.io",
    "signalhire.com",
    "wikipedia.org",
    "wikidata.org",
}


class WebSearch:
    def __init__(self, user_agent: str) -> None:
        self.client = httpx.Client(
            timeout=20,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html",
            },
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def search(self, query: str, limit: int = 8) -> list[WebHit]:
        hits = self._duckduckgo(query, limit)
        if hits:
            return hits
        return self._bing(query, limit)

    def _duckduckgo(self, query: str, limit: int) -> list[WebHit]:
        response = self.client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
        )
        if response.status_code >= 400 or "anomaly-modal" in response.text:
            return []
        hits = []
        for href, title in re.findall(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            response.text,
            flags=re.S,
        ):
            url = _ddg_url(href)
            if not url or _skip(url):
                continue
            snippet = ""
            hits.append(WebHit(_plain(title), url, snippet))
            if len(hits) >= limit:
                break
        # Attach the snippet that follows each result link when present.
        snippets = [
            _plain(item)
            for item in re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|td|span)', response.text, flags=re.S)
        ]
        for index, snippet in enumerate(snippets):
            if index < len(hits):
                hits[index] = WebHit(hits[index].title, hits[index].url, snippet)
        return hits

    def _bing(self, query: str, limit: int) -> list[WebHit]:
        response = self.client.get("https://www.bing.com/search", params={"q": query, "count": limit})
        if response.status_code >= 400:
            return []
        hits = []
        for part in re.split(r'<li class="b_algo"', response.text)[1:]:
            href_match = re.search(r'href="([^"]+)"', part)
            title_match = re.search(r"<h2>\s*<a[^>]*>(.*?)</a>", part, flags=re.S)
            snippet_match = re.search(r"<p[^>]*>(.*?)</p>", part, flags=re.S)
            if not href_match or not title_match:
                continue
            url = _bing_url(unescape(href_match.group(1)))
            if not url or _skip(url):
                continue
            hits.append(
                WebHit(
                    _plain(title_match.group(1)),
                    url,
                    _plain(snippet_match.group(1) if snippet_match else ""),
                )
            )
            if len(hits) >= limit:
                break
        return hits


def _plain(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", unescape(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _skip(url: str) -> bool:
    host = urlsplit(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == blocked or host.endswith("." + blocked) for blocked in SKIP_HOSTS)


def _ddg_url(href: str) -> str:
    href = unescape(href)
    query = parse_qs(urlsplit(href).query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    if href.startswith("http"):
        return href
    return ""


def _bing_url(href: str) -> str:
    match = re.search(r"[?&]u=a1([A-Za-z0-9_\-]+)", href)
    if not match:
        if "bing.com" in href:
            return ""
        return href
    raw = match.group(1)
    padding = "=" * ((4 - len(raw) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(raw + padding).decode("utf-8", "replace")
    except Exception:
        return ""
