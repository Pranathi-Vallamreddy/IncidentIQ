"""Log parser: raw text/NDJSON lines -> ParsedEvent.

Supports three input shapes, tried in order per line:
  1. NDJSON  - a JSON object with flexible key names.
  2. Structured text - "<timestamp> <LEVEL> <service> <message>" and common
     variants (bracketed level, "logger -" separators, syslog-ish).
  3. Fallback - the whole line becomes the message with level=UNKNOWN.

No line is ever dropped; unparseable lines still produce a ParsedEvent so counts
stay honest. Timestamps that cannot be parsed fall back to a monotonic synthetic
clock so downstream time-bucketing still works.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from .types import LEVEL_RANK, ParsedEvent

# Keys we accept for each field when reading JSON logs.
_JSON_TS_KEYS = ("timestamp", "time", "ts", "@timestamp", "datetime", "date")
_JSON_LEVEL_KEYS = ("level", "severity", "lvl", "loglevel", "log_level")
_JSON_SERVICE_KEYS = ("service", "svc", "logger", "component", "app", "source", "unit")
_JSON_MSG_KEYS = ("message", "msg", "log", "text", "event", "body")

_KNOWN_LEVELS = set(LEVEL_RANK.keys())

# A leading timestamp: ISO-8601 (with optional T, ms, timezone) or
# "YYYY-MM-DD HH:MM:SS[,.]ms". Captured greedily but bounded.
_TS_RE = re.compile(
    r"^\s*(?P<ts>"
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?"
    r")\s+"
)

# A level token, optionally bracketed: ERROR / [ERROR] / (WARN).
_LEVEL_RE = re.compile(r"^\s*[\[\(]?(?P<level>[A-Za-z]{3,9})[\]\)]?\s+")

# A service token right after the level: alphanumerics, dots, dashes, colons,
# slashes. Optionally followed by a " - " or ":" separator.
_SERVICE_RE = re.compile(r"^\s*(?P<service>[A-Za-z][\w.\-/]{1,40})\s*(?:[-:]\s+|\s+)")


def _coerce_ts(value) -> Optional[datetime]:
    """Best-effort parse of a timestamp value (str/number) to aware datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Heuristic: ms vs seconds epoch.
        seconds = value / 1000.0 if value > 1e11 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    raw = value.strip().replace(",", ".")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    # Normalise "YYYY-MM-DD HH:MM:SS" to ISO by inserting a T.
    candidates = [raw]
    if " " in raw and "T" not in raw:
        candidates.append(raw.replace(" ", "T", 1))
    for cand in candidates:
        try:
            dt = datetime.fromisoformat(cand)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _norm_level(level: Optional[str]) -> str:
    if not level:
        return "UNKNOWN"
    up = level.upper()
    return up if up in _KNOWN_LEVELS else "UNKNOWN"


def _first_key(obj: dict, keys: Iterable[str]):
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return None


class LogParser:
    """Stateful parser so synthetic timestamps stay monotonic across a file."""

    def __init__(self, base_time: Optional[datetime] = None):
        # Anchor for synthetic timestamps when a line has none.
        self._synthetic = base_time or datetime.now(timezone.utc)
        self._synthetic_step = timedelta(seconds=1)

    def _next_synthetic(self) -> datetime:
        ts = self._synthetic
        self._synthetic += self._synthetic_step
        return ts

    def parse_line(self, line: str, line_no: int = 0) -> Optional[ParsedEvent]:
        raw = line.rstrip("\n").rstrip("\r")
        if not raw.strip():
            return None

        stripped = raw.lstrip()
        if stripped.startswith("{"):
            event = self._parse_json(stripped, raw, line_no)
            if event is not None:
                return event

        return self._parse_text(raw, line_no)

    def _parse_json(self, stripped: str, raw: str, line_no: int) -> Optional[ParsedEvent]:
        try:
            obj = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(obj, dict):
            return None

        ts = _coerce_ts(_first_key(obj, _JSON_TS_KEYS)) or self._next_synthetic()
        level = _norm_level(_first_key(obj, _JSON_LEVEL_KEYS))
        service = _first_key(obj, _JSON_SERVICE_KEYS)
        message = _first_key(obj, _JSON_MSG_KEYS)
        if message is None:
            # No obvious message field: fold remaining scalars into a message.
            skip = set(_JSON_TS_KEYS + _JSON_LEVEL_KEYS + _JSON_SERVICE_KEYS)
            parts = [f"{k}={v}" for k, v in obj.items() if k not in skip]
            message = " ".join(parts) if parts else stripped
        return ParsedEvent(
            ts=ts,
            level=level,
            service=str(service) if service is not None else None,
            message=str(message).strip(),
            raw=raw,
            line_no=line_no,
        )

    def _parse_text(self, raw: str, line_no: int) -> ParsedEvent:
        rest = raw
        ts: Optional[datetime] = None
        level = "UNKNOWN"
        service: Optional[str] = None

        m = _TS_RE.match(rest)
        if m:
            ts = _coerce_ts(m.group("ts"))
            rest = rest[m.end():]

        m = _LEVEL_RE.match(rest)
        if m:
            candidate = _norm_level(m.group("level"))
            if candidate != "UNKNOWN":
                level = candidate
                rest = rest[m.end():]

        # Only try to peel a service token when we successfully found a level;
        # otherwise the "service" heuristic would eat real message words.
        if level != "UNKNOWN":
            m = _SERVICE_RE.match(rest)
            if m:
                token = m.group("service")
                # A service token should look like an identifier, not a sentence
                # word: require a dot/dash/slash or a known-ish shape.
                if re.search(r"[.\-/]", token) or token.islower():
                    service = token
                    rest = rest[m.end():]

        message = rest.strip() or raw.strip()
        return ParsedEvent(
            ts=ts or self._next_synthetic(),
            level=level,
            service=service,
            message=message,
            raw=raw,
            line_no=line_no,
        )

    def parse(self, lines: Iterable[str]) -> list[ParsedEvent]:
        events: list[ParsedEvent] = []
        for i, line in enumerate(lines):
            event = self.parse_line(line, line_no=i + 1)
            if event is not None:
                events.append(event)
        return events


def parse_text(text: str, base_time: Optional[datetime] = None) -> list[ParsedEvent]:
    """Convenience: parse a whole blob of log text."""
    return LogParser(base_time=base_time).parse(text.splitlines())
