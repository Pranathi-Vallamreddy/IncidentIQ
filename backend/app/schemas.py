"""Pydantic DTOs — the HTTP contract consumed by the frontend."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RunOut(BaseModel):
    id: int
    source_name: str
    event_count: int
    parsed_count: int
    unparsed_count: int
    cluster_count: int
    incident_count: int
    window_start: datetime
    window_end: datetime
    created_at: datetime


class SampleOut(BaseModel):
    name: str
    size_kb: float
    fmt: str
    description: str


class IncidentOut(BaseModel):
    incident_id: str
    cluster_id: str
    title: str
    service: Optional[str]
    severity: str
    confidence: float
    status: str
    anomaly_score: float
    growth_pct: float
    baseline_rate: float
    count: int
    first_seen: datetime
    last_seen: datetime
    correlated_ids: list[str]


class BucketOut(BaseModel):
    ts: datetime
    count: int


class SeverityFactor(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float


class ClusterDetailOut(BaseModel):
    cluster_id: str
    template: str
    normalized_example: str
    level: str
    count: int
    token_count: int
    services: dict[str, int]
    example_logs: list[str]
    buckets: list[BucketOut]
    anomaly_score: float
    zscore: float
    is_anomaly: bool
    growth_pct: float
    baseline_rate: float
    recent_count: int
    severity: str
    severity_score: float
    confidence: float
    severity_factors: list[SeverityFactor]


class CorrelationOut(BaseModel):
    upstream_id: str
    downstream_id: str
    kind: str
    detail: str
    lag_seconds: float


class ExplanationOut(BaseModel):
    source: str  # "gemini" | "deterministic"
    summary: str
    root_cause: str
    suggested_fixes: list[str]


class IncidentDetailOut(BaseModel):
    incident: IncidentOut
    cluster: ClusterDetailOut
    correlations: list[CorrelationOut]
    related_incidents: list[IncidentOut]
    explanation: Optional[ExplanationOut]


class KpiOut(BaseModel):
    key: str
    label: str
    value: str
    raw: float
    delta_pct: Optional[float] = None
    hint: str = ""


class TimelinePoint(BaseModel):
    ts: datetime
    Critical: int = 0
    High: int = 0
    Medium: int = 0
    Low: int = 0


class ServiceHealth(BaseModel):
    service: str
    status: str  # Critical | Degraded | Healthy
    incidents: int


class TopClusterOut(BaseModel):
    cluster_id: str
    incident_id: Optional[str] = None
    title: str
    service: Optional[str]
    severity: str
    count: int
    growth_pct: float
    baseline_rate: float


class InsightOut(BaseModel):
    kind: str
    title: str
    detail: str
    incident_id: Optional[str] = None


class PipelineStats(BaseModel):
    events: int
    parsed: int
    unparsed: int
    clusters: int
    anomalies: int
    incidents: int
    correlations: int


class DashboardOut(BaseModel):
    run: Optional[RunOut]
    kpis: list[KpiOut]
    timeline: list[TimelinePoint]
    health_score: int
    health_summary: str
    service_health: list[ServiceHealth]
    top_clusters: list[TopClusterOut]
    severity_distribution: dict[str, int]
    insights: list[InsightOut]
    pipeline: Optional[PipelineStats] = None


class TrendPoint(BaseModel):
    ts: datetime
    errors: int
    warnings: int


class FreqBar(BaseModel):
    cluster_id: str
    count: int


class AnalyticsOut(BaseModel):
    run: Optional[RunOut]
    trends: list[TrendPoint]
    cluster_frequency: list[FreqBar]
    timeline: list[TimelinePoint]


