"""Aggregate a persisted run into the dashboard + analytics payloads.

Every number here is derived from the engine's stored output — no hard-coded
demo values.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from . import analysis

_SEV_RANK = {"Critical": 3, "High": 2, "Medium": 1, "Low": 0}
_ACTIVE = {"Active", "Investigating", "Monitoring"}


def _fmt_count(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def _fmt_minutes(seconds: float) -> str:
    minutes = seconds / 60.0
    if minutes >= 60:
        return f"{minutes / 60:.1f}h"
    return f"{max(minutes, 0):.0f}m"


def _run_out(run: models.Run) -> schemas.RunOut:
    return schemas.RunOut(
        id=run.id,
        source_name=run.source_name,
        event_count=run.event_count,
        parsed_count=run.parsed_count,
        unparsed_count=run.unparsed_count,
        cluster_count=run.cluster_count,
        incident_count=run.incident_count,
        window_start=run.window_start,
        window_end=run.window_end,
        created_at=run.created_at,
    )


def _previous_run(db: Session, run: models.Run) -> Optional[models.Run]:
    return db.scalars(
        select(models.Run)
        .where(models.Run.id < run.id)
        .order_by(models.Run.id.desc())
        .limit(1)
    ).first()


def _mttr_seconds(incidents: list[models.Incident]) -> float:
    resolved = [i for i in incidents if i.status == "Resolved"]
    pool = resolved or incidents
    if not pool:
        return 0.0
    spans = [(i.last_seen - i.first_seen).total_seconds() for i in pool]
    return sum(spans) / len(spans)


def _kpis(db: Session, run: models.Run,
          clusters: list[models.Cluster],
          incidents: list[models.Incident]) -> list[schemas.KpiOut]:
    active = [i for i in incidents if i.status in _ACTIVE]
    critical = [i for i in incidents if i.severity == "Critical"]
    anomalies = [c for c in clusters if c.is_anomaly]
    mttr = _mttr_seconds(incidents)

    prev = _previous_run(db, run)
    ev_delta = None
    if prev and prev.event_count:
        ev_delta = (run.event_count - prev.event_count) / prev.event_count * 100.0

    services = {i.service for i in active if i.service}
    return [
        schemas.KpiOut(key="events", label="Total log events",
                       value=_fmt_count(run.event_count), raw=run.event_count,
                       delta_pct=ev_delta, hint="analyzed this run"),
        schemas.KpiOut(key="active", label="Active incidents",
                       value=str(len(active)), raw=len(active),
                       hint=f"across {len(services)} services"),
        schemas.KpiOut(key="critical", label="Critical incidents",
                       value=str(len(critical)), raw=len(critical),
                       hint="need attention"),
        schemas.KpiOut(key="anomalies", label="Anomaly clusters",
                       value=str(len(anomalies)), raw=len(anomalies),
                       hint="detected"),
        schemas.KpiOut(key="mttr", label="Mean incident duration",
                       value=_fmt_minutes(mttr), raw=mttr,
                       hint="first → last seen"),
    ]


def _timeline(run: models.Run,
              clusters: list[models.Cluster],
              incidents: list[models.Incident]) -> list[schemas.TimelinePoint]:
    by_id = {c.cluster_id: c for c in clusters}
    sev_by_cluster = {i.cluster_id: i.severity for i in incidents}

    # Build axis from the first incident cluster that has buckets.
    axis: list[str] = []
    for inc in incidents:
        c = by_id.get(inc.cluster_id)
        if c and c.buckets:
            axis = [b[0] for b in c.buckets]
            break
    if not axis:
        return []

    points = [{"ts": ts, "Critical": 0, "High": 0, "Medium": 0, "Low": 0} for ts in axis]
    for inc in incidents:
        c = by_id.get(inc.cluster_id)
        if not c or not c.buckets:
            continue
        sev = sev_by_cluster.get(inc.cluster_id, "Low")
        for idx, (_, count) in enumerate(c.buckets):
            if idx < len(points):
                points[idx][sev] += count

    return [schemas.TimelinePoint(ts=datetime.fromisoformat(p["ts"]),
                                  Critical=p["Critical"], High=p["High"],
                                  Medium=p["Medium"], Low=p["Low"]) for p in points]


def _service_health(incidents: list[models.Incident],
                    clusters: list[models.Cluster]) -> tuple[int, str, list[schemas.ServiceHealth]]:
    all_services = {c.services and max(c.services, key=c.services.get) for c in clusters}
    all_services = {s for s in all_services if s}
    for i in incidents:
        if i.service:
            all_services.add(i.service)

    status_by_service: dict[str, str] = {s: "Healthy" for s in all_services}
    count_by_service: dict[str, int] = {s: 0 for s in all_services}
    for i in incidents:
        if not i.service or i.status not in _ACTIVE:
            continue
        count_by_service[i.service] = count_by_service.get(i.service, 0) + 1
        rank = {"Critical": "Critical", "High": "Degraded",
                "Medium": "Degraded", "Low": "Healthy"}[i.severity]
        current = status_by_service.get(i.service, "Healthy")
        order = {"Healthy": 0, "Degraded": 1, "Critical": 2}
        if order[rank] > order[current]:
            status_by_service[i.service] = rank

    penalty = sum(12 if s == "Critical" else 6 if s == "Degraded" else 0
                  for s in status_by_service.values())
    score = max(0, min(100, 100 - penalty))
    n_critical = sum(1 for s in status_by_service.values() if s == "Critical")
    n_degraded = sum(1 for s in status_by_service.values() if s == "Degraded")
    if n_critical:
        summary = f"Degraded — {n_critical} critical service{'s' if n_critical != 1 else ''}"
    elif n_degraded:
        summary = f"Degraded — {n_degraded} service{'s' if n_degraded != 1 else ''} at risk"
    else:
        summary = "All systems operational"

    health = [schemas.ServiceHealth(service=s, status=st, incidents=count_by_service.get(s, 0))
              for s, st in sorted(status_by_service.items(),
                                  key=lambda kv: (-{"Critical": 2, "Degraded": 1, "Healthy": 0}[kv[1]], kv[0]))]
    return score, summary, health


def _top_clusters(clusters: list[models.Cluster],
                  incidents: list[models.Incident]) -> list[schemas.TopClusterOut]:
    title_by_cluster = {i.cluster_id: i.title for i in incidents}
    incident_by_cluster = {i.cluster_id: i.incident_id for i in incidents}
    ranked = sorted(clusters, key=lambda c: (c.anomaly_score, c.growth_pct, c.count), reverse=True)
    out = []
    for c in ranked[:5]:
        primary = max(c.services, key=c.services.get) if c.services else None
        out.append(schemas.TopClusterOut(
            cluster_id=c.cluster_id,
            incident_id=incident_by_cluster.get(c.cluster_id),
            title=title_by_cluster.get(c.cluster_id, c.example[:60] or c.template[:60]),
            service=primary,
            severity=c.severity,
            count=c.count,
            growth_pct=c.growth_pct,
            baseline_rate=c.baseline_rate,
        ))
    return out


def _pipeline(run: models.Run, clusters: list[models.Cluster],
              incidents: list[models.Incident],
              correlations: list[models.Correlation]) -> schemas.PipelineStats:
    return schemas.PipelineStats(
        events=run.event_count,
        parsed=run.parsed_count,
        unparsed=run.unparsed_count,
        clusters=len(clusters),
        anomalies=sum(1 for c in clusters if c.is_anomaly),
        incidents=len(incidents),
        correlations=len(correlations),
    )


def _insights(incidents: list[models.Incident],
              correlations: list[models.Correlation]) -> list[schemas.InsightOut]:
    by_id = {i.incident_id: i for i in incidents}
    insights: list[schemas.InsightOut] = []
    seen_downstream: set[str] = set()
    # Prefer the most severe upstream when a downstream has several causes.
    dep = sorted(
        [c for c in correlations if c.kind == "dependency"],
        key=lambda c: _SEV_RANK.get(
            by_id[c.upstream_id].severity if c.upstream_id in by_id else "Low", 0),
        reverse=True,
    )
    for corr in dep:
        up = by_id.get(corr.upstream_id)
        down = by_id.get(corr.downstream_id)
        if not up or not down or down.incident_id in seen_downstream:
            continue
        seen_downstream.add(down.incident_id)
        insights.append(schemas.InsightOut(
            kind="Correlation",
            title="Cascading failure detected",
            detail=(f"{down.incident_id} ({down.service}) is downstream of "
                    f"{up.incident_id} ({up.service}). {corr.detail}"),
            incident_id=up.incident_id,  # link to the root cause
        ))
    # A spike highlight for the strongest active anomaly.
    active_anoms = sorted(
        [i for i in incidents if i.status in _ACTIVE and i.anomaly_score >= 0.7],
        key=lambda i: i.anomaly_score, reverse=True)
    if active_anoms:
        top = active_anoms[0]
        insights.append(schemas.InsightOut(
            kind="Anomaly",
            title="Volume spike detected",
            detail=(f"{top.incident_id} on {top.service} is spiking "
                    f"({top.count} events, {top.severity.lower()} severity)."),
            incident_id=top.incident_id,
        ))
    return insights[:4]


def build_dashboard(db: Session, run: Optional[models.Run]) -> schemas.DashboardOut:
    if run is None:
        return schemas.DashboardOut(
            run=None, kpis=[], timeline=[], health_score=100,
            health_summary="No data yet — upload logs to begin.",
            service_health=[], top_clusters=[], severity_distribution={},
            insights=[],
        )
    clusters = analysis.run_clusters(db, run.id)
    incidents = analysis.run_incidents(db, run.id)
    correlations = analysis.run_correlations(db, run.id)

    score, summary, health = _service_health(incidents, clusters)
    dist = {s: 0 for s in ("Critical", "High", "Medium", "Low")}
    for i in incidents:
        dist[i.severity] = dist.get(i.severity, 0) + 1

    return schemas.DashboardOut(
        run=_run_out(run),
        kpis=_kpis(db, run, clusters, incidents),
        timeline=_timeline(run, clusters, incidents),
        health_score=score,
        health_summary=summary,
        service_health=health,
        top_clusters=_top_clusters(clusters, incidents),
        severity_distribution=dist,
        insights=_insights(incidents, correlations),
        pipeline=_pipeline(run, clusters, incidents, correlations),
    )


def build_analytics(db: Session, run: Optional[models.Run]) -> schemas.AnalyticsOut:
    if run is None:
        return schemas.AnalyticsOut(run=None, trends=[], cluster_frequency=[], timeline=[])
    clusters = analysis.run_clusters(db, run.id)
    incidents = analysis.run_incidents(db, run.id)

    # Error/warning trends: sum error- and warn-level cluster buckets per bucket.
    axis: list[str] = []
    for c in clusters:
        if c.buckets:
            axis = [b[0] for b in c.buckets]
            break
    trends: list[schemas.TrendPoint] = []
    if axis:
        err = [0] * len(axis)
        warn = [0] * len(axis)
        for c in clusters:
            target = None
            if c.level in ("ERROR", "ERR", "CRITICAL", "CRIT", "FATAL", "EMERGENCY"):
                target = err
            elif c.level in ("WARN", "WARNING", "NOTICE"):
                target = warn
            if target is None:
                continue
            for idx, (_, count) in enumerate(c.buckets):
                if idx < len(target):
                    target[idx] += count
        trends = [schemas.TrendPoint(ts=datetime.fromisoformat(axis[i]),
                                     errors=err[i], warnings=warn[i])
                  for i in range(len(axis))]

    freq = sorted(clusters, key=lambda c: c.count, reverse=True)[:8]
    cluster_frequency = [schemas.FreqBar(cluster_id=c.cluster_id, count=c.count) for c in freq]

    return schemas.AnalyticsOut(
        run=_run_out(run),
        trends=trends,
        cluster_frequency=cluster_frequency,
        timeline=_timeline(run, clusters, incidents),
    )
