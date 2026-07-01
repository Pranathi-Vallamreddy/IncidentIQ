"""Incident formation: promote notable clusters to incidents.

A cluster becomes an incident when it is anomalous or reaches at least Medium
severity — i.e. something an engineer would actually want on the board. Titles
are derived from the cluster template, and status is inferred from recency and
trend.
"""

from __future__ import annotations

from datetime import datetime

from .types import LEVEL_RANK, Cluster, Incident

# Incident numbering base, purely cosmetic so ids read like INC-48xx.
_INC_BASE = 4800

_STOPWORDS = {"<*>", "<num>", "<str>", "<id>", "<hex>", "<dur>", "<ip>",
              "<ts>", "<uuid>", "<url>", "<path>", "<pct>", "<size>",
              "<email>", "<empty>"}


def _title_from(cluster: Cluster) -> str:
    """Human-readable title from the example message, capped to a clause."""
    source = cluster.example or cluster.template
    words = source.split()
    kept: list[str] = []
    for w in words:
        if w.lower() in _STOPWORDS:
            continue
        kept.append(w)
        if len(kept) >= 9:
            break
    title = " ".join(kept).strip(" :-").strip()
    if not title:
        title = cluster.template
    return title[:80].rstrip()


def _status(cluster: Cluster) -> str:
    # The spike already passed and activity has died down -> resolved.
    if cluster.recent_count == 0 or not cluster.peak_is_recent:
        return "Resolved"
    if cluster.severity == "Critical":
        return "Active"
    if cluster.severity == "High":
        return "Investigating"
    return "Monitoring"


def is_incident(cluster: Cluster) -> bool:
    # A genuine anomaly is always worth surfacing, whatever the level.
    if cluster.is_anomaly:
        return True
    # Otherwise it must be error-ish (WARN+) and reach at least Medium severity;
    # high-volume INFO/DEBUG traffic is normal operation, not an incident.
    error_ish = LEVEL_RANK.get(cluster.level, 1) >= 2
    return error_ish and cluster.severity_score >= 0.35


def form(clusters: list[Cluster]) -> list[Incident]:
    candidates = [c for c in clusters if is_incident(c)]
    # Rank by severity, then anomaly, then volume — highest first.
    candidates.sort(
        key=lambda c: (c.severity_score, c.anomaly_score, c.count),
        reverse=True,
    )

    incidents: list[Incident] = []
    for i, cluster in enumerate(candidates):
        incidents.append(
            Incident(
                incident_id=f"INC-{_INC_BASE + len(candidates) - i}",
                cluster_id=cluster.cluster_id,
                title=_title_from(cluster),
                service=cluster.primary_service,
                severity=cluster.severity,
                confidence=cluster.confidence,
                status=_status(cluster),
                anomaly_score=cluster.anomaly_score,
                growth_pct=cluster.growth_pct,
                count=cluster.count,
                first_seen=cluster.first_seen,
                last_seen=cluster.last_seen,
            )
        )
    return incidents
