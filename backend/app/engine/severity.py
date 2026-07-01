"""Severity engine: score every cluster and assign a severity + confidence.

Severity is a transparent weighted blend of six normalised factors, so the
Incident Detail page can show *why* something is Critical rather than a black-box
number:

    anomaly (0.30) + level (0.25) + service criticality (0.15)
    + volume (0.15) + growth (0.10) + breadth (0.05)

Confidence is a separate signal describing how much evidence backs the call
(sample size + anomaly strength + log level), which is what the UI renders as the
74–96% bars.
"""

from __future__ import annotations

import math

from .types import LEVEL_RANK, Cluster

# Business criticality per service. Unknown services default to 0.5.
SERVICE_CRITICALITY: dict[str, float] = {
    "payments-api": 1.0,
    "checkout-gateway": 1.0,
    "auth-service": 0.9,
    "orders-api": 0.85,
    "webhooks": 0.6,
    "analytics-api": 0.5,
    "media-worker": 0.5,
    "edge-cache": 0.45,
    "notifications": 0.4,
}

_WEIGHTS = {
    "anomaly": 0.30,
    "level": 0.25,
    "criticality": 0.15,
    "volume": 0.15,
    "growth": 0.10,
    "breadth": 0.05,
}


def service_criticality(service: str | None) -> float:
    if not service:
        return 0.5
    return SERVICE_CRITICALITY.get(service, 0.5)


def _bucket(score: float) -> str:
    if score >= 0.75:
        return "Critical"
    if score >= 0.55:
        return "High"
    if score >= 0.35:
        return "Medium"
    return "Low"


def score(clusters: list[Cluster]) -> None:
    max_count = max((c.count for c in clusters), default=1) or 1
    log_max = math.log10(max_count + 1)

    for cluster in clusters:
        level_factor = LEVEL_RANK.get(cluster.level, 1) / 4.0
        anomaly_factor = cluster.anomaly_score
        crit_factor = service_criticality(cluster.primary_service)
        volume_factor = math.log10(cluster.count + 1) / (log_max + 1e-9)
        growth_factor = min(max(cluster.growth_pct / 300.0, 0.0), 1.0)
        breadth_factor = min(max((len(cluster.services) - 1) / 3.0, 0.0), 1.0)

        factors = {
            "anomaly": anomaly_factor,
            "level": level_factor,
            "criticality": crit_factor,
            "volume": volume_factor,
            "growth": growth_factor,
            "breadth": breadth_factor,
        }
        severity_score = sum(_WEIGHTS[k] * v for k, v in factors.items())

        cluster.severity_score = severity_score
        cluster.severity = _bucket(severity_score)
        cluster.severity_factors = factors

        # Confidence: evidence behind the call (not the same as severity).
        sample_conf = min(math.log10(cluster.count + 1) / math.log10(500), 1.0)
        base = 0.45 * sample_conf + 0.35 * anomaly_factor + 0.20 * level_factor
        cluster.confidence = min(0.99, max(0.5, 0.60 + 0.38 * base))
