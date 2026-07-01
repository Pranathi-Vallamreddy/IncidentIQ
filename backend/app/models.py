"""ORM models. One analysis run owns its clusters, incidents and correlations."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(200))
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    parsed_count: Mapped[int] = mapped_column(Integer, default=0)
    unparsed_count: Mapped[int] = mapped_column(Integer, default=0)
    cluster_count: Mapped[int] = mapped_column(Integer, default=0)
    incident_count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime)
    window_end: Mapped[datetime] = mapped_column(DateTime)
    bucket_seconds: Mapped[int] = mapped_column(Integer, default=300)
    sensitivity: Mapped[float] = mapped_column(Float, default=0.6)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    clusters: Mapped[list["Cluster"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    correlations: Mapped[list["Correlation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    cluster_id: Mapped[str] = mapped_column(String(20), index=True)
    template: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(12))
    count: Mapped[int] = mapped_column(Integer)
    example: Mapped[str] = mapped_column(Text)
    examples: Mapped[list] = mapped_column(JSON, default=list)
    first_seen: Mapped[datetime] = mapped_column(DateTime)
    last_seen: Mapped[datetime] = mapped_column(DateTime)
    services: Mapped[dict] = mapped_column(JSON, default=dict)
    buckets: Mapped[list] = mapped_column(JSON, default=list)  # [[iso, count], ...]

    growth_pct: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_rate: Mapped[float] = mapped_column(Float, default=0.0)
    recent_count: Mapped[int] = mapped_column(Integer, default=0)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    zscore: Mapped[float] = mapped_column(Float, default=0.0)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)

    severity: Mapped[str] = mapped_column(String(12), default="Low")
    severity_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    severity_factors: Mapped[dict] = mapped_column(JSON, default=dict)

    run: Mapped["Run"] = relationship(back_populates="clusters")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    incident_id: Mapped[str] = mapped_column(String(20), index=True)
    cluster_id: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(Text)
    service: Mapped[str | None] = mapped_column(String(80), nullable=True)
    severity: Mapped[str] = mapped_column(String(12))
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))
    anomaly_score: Mapped[float] = mapped_column(Float)
    growth_pct: Mapped[float] = mapped_column(Float)
    count: Mapped[int] = mapped_column(Integer)
    first_seen: Mapped[datetime] = mapped_column(DateTime)
    last_seen: Mapped[datetime] = mapped_column(DateTime)
    correlated_ids: Mapped[list] = mapped_column(JSON, default=list)

    # AI / deterministic explanation, filled on demand.
    explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explanation_source: Mapped[str | None] = mapped_column(String(20), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="incidents")


class Correlation(Base):
    __tablename__ = "correlations"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    upstream_id: Mapped[str] = mapped_column(String(20))
    downstream_id: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20))
    detail: Mapped[str] = mapped_column(Text)
    lag_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    run: Mapped["Run"] = relationship(back_populates="correlations")


class AppSettings(Base):
    """Singleton config row (id always 1).

    Only settings that actually change engine behaviour are stored here:
    `anomaly_sensitivity` feeds the anomaly detector and `ai_root_cause` gates
    the Gemini explainer.
    """

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    anomaly_sensitivity: Mapped[float] = mapped_column(Float, default=0.6)
    ai_root_cause: Mapped[bool] = mapped_column(Boolean, default=True)
