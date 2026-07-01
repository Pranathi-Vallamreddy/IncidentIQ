"""Detection settings (the only settings wired into the engine)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings as env_settings
from ..db import get_db
from ..services.settings import get_settings

router = APIRouter(tags=["settings"])


def _out(row) -> schemas.SettingsOut:
    return schemas.SettingsOut(
        anomaly_sensitivity=row.anomaly_sensitivity,
        auto_cluster=row.auto_cluster,
        ai_root_cause=row.ai_root_cause,
        page_on_critical=row.page_on_critical,
        ai_available=env_settings.ai_enabled,
    )


@router.get("/settings", response_model=schemas.SettingsOut)
def read_settings(db: Session = Depends(get_db)) -> schemas.SettingsOut:
    return _out(get_settings(db))


@router.put("/settings", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsIn, db: Session = Depends(get_db)) -> schemas.SettingsOut:
    row = get_settings(db)
    if payload.anomaly_sensitivity is not None:
        row.anomaly_sensitivity = max(0.0, min(1.0, payload.anomaly_sensitivity))
    if payload.auto_cluster is not None:
        row.auto_cluster = payload.auto_cluster
    if payload.ai_root_cause is not None:
        row.ai_root_cause = payload.ai_root_cause
    if payload.page_on_critical is not None:
        row.page_on_critical = payload.page_on_critical
    db.commit()
    db.refresh(row)
    return _out(row)
