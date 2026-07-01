from datetime import datetime, timezone

from app.engine.parser import LogParser, parse_text


def test_parses_structured_text_line():
    line = "2026-06-30T13:45:12.031Z ERROR payments-api connection pool exhausted after 5031ms"
    event = LogParser().parse_line(line)
    assert event is not None
    assert event.level == "ERROR"
    assert event.service == "payments-api"
    assert "connection pool exhausted" in event.message
    assert event.ts == datetime(2026, 6, 30, 13, 45, 12, 31000, tzinfo=timezone.utc)


def test_parses_ndjson_with_flexible_keys():
    line = '{"time": "2026-06-30T10:00:00Z", "severity": "warn", "svc": "auth", "msg": "slow"}'
    event = LogParser().parse_line(line)
    assert event.level == "WARN"
    assert event.service == "auth"
    assert event.message == "slow"


def test_bracketed_level_and_unknown_fallback():
    event = LogParser().parse_line("2026-06-30 10:00:00 [WARN] worker something happened")
    assert event.level == "WARN"

    # A line with no recognisable structure still yields an event (never dropped).
    event2 = LogParser().parse_line("totally freeform text with no level")
    assert event2.level == "UNKNOWN"
    assert event2.message == "totally freeform text with no level"


def test_synthetic_timestamps_are_monotonic():
    events = parse_text("no timestamp one\nno timestamp two\nno timestamp three")
    times = [e.ts for e in events]
    assert times == sorted(times)
    assert len(set(times)) == 3


def test_blank_lines_skipped():
    events = parse_text("line one\n\n   \nline two")
    assert len(events) == 2
