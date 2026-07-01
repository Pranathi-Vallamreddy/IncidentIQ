"""Frequency analysis: per-cluster time series, rates, and growth.

For each cluster we bucket its events into fixed windows across the analysis
period, then compare a *recent* tail of the window against the *baseline* body.
The recent-vs-baseline rate ratio produces the "+214%" style growth number and
feeds anomaly detection.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .types import Cluster, TimeBucket

_EPS = 1e-9


def choose_bucket_seconds(span_seconds: float) -> int:
    """Pick a bucket size that yields ~24-40 buckets for stable statistics."""
    minutes = span_seconds / 60.0
    if minutes <= 30:
        return 60          # <=30m  -> 1 min
    if minutes <= 3 * 60:
        return 5 * 60      # <=3h   -> 5 min   (2h -> 24 buckets)
    if minutes <= 24 * 60:
        return 60 * 60     # <=1d   -> 1 hour  (24 buckets)
    if minutes <= 7 * 24 * 60:
        return 6 * 60 * 60  # <=1w  -> 6 hours
    return 24 * 60 * 60    # else   -> 1 day


def _bucket_index(ts: datetime, start: datetime, bucket_seconds: int) -> int:
    return int((ts - start).total_seconds() // bucket_seconds)


def compute(
    clusters: list[Cluster],
    cluster_times: dict[str, list[datetime]],
    window_start: datetime,
    window_end: datetime,
    bucket_seconds: int,
) -> None:
    span = max((window_end - window_start).total_seconds(), bucket_seconds)
    n_buckets = max(1, int(span // bucket_seconds) + 1)
    recent_span = max(1, n_buckets // 6)

    for cluster in clusters:
        times = cluster_times.get(cluster.cluster_id, [])
        counts = [0] * n_buckets
        for ts in times:
            idx = _bucket_index(ts, window_start, bucket_seconds)
            idx = min(max(idx, 0), n_buckets - 1)
            counts[idx] += 1

        cluster.buckets = [
            TimeBucket(
                bucket_ts=window_start + timedelta(seconds=i * bucket_seconds),
                count=c,
            )
            for i, c in enumerate(counts)
        ]

        recent = counts[-recent_span:]
        baseline = counts[:-recent_span] if n_buckets > recent_span else []

        recent_rate = sum(recent) / len(recent)
        baseline_rate = (sum(baseline) / len(baseline)) if baseline else recent_rate

        cluster.recent_count = sum(recent)
        cluster.baseline_rate = baseline_rate
        raw_growth = ((recent_rate - baseline_rate) / (baseline_rate + _EPS)) * 100.0
        # Clamp: a near-zero baseline makes the ratio blow up; cap it at a
        # display-sane ceiling (an emerging cluster is "new", not +1e12%).
        cluster.growth_pct = max(-100.0, min(9999.0, raw_growth))
