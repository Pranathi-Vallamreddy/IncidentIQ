"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import dashboard, incidents, logs, settings
from .config import settings as env_settings
from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="IncidentIQ API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=env_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "ai_enabled": env_settings.ai_enabled}
