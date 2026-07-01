"""Log ingestion: list/load bundled samples and upload custom log files."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..services import analysis
from ..services.settings import get_settings

router = APIRouter(tags=["logs"])

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"

_SAMPLE_META = {
    "ecommerce-cascade.log": (
        "text",
        "E-commerce outage: DB connection-pool exhaustion cascading into checkout "
        "5xx, plus auth latency, a media-worker memory leak, and resolved "
        "analytics/CDN incidents.",
    ),
    "platform-microservices.ndjson": (
        "ndjson",
        "Structured NDJSON logs from a microservices platform featuring an auth "
        "latency spike and a media-worker memory leak.",
    ),
    "payments-postmortem.log": (
        "text",
        "Focused payments outage: fatal DB pool exhaustion cascading into checkout "
        "failures.",
    ),
}

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.get("/samples", response_model=list[schemas.SampleOut])
def list_samples() -> list[schemas.SampleOut]:
    out: list[schemas.SampleOut] = []
    for name, (fmt, desc) in _SAMPLE_META.items():
        path = SAMPLES_DIR / name
        size_kb = round(path.stat().st_size / 1024, 1) if path.exists() else 0.0
        out.append(schemas.SampleOut(name=name, size_kb=size_kb, fmt=fmt, description=desc))
    return out


@router.post("/samples/{name}/load", response_model=schemas.RunOut)
def load_sample(name: str, db: Session = Depends(get_db)) -> schemas.RunOut:
    if name not in _SAMPLE_META:
        raise HTTPException(status_code=404, detail="Unknown sample")
    path = SAMPLES_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sample file missing; run generate_samples")

    sensitivity = get_settings(db).anomaly_sensitivity
    text = path.read_text(encoding="utf-8", errors="replace")
    run = analysis.analyze_and_store(db, name, text.splitlines(), sensitivity)
    return _run_out(run)


@router.post("/logs/upload", response_model=schemas.RunOut)
async def upload_logs(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> schemas.RunOut:
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 25 MB)")
    text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty file")

    sensitivity = get_settings(db).anomaly_sensitivity
    run = analysis.analyze_and_store(db, file.filename or "upload.log",
                                     text.splitlines(), sensitivity)
    return _run_out(run)


def _run_out(run) -> schemas.RunOut:
    return schemas.RunOut(
        id=run.id, source_name=run.source_name, event_count=run.event_count,
        parsed_count=run.parsed_count, unparsed_count=run.unparsed_count,
        cluster_count=run.cluster_count, incident_count=run.incident_count,
        window_start=run.window_start, window_end=run.window_end,
        created_at=run.created_at,
    )
