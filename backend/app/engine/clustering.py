"""Clustering: turn mined templates into Cluster objects.

In this engine a *template is a cluster* — the Drain miner already groups every
event into exactly one template. This module's job is to lift the raw
``Template`` records into the richer ``Cluster`` structure the rest of the
pipeline (frequency, anomaly, severity) annotates in place.
"""

from __future__ import annotations

from datetime import datetime

from .types import Cluster, Template


def build_clusters(templates: list[Template]) -> list[Cluster]:
    clusters: list[Cluster] = []
    for tmpl in templates:
        if tmpl.count == 0:
            continue
        first = tmpl.first_seen or datetime.min
        last = tmpl.last_seen or first
        clusters.append(
            Cluster(
                cluster_id=tmpl.template_id,
                template=tmpl.pattern,
                tokens=list(tmpl.tokens),
                token_count=tmpl.token_count,
                level=tmpl.level,
                count=tmpl.count,
                example=tmpl.example,
                examples=list(tmpl.examples),
                first_seen=first,
                last_seen=last,
                services=dict(tmpl.services),
            )
        )
    return clusters
