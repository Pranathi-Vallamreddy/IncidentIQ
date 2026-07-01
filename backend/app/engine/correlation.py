"""Correlation engine: link incidents into cause chains.

Two mechanisms, both deterministic and computed by the engine (never the LLM):

  * dependency  - a static service dependency graph. If a downstream service's
                  incident starts at/after an upstream service's incident, we
                  emit an upstream -> downstream edge. This is what surfaces
                  "checkout 5xx is downstream of DB pool exhaustion".
  * temporal    - two high-severity incidents on unrelated services that ignite
                  within a short lag are flagged as a weaker temporal link.
"""

from __future__ import annotations

from .types import Correlation, Incident

# downstream service -> upstream services it depends on.
DEPENDENCIES: dict[str, set[str]] = {
    "checkout-gateway": {"payments-api", "cart-service", "auth-service"},
    "payments-api": {"payments-db", "auth-service"},
    "orders-api": {"payments-api", "orders-db"},
    "webhooks": {"orders-api"},
    "media-worker": {"media-storage"},
    "analytics-api": {"analytics-db"},
}

# Upstream may lead downstream by at most this long to be considered causal.
_MAX_LAG_SECONDS = 60 * 60
# Allow a little slack for downstream appearing marginally before upstream.
_LEAD_TOLERANCE_SECONDS = 120
_TEMPORAL_WINDOW_SECONDS = 180


def _depends_on(downstream: str | None, upstream: str | None) -> bool:
    if not downstream or not upstream:
        return False
    return upstream in DEPENDENCIES.get(downstream, set())


def correlate(incidents: list[Incident]) -> list[Correlation]:
    correlations: list[Correlation] = []
    linked: set[tuple[str, str]] = set()

    for downstream in incidents:
        for upstream in incidents:
            if upstream.incident_id == downstream.incident_id:
                continue
            if not _depends_on(downstream.service, upstream.service):
                continue
            lag = (downstream.first_seen - upstream.first_seen).total_seconds()
            if lag < -_LEAD_TOLERANCE_SECONDS or lag > _MAX_LAG_SECONDS:
                continue
            correlations.append(
                Correlation(
                    upstream_id=upstream.incident_id,
                    downstream_id=downstream.incident_id,
                    kind="dependency",
                    detail=(
                        f"{downstream.service} depends on {upstream.service}; "
                        f"{downstream.incident_id} ignited ~{max(lag, 0):.0f}s after "
                        f"{upstream.incident_id}"
                    ),
                    lag_seconds=lag,
                )
            )
            linked.add((upstream.incident_id, downstream.incident_id))
            _link(upstream, downstream)

    # Temporal links between high-severity incidents not already dependency-linked.
    high = [i for i in incidents if i.severity in ("Critical", "High")]
    for idx, a in enumerate(high):
        for b in high[idx + 1:]:
            if a.service == b.service:
                continue
            pair = tuple(sorted((a.incident_id, b.incident_id)))
            if pair in linked or (pair[1], pair[0]) in linked:
                continue
            lag = abs((a.first_seen - b.first_seen).total_seconds())
            if lag > _TEMPORAL_WINDOW_SECONDS:
                continue
            first, second = (a, b) if a.first_seen <= b.first_seen else (b, a)
            correlations.append(
                Correlation(
                    upstream_id=first.incident_id,
                    downstream_id=second.incident_id,
                    kind="temporal",
                    detail=(
                        f"{first.incident_id} and {second.incident_id} spiked within "
                        f"{lag:.0f}s across services"
                    ),
                    lag_seconds=(second.first_seen - first.first_seen).total_seconds(),
                )
            )
            linked.add(pair)
            _link(first, second)

    return correlations


def _link(a: Incident, b: Incident) -> None:
    if b.incident_id not in a.correlated_ids:
        a.correlated_ids.append(b.incident_id)
    if a.incident_id not in b.correlated_ids:
        b.correlated_ids.append(a.incident_id)
