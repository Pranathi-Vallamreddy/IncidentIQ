"""Shared data structures for the analysis engine.

These are plain dataclasses with no framework dependencies. The API layer maps
them onto ORM models / Pydantic DTOs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Canonical severity ordering, weakest -> strongest.
SEVERITY_ORDER = ["Low", "Medium", "High", "Critical"]

# Canonical log levels we recognise, mapped to a coarse rank used by scoring.
LEVEL_RANK = {
    "TRACE": 0,
    "DEBUG": 0,
    "INFO": 1,
    "NOTICE": 1,
    "WARN": 2,
    "WARNING": 2,
    "ERROR": 3,
    "ERR": 3,
    "CRITICAL": 4,
    "CRIT": 4,
    "FATAL": 4,
    "EMERGENCY": 4,
    "UNKNOWN": 1,
}


@dataclass
class ParsedEvent:
    """A single log line after parsing."""

    ts: datetime
    level: str
    service: Optional[str]
    message: str
    raw: str
    line_no: int = 0


@dataclass
class Template:
    """A mined log template (the pattern shared by a group of events)."""

    template_id: str  # e.g. "CLU-118"
    tokens: list[str]  # template tokens, variable positions are "<*>"
    token_count: int
    level: str
    count: int = 0
    example: str = ""
    examples: list[str] = field(default_factory=list)  # capped raw sample lines
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    services: dict[str, int] = field(default_factory=dict)

    @property
    def pattern(self) -> str:
        return " ".join(self.tokens)


@dataclass
class TimeBucket:
    bucket_ts: datetime
    count: int


@dataclass
class Cluster:
    """A template enriched with frequency + scoring signals."""

    cluster_id: str
    template: str
    tokens: list[str]
    token_count: int
    level: str
    count: int
    example: str
    examples: list[str]
    first_seen: datetime
    last_seen: datetime
    services: dict[str, int]
    buckets: list[TimeBucket] = field(default_factory=list)

    # frequency signals
    growth_pct: float = 0.0
    recent_count: int = 0
    baseline_rate: float = 0.0

    # anomaly signals
    anomaly_score: float = 0.0  # 0..1
    zscore: float = 0.0
    is_anomaly: bool = False
    peak_is_recent: bool = True  # is the largest spike in the recent tail?

    # severity signals
    severity: str = "Low"
    severity_score: float = 0.0  # 0..1
    confidence: float = 0.0  # 0..1
    severity_factors: dict[str, float] = field(default_factory=dict)

    @property
    def primary_service(self) -> Optional[str]:
        if not self.services:
            return None
        return max(self.services.items(), key=lambda kv: kv[1])[0]


@dataclass
class Correlation:
    """A directed link between two incidents (upstream -> downstream)."""

    upstream_id: str
    downstream_id: str
    kind: str  # "dependency" | "temporal"
    detail: str
    lag_seconds: float = 0.0


@dataclass
class Incident:
    """A cluster promoted to an actionable incident."""

    incident_id: str  # e.g. "INC-4821"
    cluster_id: str
    title: str
    service: Optional[str]
    severity: str
    confidence: float
    status: str  # Active | Investigating | Monitoring | Resolved
    anomaly_score: float
    growth_pct: float
    count: int
    first_seen: datetime
    last_seen: datetime
    correlated_ids: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Full output of one pipeline run."""

    source_name: str
    event_count: int
    parsed_count: int
    unparsed_count: int
    started_at: datetime
    finished_at: datetime
    window_start: datetime
    window_end: datetime
    clusters: list[Cluster] = field(default_factory=list)
    incidents: list[Incident] = field(default_factory=list)
    correlations: list[Correlation] = field(default_factory=list)
