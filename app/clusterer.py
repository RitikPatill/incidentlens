"""Clustering engine: groups incident embeddings and computes risk scores."""
from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timezone
from math import exp

import numpy as np
from pydantic import BaseModel
from sklearn.cluster import KMeans

from app.models import Incident

K: int = int(os.environ.get("N_CLUSTERS", "8"))


class ClusterResult(BaseModel):
    cluster_id: int          # -1 = HDBSCAN noise bucket
    incident_ids: list[str]
    size: int
    risk_score: float        # cluster_size * sum(recency_weight per incident)
    top_severity: str        # most common severity in cluster


def _recency_weight(incident: Incident) -> float:
    now = datetime.now(tz=timezone.utc)
    age_days = (now - incident.timestamp).total_seconds() / 86400.0
    return exp(-age_days / 7.0)


def _build_results(
    labels: np.ndarray,
    incidents: list[Incident],
) -> list[ClusterResult]:
    groups: dict[int, list[Incident]] = {}
    for label, inc in zip(labels, incidents):
        groups.setdefault(int(label), []).append(inc)

    results: list[ClusterResult] = []
    for cluster_id, members in groups.items():
        size = len(members)
        risk_score = size * sum(_recency_weight(inc) for inc in members)
        top_severity = Counter(inc.severity for inc in members).most_common(1)[0][0]
        results.append(
            ClusterResult(
                cluster_id=cluster_id,
                incident_ids=[inc.id for inc in members],
                size=size,
                risk_score=risk_score,
                top_severity=top_severity,
            )
        )

    # Sort by risk_score descending; noise cluster (-1) naturally falls last
    results.sort(key=lambda r: r.risk_score, reverse=True)
    return results


def cluster(
    incidents: list[Incident],
    embeddings: np.ndarray,
    k: int = K,
) -> list[ClusterResult]:
    """Cluster embeddings and return risk-scored ClusterResult list.

    Strategy:
    1. Try HDBSCAN(min_cluster_size=max(5, len//20)).
       If hdbscan import fails or produces >50% noise, fall back to KMeans(k).
    2. Compute risk_score = cluster_size * sum(exp(-age_days/7)) per cluster.
    3. Return list sorted by risk_score descending.
    """
    labels: np.ndarray | None = None

    try:
        import hdbscan  # noqa: PLC0415

        min_cluster_size = max(5, len(incidents) // 20)
        hdb = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
        hdb_labels: np.ndarray = hdb.fit_predict(embeddings)
        noise_ratio = (hdb_labels == -1).sum() / len(hdb_labels)
        if noise_ratio <= 0.5:
            labels = hdb_labels
    except ImportError:
        pass  # fall through to KMeans

    if labels is None:
        n_clusters = min(k, len(incidents))
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)

    return _build_results(labels, incidents)
