"""Tests for M3: embedding + clustering engine."""
from __future__ import annotations

import importlib
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
import pytest

from app.models import Incident


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_incident(
    idx: int,
    days_ago: float = 1.0,
    severity: str = "medium",
) -> Incident:
    ts = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return Incident(
        id=f"INC-{idx:04d}",
        timestamp=ts,
        title=f"Incident {idx}",
        description=f"Description for incident {idx}",
        severity=severity,  # type: ignore[arg-type]
        source="test",
    )


def _make_incidents(n: int, days_ago: float = 1.0) -> list[Incident]:
    return [_make_incident(i, days_ago=days_ago) for i in range(n)]


def _random_embeddings(n: int, dim: int = 384) -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.random((n, dim), dtype=np.float32)


# ---------------------------------------------------------------------------
# test_embed_shape
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_embed_shape():
    """embed() returns float32 ndarray of shape (N, 384). Requires model download."""
    from demo.generate_dataset import generate
    from app.embedder import embed

    df = generate()
    sample = df.head(5)
    incidents = [
        Incident(
            id=row["id"],
            timestamp=row["timestamp"],
            title=row["title"],
            description=row["description"],
            severity=row["severity"],
            source=row["source"],
        )
        for _, row in sample.iterrows()
    ]

    embeddings = embed(incidents)
    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (5, 384)
    assert embeddings.dtype == np.float32


# ---------------------------------------------------------------------------
# test_cluster_returns_results
# ---------------------------------------------------------------------------

def test_cluster_returns_results():
    """cluster() returns non-empty ClusterResult list with valid fields."""
    from app.clusterer import cluster

    incidents = _make_incidents(20)
    embeddings = _random_embeddings(20)

    results = cluster(incidents, embeddings)

    assert len(results) > 0
    for r in results:
        assert r.size >= 1
        assert r.risk_score > 0
        assert len(r.incident_ids) == r.size


# ---------------------------------------------------------------------------
# test_risk_score_recency
# ---------------------------------------------------------------------------

def test_risk_score_recency():
    """Recent clusters have higher risk_score than old clusters."""
    from app.clusterer import ClusterResult, _build_results

    recent = _make_incident(0, days_ago=1.0, severity="high")
    old = _make_incident(1, days_ago=20.0, severity="high")

    # Two clusters: label 0 = recent, label 1 = old
    labels = np.array([0, 1])
    results = _build_results(labels, [recent, old])

    by_id = {r.cluster_id: r for r in results}
    assert by_id[0].risk_score > by_id[1].risk_score


# ---------------------------------------------------------------------------
# test_noise_cluster_excluded_or_last
# ---------------------------------------------------------------------------

def test_noise_cluster_excluded_or_last():
    """HDBSCAN noise cluster (id=-1) appears last in sorted output."""
    from app.clusterer import _build_results

    # One recent cluster (id=0) and one noise point (id=-1, old)
    recent = _make_incident(0, days_ago=1.0)
    noise_old = _make_incident(1, days_ago=30.0)

    labels = np.array([0, -1])
    results = _build_results(labels, [recent, noise_old])

    # Noise cluster must be last (it has a very low risk_score)
    assert results[-1].cluster_id == -1


# ---------------------------------------------------------------------------
# test_kmeans_fallback
# ---------------------------------------------------------------------------

def test_kmeans_fallback():
    """cluster() falls back to KMeans when hdbscan import fails."""
    from app.clusterer import cluster

    incidents = _make_incidents(20)
    embeddings = _random_embeddings(20)

    # Remove hdbscan from sys.modules and make import raise ImportError
    with patch.dict(sys.modules, {"hdbscan": None}):
        results = cluster(incidents, embeddings)

    assert len(results) > 0
    for r in results:
        assert r.size >= 1
        assert r.risk_score > 0
