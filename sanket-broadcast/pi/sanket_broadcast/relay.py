"""Safe PTT line-to-line relay policy engine.

This module decides *where* a received PTT event may be forwarded. It does not
publish MQTT messages or copy audio itself; the transport adapter must preserve
the returned relay metadata when publishing to prevent network-level loops.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any, Iterable


@dataclass(frozen=True)
class RelayRule:
    rule_id: str
    source: str
    destinations: tuple[str, ...]
    enabled: bool = True
    priority: int = 0
    max_hops: int = 4


@dataclass
class RelayDecision:
    event_id: str
    destinations: list[str]
    blocked: dict[str, str] = field(default_factory=dict)
    rule_ids: list[str] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return bool(self.destinations)


class RelayEngine:
    """Evaluate relay rules with deduplication, hop limits and source-echo guards."""

    def __init__(self, rules: Iterable[RelayRule], *, dedupe_ttl: float = 30.0,
                 max_cache_entries: int = 10000, clock=time.monotonic):
        self.rules = tuple(sorted(rules, key=lambda r: (-r.priority, r.rule_id)))
        self.dedupe_ttl = max(1.0, float(dedupe_ttl))
        self.max_cache_entries = max(100, int(max_cache_entries))
        self.clock = clock
        self._seen: dict[str, float] = {}

    @staticmethod
    def stable_event_id(event: dict[str, Any]) -> str:
        supplied = str(event.get("event_id") or "").strip()
        if supplied:
            return supplied
        # Fallback is deterministic; adapters should provide a source event ID.
        stable = {k: event.get(k) for k in ("source", "sequence", "timestamp", "speaker_id")}
        payload = json.dumps(stable, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _prune(self, now: float) -> None:
        expired = [key for key, seen_at in self._seen.items()
                   if now - seen_at > self.dedupe_ttl]
        for key in expired:
            self._seen.pop(key, None)
        if len(self._seen) > self.max_cache_entries:
            oldest = sorted(self._seen.items(), key=lambda item: item[1])
            for key, _ in oldest[:len(self._seen) - self.max_cache_entries]:
                self._seen.pop(key, None)

    def evaluate(self, event: dict[str, Any]) -> RelayDecision:
        source = str(event.get("source") or "").strip()
        event_id = self.stable_event_id(event)
        now = self.clock()
        self._prune(now)
        if not source:
            return RelayDecision(event_id, [], {"*": "missing_source"})

        if event_id in self._seen:
            return RelayDecision(event_id, [], {"*": "duplicate_event"})
        self._seen[event_id] = now

        try:
            hops = int(event.get("relay_hops", 0))
        except (TypeError, ValueError):
            hops = 0
        visited = {str(item) for item in (event.get("relay_path") or [])}
        visited.add(source)
        origin = str(event.get("origin_channel") or source)

        destinations: list[str] = []
        blocked: dict[str, str] = {}
        matched_rules: list[str] = []
        for rule in self.rules:
            if not rule.enabled or rule.source != source:
                continue
            matched_rules.append(rule.rule_id)
            if hops >= max(1, rule.max_hops):
                blocked[rule.rule_id] = "hop_limit"
                continue
            for destination in rule.destinations:
                dest = str(destination).strip()
                if not dest:
                    continue
                if dest == source or dest == origin or dest in visited:
                    blocked[dest] = "loop_or_source_echo"
                    continue
                if dest not in destinations:
                    destinations.append(dest)

        return RelayDecision(event_id, destinations, blocked, matched_rules)

    @staticmethod
    def relay_metadata(event: dict[str, Any], destination: str,
                       event_id: str) -> dict[str, Any]:
        """Metadata that the MQTT adapter must attach to the forwarded event."""
        source = str(event.get("source") or "")
        path = [str(item) for item in (event.get("relay_path") or [])]
        if source and (not path or path[-1] != source):
            path.append(source)
        return {
            "event_id": event_id,
            "origin_channel": str(event.get("origin_channel") or source),
            "relay_path": path,
            "relay_hops": int(event.get("relay_hops", 0)) + 1,
            "relay_destination": destination,
        }
