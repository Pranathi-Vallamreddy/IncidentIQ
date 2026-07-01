"""Run the engine and persist its result; fetch runs back out."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..engine import pipeline
from ..engine.types import AnalysisResult, Cluster


def _serialize_buckets(cluster: Cluster) -> list[list]:
    return [[b.bucket_ts.isoformat(), b.count] for b in cluster.buckets]


def persist_result(db: Session, result: AnalysisResult, sensitivity: float) -> models.Run:
    run = models.Run(
        source_name=result.source_name,
        event_count=result.event_count,
        parsed_count=result.parsed_count,
        unparsed_count=result.unparsed_count,
        cluster_count=len(result.clusters),
        incident_count=len(result.incidents),
        window_start=result.window_start.replace(tzinfo=None),
        window_end=result.window_end.replace(tzinfo=None),
        bucket_seconds=(
            int((result.clusters[0].buckets[1].bucket_ts
                 - result.clusters[0].buckets[0].bucket_ts).total_seconds())
            if result.clusters and len(result.clusters[0].buckets) > 1 else 300
        ),
        sensitivity=sensitivity,
    )
    db.add(run)
    db.flush()  # assign run.id

    for c in result.clusters:
        db.add(models.Cluster(
            run_id=run.id,
            cluster_id=c.cluster_id,
            template=c.template,
            token_count=c.token_count,
            level=c.level,
            count=c.count,
            example=c.example,
            examples=list(c.examples),
            first_seen=c.first_seen.replace(tzinfo=None),
            last_seen=c.last_seen.replace(tzinfo=None),
            services=dict(c.services),
            buckets=_serialize_buckets(c),
            growth_pct=c.growth_pct,
            baseline_rate=c.baseline_rate,
            recent_count=c.recent_count,
            anomaly_score=c.anomaly_score,
            zscore=c.zscore,
            is_anomaly=c.is_anomaly,
            severity=c.severity,
            severity_score=c.severity_score,
            confidence=c.confidence,
            severity_factors=dict(c.severity_factors),
        ))

    for i in result.incidents:
        db.add(models.Incident(
            run_id=run.id,
            incident_id=i.incident_id,
            cluster_id=i.cluster_id,
            title=i.title,
            service=i.service,
            severity=i.severity,
            confidence=i.confidence,
            status=i.status,
            anomaly_score=i.anomaly_score,
            growth_pct=i.growth_pct,
            count=i.count,
            first_seen=i.first_seen.replace(tzinfo=None),
            last_seen=i.last_seen.replace(tzinfo=None),
            correlated_ids=list(i.correlated_ids),
        ))

    for c in result.correlations:
        db.add(models.Correlation(
            run_id=run.id,
            upstream_id=c.upstream_id,
            downstream_id=c.downstream_id,
            kind=c.kind,
            detail=c.detail,
            lag_seconds=c.lag_seconds,
        ))

    db.commit()
    db.refresh(run)
    return run


def analyze_and_store(
    db: Session,
    source_name: str,
    lines: Iterable[str],
    sensitivity: float,
) -> models.Run:
    result = pipeline.analyze(source_name, lines, sensitivity=sensitivity)
    return persist_result(db, result, sensitivity)


def latest_run(db: Session) -> Optional[models.Run]:
    return db.scalars(
        select(models.Run).order_by(models.Run.created_at.desc()).limit(1)
    ).first()


def get_run(db: Session, run_id: Optional[int]) -> Optional[models.Run]:
    if run_id is None:
        return latest_run(db)
    return db.get(models.Run, run_id)


def run_clusters(db: Session, run_id: int) -> list[models.Cluster]:
    return list(db.scalars(
        select(models.Cluster).where(models.Cluster.run_id == run_id)
    ))


def run_incidents(db: Session, run_id: int) -> list[models.Incident]:
    return list(db.scalars(
        select(models.Incident).where(models.Incident.run_id == run_id)
    ))


def run_correlations(db: Session, run_id: int) -> list[models.Correlation]:
    return list(db.scalars(
        select(models.Correlation).where(models.Correlation.run_id == run_id)
    ))
