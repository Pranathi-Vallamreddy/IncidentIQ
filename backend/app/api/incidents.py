"""Incident explorer, detail (centerpiece), explanation, and CSV export."""

from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..ai.explainer import ExplainInput
from ..ai.service import generate_explanation
from ..db import get_db
from ..services import analysis, detail
from ..services.settings import get_settings

router = APIRouter(tags=["incidents"])

_SEV_RANK = {"Critical": 3, "High": 2, "Medium": 1, "Low": 0}


def _incident_out(i, baseline_rate=0.0) -> schemas.IncidentOut:
    return schemas.IncidentOut(
        incident_id=i.incident_id, cluster_id=i.cluster_id, title=i.title,
        service=i.service, severity=i.severity, confidence=i.confidence,
        status=i.status, anomaly_score=i.anomaly_score, growth_pct=i.growth_pct,
        baseline_rate=baseline_rate, count=i.count, first_seen=i.first_seen,
        last_seen=i.last_seen, correlated_ids=list(i.correlated_ids or []),
    )


@router.get("/incidents", response_model=list[schemas.IncidentOut])
def list_incidents(
    run_id: Optional[int] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[schemas.IncidentOut]:
    run = analysis.get_run(db, run_id)
    if run is None:
        return []
    incidents = analysis.run_incidents(db, run.id)
    baseline = {c.cluster_id: c.baseline_rate for c in analysis.run_clusters(db, run.id)}

    if severity and severity.lower() != "all":
        incidents = [i for i in incidents if i.severity.lower() == severity.lower()]
    if status and status.lower() != "all":
        incidents = [i for i in incidents if i.status.lower() == status.lower()]
    if q:
        needle = q.lower()
        incidents = [i for i in incidents if needle in i.title.lower()
                     or needle in (i.service or "").lower()
                     or needle in i.incident_id.lower()
                     or needle in i.cluster_id.lower()]

    incidents.sort(key=lambda i: (_SEV_RANK.get(i.severity, 0), i.confidence), reverse=True)
    return [_incident_out(i, baseline.get(i.cluster_id, 0.0)) for i in incidents]


@router.get("/incidents/export")
def export_incidents(
    run_id: Optional[int] = Query(default=None), db: Session = Depends(get_db)
) -> StreamingResponse:
    run = analysis.get_run(db, run_id)
    incidents = analysis.run_incidents(db, run.id) if run else []
    incidents.sort(key=lambda i: (_SEV_RANK.get(i.severity, 0), i.confidence), reverse=True)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["incident_id", "severity", "title", "service", "cluster_id",
                     "confidence", "status", "anomaly_score", "growth_pct",
                     "count", "first_seen", "last_seen"])
    for i in incidents:
        writer.writerow([i.incident_id, i.severity, i.title, i.service or "", i.cluster_id,
                         f"{i.confidence:.2f}", i.status, f"{i.anomaly_score:.2f}",
                         f"{i.growth_pct:.0f}", i.count,
                         i.first_seen.isoformat(), i.last_seen.isoformat()])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=incidents.csv"},
    )


@router.get("/incidents/{incident_id}", response_model=schemas.IncidentDetailOut)
def get_incident(
    incident_id: str,
    run_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> schemas.IncidentDetailOut:
    run = analysis.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No analysis run available")
    result = detail.build_incident_detail(db, run, incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@router.post("/incidents/{incident_id}/explain", response_model=schemas.ExplanationOut)
def explain_incident(
    incident_id: str,
    run_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> schemas.ExplanationOut:
    run = analysis.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No analysis run available")
    incident = detail.find_incident(db, run.id, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    cluster = detail.find_cluster(db, run.id, incident.cluster_id)

    correlations = analysis.run_correlations(db, run.id)
    upstream = [c.upstream_id for c in correlations if c.downstream_id == incident_id]
    downstream = [c.downstream_id for c in correlations if c.upstream_id == incident_id]

    inp = ExplainInput(
        incident_id=incident.incident_id, title=incident.title, service=incident.service,
        severity=incident.severity, status=incident.status, confidence=incident.confidence,
        anomaly_score=incident.anomaly_score, zscore=cluster.zscore if cluster else 0.0,
        growth_pct=incident.growth_pct, baseline_rate=cluster.baseline_rate if cluster else 0.0,
        count=incident.count, level=cluster.level if cluster else "UNKNOWN",
        template=cluster.template if cluster else incident.title,
        example=cluster.example if cluster else "",
        upstream=upstream, downstream=downstream,
    )

    use_ai = get_settings(db).ai_root_cause
    source, payload = generate_explanation(inp, use_ai=use_ai)

    incident.explanation = payload
    incident.explanation_source = source
    db.commit()

    return schemas.ExplanationOut(source=source, summary=payload["summary"],
                                  root_cause=payload["root_cause"],
                                  suggested_fixes=payload["suggested_fixes"])
