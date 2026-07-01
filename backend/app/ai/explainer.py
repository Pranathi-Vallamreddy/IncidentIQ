"""Deterministic explanation layer.

This is the *fallback* explainer used whenever Gemini is unavailable — and it is
also the source of truth for the structured prompt we hand to Gemini. It performs
NO detection: it only phrases the engine's already-computed results (severity,
anomaly, growth, correlations) into human language, plus a rule-based root cause
keyed off keywords in the detected template.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExplainInput:
    """Everything the explainer is allowed to see — all engine output."""

    incident_id: str
    title: str
    service: str | None
    severity: str
    status: str
    confidence: float
    anomaly_score: float
    zscore: float
    growth_pct: float
    baseline_rate: float
    count: int
    level: str
    template: str
    example: str
    upstream: list[str]   # incident ids / labels this is downstream of
    downstream: list[str]


# Ordered keyword rules: (needle, root_cause, fixes[])
_RULES: list[tuple[tuple[str, ...], str, list[str]]] = [
    (("connection pool", "pool exhausted", "too many connections"),
     "The service exhausted its database connection pool — connections are being "
     "acquired faster than they are released (slow queries, a leak, or an undersized pool).",
     ["Increase the pool size / max connections and validate DB capacity",
      "Audit for unclosed connections or long-running transactions holding connections",
      "Add acquisition timeouts and circuit breaking to fail fast under saturation"]),
    (("503", "5xx", "upstream", "bad gateway", "returned 500"),
     "Elevated 5xx responses driven by a failing upstream dependency rather than a "
     "fault in this service itself.",
     ["Confirm the upstream dependency's health and roll back its recent changes",
      "Add retries with backoff and a circuit breaker around the upstream call",
      "Serve cached/degraded responses while the dependency recovers"]),
    (("heap", "oom", "memory", "rss"),
     "Memory pressure consistent with a leak — heap/RSS climbs until the worker "
     "approaches out-of-memory.",
     ["Capture a heap snapshot and diff allocations to find the retained objects",
      "Cap in-flight work and add back-pressure to bound memory growth",
      "Roll the affected workers and set memory limits with auto-restart"]),
    (("latency", "slo", "timeout", "slow"),
     "Latency has breached its SLO — requests are taking materially longer than the "
     "configured threshold.",
     ["Profile the hot path and check downstream call latency",
      "Add/inspect timeouts and connection reuse to bound tail latency",
      "Scale out or add caching for the slow operation"]),
    (("duplicate", "idempoten"),
     "Duplicate processing — the same work is being handled more than once, "
     "indicating a missing idempotency guard or at-least-once redelivery.",
     ["Enforce idempotency keys on the handler and dedupe on delivery id",
      "Verify ack/retry semantics on the producer",
      "Add a short-lived dedupe cache keyed on the event id"]),
    (("query", "index", "rollup"),
     "A slow database query — likely a missing index or an unbounded scan over a "
     "large table.",
     ["EXPLAIN the query and add the missing index",
      "Bound the scan (pagination / time window) and precompute heavy rollups",
      "Move the workload off the hot path to a background job"]),
    (("cache miss", "cache", "cdn", "hit ratio"),
     "Cache effectiveness dropped — a cold cache or shortened TTL is pushing load to "
     "the origin.",
     ["Warm the cache and review TTL / invalidation changes",
      "Check for a key-space change that reduced hit ratio",
      "Add stale-while-revalidate to shield the origin"]),
]


def _root_cause_and_fixes(inp: ExplainInput) -> tuple[str, list[str]]:
    hay = f"{inp.template} {inp.example} {inp.title}".lower()
    for needles, cause, fixes in _RULES:
        if any(n in hay for n in needles):
            return cause, fixes
    return (
        "An abnormal, statistically significant change in this log cluster relative "
        "to its baseline.",
        ["Inspect the example log lines below for the failing operation",
         "Correlate with recent deploys or config changes on this service",
         "Check downstream dependencies for related errors"],
    )


def _growth_phrase(inp: ExplainInput) -> str:
    if inp.baseline_rate < 1e-6:
        return "an entirely new pattern with no prior baseline"
    if inp.growth_pct >= 100:
        return f"up {inp.growth_pct:.0f}% versus its baseline"
    if inp.growth_pct <= -50:
        return "now subsiding after an earlier spike"
    return f"{inp.growth_pct:+.0f}% versus its baseline"


def explain_deterministic(inp: ExplainInput) -> dict:
    cause, fixes = _root_cause_and_fixes(inp)
    svc = inp.service or "an unknown service"

    summary = (
        f"The detection engine flagged {inp.incident_id} on {svc} as "
        f"{inp.severity} severity ({inp.confidence * 100:.0f}% confidence). "
        f"The '{inp.template}' cluster produced {inp.count} events at {inp.level} level, "
        f"{_growth_phrase(inp)} (anomaly z-score {inp.zscore:.1f})."
    )
    if inp.upstream:
        cause = (f"This incident is downstream of {', '.join(inp.upstream)}. " + cause)
    if inp.downstream:
        summary += (f" It appears to be propagating to {', '.join(inp.downstream)}.")

    return {
        "summary": summary,
        "root_cause": cause,
        "suggested_fixes": fixes,
    }


def build_prompt(inp: ExplainInput) -> str:
    """Structured, analysis-only prompt for the LLM (never raw log dumps)."""
    lines = [
        "You are an SRE assistant. The detection ENGINE has already computed the "
        "analysis below. Do NOT re-detect or re-score. Only explain it clearly.",
        "",
        f"Incident: {inp.incident_id}",
        f"Service: {inp.service}",
        f"Severity: {inp.severity} (confidence {inp.confidence * 100:.0f}%)",
        f"Status: {inp.status}",
        f"Detected template: {inp.template}",
        f"Log level: {inp.level}",
        f"Event count: {inp.count}",
        f"Anomaly z-score: {inp.zscore:.2f}; growth vs baseline: {inp.growth_pct:.0f}%",
        f"Upstream causes: {inp.upstream or 'none'}",
        f"Downstream impact: {inp.downstream or 'none'}",
        f"Representative log: {inp.example}",
        "",
        "Respond as JSON with keys: summary (2-3 sentences), root_cause (1-2 "
        "sentences), suggested_fixes (array of 3 short imperative strings).",
    ]
    return "\n".join(lines)
