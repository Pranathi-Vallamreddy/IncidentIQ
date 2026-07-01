"""Dashboard + analytics read endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..services import analysis
from ..services.dashboard import _run_out, build_analytics, build_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/runs/latest", response_model=Optional[schemas.RunOut])
def latest_run(db: Session = Depends(get_db)) -> Optional[schemas.RunOut]:
    """Lightweight current-run summary for the sidebar (avoids a full dashboard fetch)."""
    run = analysis.latest_run(db)
    return _run_out(run) if run else None


@router.get("/dashboard", response_model=schemas.DashboardOut)
def get_dashboard(
    run_id: Optional[int] = Query(default=None), db: Session = Depends(get_db)
) -> schemas.DashboardOut:
    run = analysis.get_run(db, run_id)
    return build_dashboard(db, run)


@router.get("/analytics", response_model=schemas.AnalyticsOut)
def get_analytics(
    run_id: Optional[int] = Query(default=None), db: Session = Depends(get_db)
) -> schemas.AnalyticsOut:
    run = analysis.get_run(db, run_id)
    return build_analytics(db, run)
