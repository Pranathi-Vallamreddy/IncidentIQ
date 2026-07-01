"""API smoke tests over the real engine + persistence (in-memory SQLite)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_load_sample_then_dashboard(client):
    run = client.post("/api/samples/ecommerce-cascade.log/load").json()
    assert run["event_count"] > 0
    assert run["incident_count"] >= 5

    dash = client.get("/api/dashboard").json()
    kpi_keys = {k["key"] for k in dash["kpis"]}
    assert {"events", "active", "critical", "anomalies", "mttr"} <= kpi_keys
    assert dash["severity_distribution"]["Critical"] >= 1
    assert len(dash["timeline"]) > 0
    assert any(i["title"] == "Cascading failure detected" for i in dash["insights"])


def test_incident_detail_exposes_engine_reasoning(client):
    client.post("/api/samples/ecommerce-cascade.log/load")
    incidents = client.get("/api/incidents").json()
    payments = next(i for i in incidents if i["service"] == "payments-api")

    detail = client.get(f"/api/incidents/{payments['incident_id']}").json()
    cluster = detail["cluster"]
    assert cluster["template"]
    assert cluster["zscore"] > 0
    assert len(cluster["severity_factors"]) == 6
    assert len(cluster["example_logs"]) > 0
    assert any(c["kind"] == "dependency" for c in detail["correlations"])


def test_explain_falls_back_to_deterministic(client):
    client.post("/api/samples/ecommerce-cascade.log/load")
    incidents = client.get("/api/incidents").json()
    inc = incidents[0]["incident_id"]
    ex = client.post(f"/api/incidents/{inc}/explain").json()
    assert ex["source"] in ("gemini", "deterministic")
    assert ex["summary"] and ex["root_cause"]
    assert len(ex["suggested_fixes"]) >= 1


def test_filters_and_export(client):
    client.post("/api/samples/ecommerce-cascade.log/load")
    crit = client.get("/api/incidents?severity=Critical").json()
    assert all(i["severity"] == "Critical" for i in crit)
    csv = client.get("/api/incidents/export")
    assert csv.headers["content-type"].startswith("text/csv")
    assert "incident_id" in csv.text
