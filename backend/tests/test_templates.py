from datetime import datetime, timedelta, timezone

from app.engine.templates import WILDCARD, TemplateMiner
from app.engine.types import ParsedEvent

_T0 = datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc)


def _ev(message, level="ERROR", service="svc", i=0):
    return ParsedEvent(ts=_T0 + timedelta(seconds=i), level=level,
                       service=service, message=message, raw=message, line_no=i)


def test_similar_logs_collapse_to_one_template():
    miner = TemplateMiner()
    for i in range(5):
        miner.add_event(_ev(f"connection pool exhausted for db-{i} after {i*10}ms", i=i))
    templates = miner.get_templates()
    assert len(templates) == 1
    assert templates[0].count == 5


def test_distinct_messages_form_distinct_templates():
    miner = TemplateMiner()
    miner.add_event(_ev("connection pool exhausted", i=0))
    miner.add_event(_ev("checkout returned 500 upstream error", i=1))
    miner.add_event(_ev("user login succeeded", level="INFO", i=2))
    assert len(miner.get_templates()) == 3


def test_variable_word_position_becomes_wildcard():
    miner = TemplateMiner()
    miner.add_event(_ev("payment failed for account alice", i=0))
    miner.add_event(_ev("payment failed for account bob", i=1))
    template = miner.get_templates()[0]
    assert template.count == 2
    assert WILDCARD in template.tokens
    assert template.tokens[:3] == ["payment", "failed", "for"]


def test_template_tracks_most_severe_level_and_services():
    miner = TemplateMiner()
    miner.add_event(_ev("db error occurred", level="WARN", service="a", i=0))
    miner.add_event(_ev("db error occurred", level="ERROR", service="b", i=1))
    template = miner.get_templates()[0]
    assert template.level == "ERROR"  # most severe wins
    assert set(template.services) == {"a", "b"}


def test_ids_are_stable_and_sequential():
    miner = TemplateMiner()
    first = miner.add_event(_ev("alpha event one", i=0))
    second = miner.add_event(_ev("beta event two", i=1))
    assert first.template_id == "CLU-001"
    assert second.template_id == "CLU-002"
