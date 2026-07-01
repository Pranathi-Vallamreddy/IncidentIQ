"""Integration tests over the generated marquee dataset.

These assert the *behaviour that matters for the product*: the cascade is
detected, severities order correctly, normal traffic is not an incident, and the
whole pipeline is deterministic.
"""

from pathlib import Path

import pytest

from app.data import generate_samples
from app.engine import pipeline
from app.engine.types import SEVERITY_ORDER

SAMPLES = Path(generate_samples.SAMPLES_DIR)


@pytest.fixture(scope="module", autouse=True)
def _ensure_samples():
    if not (SAMPLES / "ecommerce-cascade.log").exists():
        generate_samples.generate()


def _analyze(name):
    text = (SAMPLES / name).read_text(encoding="utf-8")
    return pipeline.analyze_text(name, text, sensitivity=0.6)


def test_cascade_dataset_detects_root_cause_and_downstream():
    result = _analyze("ecommerce-cascade.log")
    by_service = {i.service: i for i in result.incidents}

    assert "payments-api" in by_service
    assert "checkout-gateway" in by_service
    assert by_service["payments-api"].severity == "Critical"
    assert by_service["checkout-gateway"].severity == "Critical"


def test_cascade_correlation_links_payments_to_checkout():
    result = _analyze("ecommerce-cascade.log")
    by_service = {i.service: i for i in result.incidents}
    payments = by_service["payments-api"].incident_id
    checkout = by_service["checkout-gateway"].incident_id

    dep_links = [
        c for c in result.correlations
        if c.kind == "dependency" and c.upstream_id == payments and c.downstream_id == checkout
    ]
    assert dep_links, "expected payments-api -> checkout-gateway dependency correlation"
    assert dep_links[0].lag_seconds >= 0  # downstream ignites after upstream


def test_normal_info_traffic_is_not_an_incident():
    result = _analyze("ecommerce-cascade.log")
    titles = " ".join(i.title.lower() for i in result.incidents)
    # High-volume INFO baselines must not be surfaced as incidents.
    assert "processed payment intent" not in titles
    assert "login success" not in titles


def test_resolved_incident_detected_from_past_spike():
    result = _analyze("ecommerce-cascade.log")
    resolved = [i for i in result.incidents if i.status == "Resolved"]
    # analytics slow-query + edge-cache burst mid/early window then stopped.
    assert any(i.service == "analytics-api" for i in resolved)


def test_severity_labels_are_valid_and_confidence_bounded():
    result = _analyze("ecommerce-cascade.log")
    for inc in result.incidents:
        assert inc.severity in SEVERITY_ORDER
        assert 0.0 <= inc.confidence <= 1.0
        assert 0.0 <= inc.anomaly_score <= 1.0


def test_pipeline_is_deterministic():
    a = _analyze("ecommerce-cascade.log")
    b = _analyze("ecommerce-cascade.log")
    sig_a = [(i.incident_id, i.severity, i.status, i.service) for i in a.incidents]
    sig_b = [(i.incident_id, i.severity, i.status, i.service) for i in b.incidents]
    assert sig_a == sig_b
    assert len(a.clusters) == len(b.clusters)
