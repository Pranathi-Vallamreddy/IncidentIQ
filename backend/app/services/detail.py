"""Build the Incident Detail payload — the technical centerpiece.

Exposes the full engine reasoning for one incident: detected template, a
normalized example, cluster stats, the anomaly z-score, the weighted severity
breakdown, confidence, example log lines, the correlation chain, and (optionally)
the AI/deterministic explanation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..engine.normalize import normalize_message
from ..engine.severity import _WEIGHTS
from . import analysis


def _incident_out(i: models.Incident, baseline_rate: float = 0.0) -> schemas.IncidentOut:
    return schemas.IncidentOut(
        incident_id=i.incident_id,
        cluster_id=i.cluster_id,
        title=i.title,
        service=i.service,
        severity=i.severity,
        confidence=i.confidence,
        status=i.status,
        anomaly_score=i.anomaly_score,
        growth_pct=i.growth_pct,
        baseline_rate=baseline_rate,
        count=i.count,
        first_seen=i.first_seen,
        last_seen=i.last_seen,
        correlated_ids=list(i.correlated_ids or []),
    )


def _cluster_detail(c: models.Cluster) -> schemas.ClusterDetailOut:
    factors = []
    for name, weight in _WEIGHTS.items():
        value = float(c.severity_factors.get(name, 0.0)) if c.severity_factors else 0.0
        factors.append(schemas.SeverityFactor(
            name=name, value=value, weight=weight, contribution=value * weight,
        ))
    factors.sort(key=lambda f: f.contribution, reverse=True)

    buckets = [schemas.BucketOut(ts=datetime.fromisoformat(b[0]), count=b[1])
               for b in (c.buckets or [])]

    return schemas.ClusterDetailOut(
        cluster_id=c.cluster_id,
        template=c.template,
        normalized_example=normalize_message(c.example) if c.example else c.template,
        level=c.level,
        count=c.count,
        token_count=c.token_count,
        services=dict(c.services or {}),
        example_logs=list(c.examples or []),
        buckets=buckets,
        anomaly_score=c.anomaly_score,
        zscore=c.zscore,
        is_anomaly=c.is_anomaly,
        growth_pct=c.growth_pct,
        baseline_rate=c.baseline_rate,
        recent_count=c.recent_count,
        severity=c.severity,
        severity_score=c.severity_score,
        confidence=c.confidence,
        severity_factors=factors,
    )


def find_incident(db: Session, run_id: int, incident_id: str) -> Optional[models.Incident]:
    return db.scalars(
        select(models.Incident).where(
            models.Incident.run_id == run_id,
            models.Incident.incident_id == incident_id,
        )
    ).first()


def find_cluster(db: Session, run_id: int, cluster_id: str) -> Optional[models.Cluster]:
    return db.scalars(
        select(models.Cluster).where(
            models.Cluster.run_id == run_id,
            models.Cluster.cluster_id == cluster_id,
        )
    ).first()


def build_incident_detail(
    db: Session, run: models.Run, incident_id: str
) -> Optional[schemas.IncidentDetailOut]:
    incident = find_incident(db, run.id, incident_id)
    if incident is None:
        return None
    cluster = find_cluster(db, run.id, incident.cluster_id)
    if cluster is None:
        return None

    correlations = analysis.run_correlations(db, run.id)
    related_ids = set(incident.correlated_ids or [])
    chain = [
        schemas.CorrelationOut(
            upstream_id=c.upstream_id, downstream_id=c.downstream_id,
            kind=c.kind, detail=c.detail, lag_seconds=c.lag_seconds,
        )
        for c in correlations
        if c.upstream_id == incident_id or c.downstream_id == incident_id
    ]

    all_incidents = {i.incident_id: i for i in analysis.run_incidents(db, run.id)}
    clusters_by_id = {cc.cluster_id: cc for cc in analysis.run_clusters(db, run.id)}
    related = []
    for rid in related_ids:
        ri = all_incidents.get(rid)
        if ri:
            base = clusters_by_id.get(ri.cluster_id)
            related.append(_incident_out(ri, base.baseline_rate if base else 0.0))

    explanation = None
    if incident.explanation and incident.explanation_source:
        explanation = schemas.ExplanationOut(
            source=incident.explanation_source,
            summary=incident.explanation.get("summary", ""),
            root_cause=incident.explanation.get("root_cause", ""),
            suggested_fixes=incident.explanation.get("suggested_fixes", []),
        )

    return schemas.IncidentDetailOut(
        incident=_incident_out(incident, cluster.baseline_rate),
        cluster=_cluster_detail(cluster),
        correlations=chain,
        related_incidents=related,
        explanation=explanation,
    )
