"""Anomaly detection: does a cluster spike anywhere in its history?

Rather than only comparing the recent tail to a baseline, we scan the whole
bucket series for the single largest deviation (the *peak*). This lets the engine
surface incidents that already resolved (a burst that happened mid-window and
stopped) as well as active ones, and tag which is which.

Robustness choices:
  * baseline centre = median (resistant to the very spike we're hunting),
  * scale = max(MAD-based sigma, sqrt(median), 1) — a Poisson-style floor so a
    steady low-variance baseline can't manufacture huge z-scores,
  * a flag requires statistical (z >= threshold), material (enough events at the
    peak) and relative (peak clearly above baseline) agreement.

Threshold comes from the user's anomaly-sensitivity setting.
"""

from __future__ import annotations

import math
import statistics

from .types import Cluster

_EPS = 1e-9
_Z_CLAMP = 10.0
_MIN_PEAK_EVENTS = 4
_MAD_TO_SIGMA = 1.4826  # scale factor making MAD a consistent sigma estimator


def _threshold_from_sensitivity(sensitivity: float) -> float:
    sensitivity = min(max(sensitivity, 0.0), 1.0)
    return 3.5 - sensitivity * 2.5  # sensitivity 0 -> 3.5, 1 -> 1.0


def _robust_scale(counts: list[int], center: float) -> float:
    deviations = [abs(c - center) for c in counts]
    mad = statistics.median(deviations) if deviations else 0.0
    return max(_MAD_TO_SIGMA * mad, math.sqrt(max(center, 1.0)), 1.0)


def score(clusters: list[Cluster], sensitivity: float = 0.6) -> None:
    threshold = _threshold_from_sensitivity(sensitivity)
    scale_factor = max(1.0, threshold / 2.0)

    for cluster in clusters:
        counts = [b.count for b in cluster.buckets]
        n = len(counts)
        if n == 0:
            continue
        recent_span = max(1, n // 6)

        center = statistics.median(counts)
        scale = _robust_scale(counts, center)

        # Because we scan n buckets for the single largest one, the expected max
        # of noise grows like sqrt(2 ln n). Raise the bar by that much so random
        # Poisson lumpiness in normal traffic isn't mistaken for a spike.
        scan_correction = math.sqrt(2.0 * math.log(max(n, 2)))
        effective_threshold = threshold + scan_correction

        # Per-bucket deviation; the peak bucket is the incident's ignition point.
        peak_idx = max(range(n), key=lambda i: counts[i])
        peak_count = counts[peak_idx]
        z = min(_Z_CLAMP, (peak_count - center) / scale)
        cluster.zscore = z

        cluster.anomaly_score = 1.0 / (1.0 + math.exp(-(z - effective_threshold) / scale_factor))
        cluster.peak_is_recent = peak_idx >= n - recent_span

        relative_jump = center < _EPS or peak_count >= center * 1.5
        cluster.is_anomaly = (
            z >= effective_threshold
            and peak_count >= _MIN_PEAK_EVENTS
            and relative_jump
        )
