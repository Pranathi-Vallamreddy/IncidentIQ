"""Singleton AppSettings access."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models
from ..config import settings as env_settings


def get_settings(db: Session) -> models.AppSettings:
    row = db.get(models.AppSettings, 1)
    if row is None:
        row = models.AppSettings(id=1, anomaly_sensitivity=env_settings.default_sensitivity)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row
