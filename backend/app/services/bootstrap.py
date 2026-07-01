"""Startup seeding.

Render's free tier has an ephemeral filesystem, so the SQLite DB is empty after
every deploy/cold start. To keep the deployed demo populated, we load the marquee
sample through the real engine on startup *only if no run exists yet*. Uploaded
runs are never overwritten, and this never fabricates analysis — it just runs the
same pipeline the upload endpoint would.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..data import generate_samples
from . import analysis
from .settings import get_settings

_SEED_SAMPLE = "ecommerce-cascade.log"


def seed_if_empty(db: Session) -> None:
    existing = db.scalar(select(func.count()).select_from(models.Run))
    if existing:
        return

    path = generate_samples.SAMPLES_DIR / _SEED_SAMPLE
    if not path.exists():
        generate_samples.generate()
    if not path.exists():
        return  # nothing to seed with; app still runs, just empty

    sensitivity = get_settings(db).anomaly_sensitivity
    text = path.read_text(encoding="utf-8", errors="replace")
    analysis.analyze_and_store(db, _SEED_SAMPLE, text.splitlines(), sensitivity)
