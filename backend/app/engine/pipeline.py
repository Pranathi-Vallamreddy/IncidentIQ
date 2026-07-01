"""Pipeline orchestration.

Wires the engine stages end to end and returns a single deterministic
``AnalysisResult``:

    parse -> mine templates -> build clusters -> frequency
          -> anomaly -> severity -> incidents -> correlation

Deterministic: the same input + parameters always yields the same output.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable, Optional

from . import anomaly, clustering, correlation, frequency, incidents, severity
from .parser import LogParser
from .templates import TemplateMiner
from .types import AnalysisResult


def analyze(
    source_name: str,
    lines: Iterable[str],
    *,
    sensitivity: float = 0.6,
    sim_threshold: float = 0.5,
    base_time: Optional[datetime] = None,
) -> AnalysisResult:
    started = datetime.now(timezone.utc)

    # 1. Parse
    parser = LogParser(base_time=base_time)
    events = parser.parse(lines)
    parsed_count = sum(1 for e in events if e.level != "UNKNOWN")
    unparsed_count = len(events) - parsed_count

    # Analysis window from observed timestamps.
    if events:
        window_start = min(e.ts for e in events)
        window_end = max(e.ts for e in events)
    else:
        window_start = window_end = started

    # 2. Template mining + record per-cluster event times.
    miner = TemplateMiner(sim_threshold=sim_threshold)
    cluster_times: dict[str, list[datetime]] = defaultdict(list)
    for event in events:
        template = miner.add_event(event)
        cluster_times[template.template_id].append(event.ts)

    # 3-7. Cluster -> frequency -> anomaly -> severity.
    clusters = clustering.build_clusters(miner.get_templates())
    bucket_seconds = frequency.choose_bucket_seconds(
        (window_end - window_start).total_seconds()
    )
    frequency.compute(clusters, cluster_times, window_start, window_end, bucket_seconds)
    anomaly.score(clusters, sensitivity=sensitivity)
    severity.score(clusters)

    # 8. Incidents + 9. correlation.
    incident_list = incidents.form(clusters)
    correlations = correlation.correlate(incident_list)

    finished = datetime.now(timezone.utc)
    return AnalysisResult(
        source_name=source_name,
        event_count=len(events),
        parsed_count=parsed_count,
        unparsed_count=unparsed_count,
        started_at=started,
        finished_at=finished,
        window_start=window_start,
        window_end=window_end,
        clusters=clusters,
        incidents=incident_list,
        correlations=correlations,
    )


def analyze_text(source_name: str, text: str, **kwargs) -> AnalysisResult:
    return analyze(source_name, text.splitlines(), **kwargs)
