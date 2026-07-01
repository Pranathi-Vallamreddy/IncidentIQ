"""Deterministic synthetic log generator.

Produces realistic *raw log input* for the engine to analyse. It never fabricates
analysis results — clusters, anomalies, severities and correlations are all
computed by the engine from these lines. A fixed RNG seed keeps every dataset
reproducible so the demo tells the same story each run.

Run:  python -m app.data.generate_samples
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
SEED = 20260630
WINDOW_START = datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 6, 30, 14, 0, 0, tzinfo=timezone.utc)


def _rng() -> random.Random:
    return random.Random(SEED)


def _ts(rng: random.Random, start: datetime, end: datetime) -> datetime:
    span = (end - start).total_seconds()
    return start + timedelta(seconds=rng.uniform(0, span))


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


# --- normal baseline traffic templates per service -------------------------
_BASELINE = {
    "payments-api": [
        ("INFO", lambda r: f"processed payment intent pi_{r.randrange(10**6):06d} amount={r.randrange(5,900)}.{r.randrange(0,99):02d} currency=USD"),
        ("INFO", lambda r: f"charge authorized card=**** {r.randrange(1000,9999)} latency={r.randrange(30,180)}ms"),
        ("DEBUG", lambda r: f"acquired db connection from pool active={r.randrange(3,40)} idle={r.randrange(5,50)}"),
    ],
    "checkout-gateway": [
        ("INFO", lambda r: f"checkout completed order=ord_{r.randrange(10**6):06d} items={r.randrange(1,8)} status=200 latency={r.randrange(80,300)}ms"),
        ("INFO", lambda r: f"cart validated session={r.randrange(10**7):07d} total={r.randrange(10,400)}.{r.randrange(0,99):02d}"),
    ],
    "auth-service": [
        ("INFO", lambda r: f"token issued user={r.randrange(10**6):06d} scope=read latency={r.randrange(20,120)}ms"),
        ("INFO", lambda r: f"login success user={r.randrange(10**6):06d} method=password"),
    ],
    "media-worker": [
        ("INFO", lambda r: f"resized image asset=img_{r.randrange(10**6):06d} bytes={r.randrange(20000,900000)} heap={r.randrange(40,70)}%"),
        ("DEBUG", lambda r: f"thumbnail generated asset=img_{r.randrange(10**6):06d} ms={r.randrange(50,400)}"),
    ],
    "analytics-api": [
        ("INFO", lambda r: f"rollup completed job=agg_{r.randrange(10**5):05d} rows={r.randrange(1000,50000)} duration={r.randrange(200,900)}ms"),
    ],
    "edge-cache": [
        ("INFO", lambda r: f"cache hit key=/product/{r.randrange(10**5):05d} region=us-east ratio=0.9{r.randrange(0,9)}"),
    ],
    "webhooks": [
        ("INFO", lambda r: f"webhook delivered id=wh_{r.randrange(10**5):05d} status=200 attempt=1"),
    ],
}


def _baseline_lines(rng: random.Random, per_service: int) -> list[tuple[datetime, str, str, str]]:
    """Return (ts, level, service, message) tuples spread across the window."""
    out = []
    for service, templates in _BASELINE.items():
        for _ in range(per_service):
            level, fn = rng.choice(templates)
            out.append((_ts(rng, WINDOW_START, WINDOW_END), level, service, fn(rng)))
    return out


def _burst(
    rng: random.Random,
    service: str,
    level: str,
    fn,
    start: datetime,
    end: datetime,
    count: int,
) -> list[tuple[datetime, str, str, str]]:
    return [(_ts(rng, start, end), level, service, fn(rng)) for _ in range(count)]


def _incident_lines(rng: random.Random) -> list[tuple[datetime, str, str, str]]:
    out: list[tuple[datetime, str, str, str]] = []
    t = WINDOW_END

    # 1. payments-api DB connection pool exhaustion (Critical, recent, root cause)
    out += _burst(
        rng, "payments-api", "ERROR",
        lambda r: (f"connection pool exhausted acquiring connection to payments-db "
                   f"after {r.randrange(3000,8000)}ms active=100 idle=0 waiting={r.randrange(40,120)}"),
        t - timedelta(minutes=15), t, 190,
    )
    # 2. checkout-gateway elevated 5xx (Critical, recent, downstream of #1)
    out += _burst(
        rng, "checkout-gateway", "ERROR",
        lambda r: (f"checkout request failed upstream payments-api returned 503 "
                   f"status=500 latency={r.randrange(3000,6000)}ms order=ord_{r.randrange(10**6):06d}"),
        t - timedelta(minutes=13), t, 160,
    )
    # 3. auth-service token refresh latency spike (High, recent)
    out += _burst(
        rng, "auth-service", "WARN",
        lambda r: (f"auth token refresh exceeded slo latency={r.randrange(900,2200)}ms "
                   f"threshold=500ms user={r.randrange(10**6):06d}"),
        t - timedelta(minutes=12), t, 90,
    )
    # 4. media-worker memory leak (High, recent)
    out += _burst(
        rng, "media-worker", "ERROR",
        lambda r: (f"image resize worker heap usage {r.randrange(88,99)}% rss={r.randrange(1600,2100)}MB "
                   f"oom risk asset=img_{r.randrange(10**6):06d}"),
        t - timedelta(minutes=18), t, 70,
    )
    # 5. webhooks duplicate deliveries (Medium, recent)
    out += _burst(
        rng, "webhooks", "WARN",
        lambda r: (f"duplicate webhook delivery detected id=wh_{r.randrange(10**5):05d} "
                   f"attempt={r.randrange(2,5)} status=200"),
        t - timedelta(minutes=20), t, 55,
    )
    # 6. analytics-api slow query (Medium, RESOLVED — mid-window, no recent activity)
    out += _burst(
        rng, "analytics-api", "WARN",
        lambda r: (f"slow query on analytics rollup duration={r.randrange(6000,12000)}ms "
                   f"rows={r.randrange(800000,1500000)} job=agg_{r.randrange(10**5):05d}"),
        WINDOW_START + timedelta(minutes=40), WINDOW_START + timedelta(minutes=70), 60,
    )
    # 7. edge-cache miss ratio degraded (Low, RESOLVED — early window)
    out += _burst(
        rng, "edge-cache", "WARN",
        lambda r: (f"cdn cache miss ratio degraded ratio=0.{r.randrange(35,55)} region=us-east "
                   f"key=/product/{r.randrange(10**5):05d}"),
        WINDOW_START + timedelta(minutes=10), WINDOW_START + timedelta(minutes=35), 45,
    )
    return out


def _write_text(path: Path, rows: list[tuple[datetime, str, str, str]]) -> None:
    rows = sorted(rows, key=lambda r: r[0])
    lines = [f"{_iso(ts)} {level} {service} {msg}" for ts, level, service, msg in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_ndjson(path: Path, rows: list[tuple[datetime, str, str, str]]) -> None:
    rows = sorted(rows, key=lambda r: r[0])
    lines = [
        json.dumps({"timestamp": _iso(ts), "level": level, "service": service, "message": msg})
        for ts, level, service, msg in rows
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate() -> list[Path]:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # 1) Marquee cascade dataset (text) — reproduces the mockup incident board.
    rng = _rng()
    rows = _baseline_lines(rng, per_service=90) + _incident_lines(rng)
    p = SAMPLES_DIR / "ecommerce-cascade.log"
    _write_text(p, rows)
    written.append(p)

    # 2) Platform microservices (NDJSON) — format-variety + broad baseline.
    rng = random.Random(SEED + 1)
    rows = _baseline_lines(rng, per_service=140)
    rows += _burst(
        rng, "media-worker", "ERROR",
        lambda r: (f"image resize worker heap usage {r.randrange(90,99)}% rss={r.randrange(1700,2200)}MB "
                   f"oom risk asset=img_{r.randrange(10**6):06d}"),
        WINDOW_END - timedelta(minutes=16), WINDOW_END, 80,
    )
    rows += _burst(
        rng, "auth-service", "ERROR",
        lambda r: (f"auth token refresh exceeded slo latency={r.randrange(1000,2400)}ms "
                   f"threshold=500ms user={r.randrange(10**6):06d}"),
        WINDOW_END - timedelta(minutes=14), WINDOW_END, 65,
    )
    p = SAMPLES_DIR / "platform-microservices.ndjson"
    _write_ndjson(p, rows)
    written.append(p)

    # 3) Payments postmortem focus (text) — pure DB pool cascade, smaller.
    rng = random.Random(SEED + 2)
    rows = _baseline_lines(rng, per_service=40)
    rows += _burst(
        rng, "payments-api", "FATAL",
        lambda r: (f"connection pool exhausted acquiring connection to payments-db "
                   f"after {r.randrange(4000,9000)}ms active=100 idle=0 waiting={r.randrange(60,140)}"),
        WINDOW_END - timedelta(minutes=12), WINDOW_END, 130,
    )
    rows += _burst(
        rng, "checkout-gateway", "ERROR",
        lambda r: (f"checkout request failed upstream payments-api returned 503 "
                   f"status=500 latency={r.randrange(3500,7000)}ms order=ord_{r.randrange(10**6):06d}"),
        WINDOW_END - timedelta(minutes=10), WINDOW_END, 110,
    )
    p = SAMPLES_DIR / "payments-postmortem.log"
    _write_text(p, rows)
    written.append(p)

    return written


if __name__ == "__main__":
    for path in generate():
        size = path.stat().st_size
        print(f"wrote {path.name:32s} {size/1024:7.1f} KB")
