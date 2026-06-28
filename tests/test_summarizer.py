"""Tests for app/summarizer.py — all OpenAI calls are mocked."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.models import ClusterSummary, Incident
from app.summarizer import _centroid_hash, summarize_cluster


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_members(n: int = 5) -> list[Incident]:
    return [
        Incident(
            id=f"INC-{i:03d}",
            timestamp=datetime(2024, 6, i + 1, tzinfo=timezone.utc),
            title=f"Service {i} degraded",
            description=f"Error rate spike on service {i}",
            severity="high" if i % 2 == 0 else "medium",
            source="alertmanager",
        )
        for i in range(1, n + 1)
    ]


def _make_centroid() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.random(384).astype(np.float32)


def _fake_cluster(cluster_id: int = 0, size: int = 5):
    return SimpleNamespace(
        cluster_id=cluster_id,
        size=size,
        risk_score=12.3,
        top_severity="high",
    )


def _mock_response(theme: str, risk_description: str, top_incidents: list[str]):
    payload = json.dumps(
        {"theme": theme, "risk_description": risk_description, "top_incidents": top_incidents}
    )
    msg = SimpleNamespace(content=payload)
    choice = SimpleNamespace(message=msg)
    return SimpleNamespace(choices=[choice])


# ---------------------------------------------------------------------------
# Fixtures that reset module-level cache between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    import app.summarizer as mod
    mod._CACHE.clear()
    mod._CLIENT = None
    yield
    mod._CACHE.clear()
    mod._CLIENT = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_summarize_returns_cluster_summary():
    members = _make_members()
    centroid = _make_centroid()
    cluster = _fake_cluster()

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(
        theme="Database connection pool exhausted",
        risk_description="High volume of connection failures may cascade to service outage.",
        top_incidents=["Service 1 degraded", "Service 2 degraded", "Service 3 degraded"],
    )

    with patch("app.summarizer._get_client", return_value=mock_client):
        result = summarize_cluster(cluster, members, centroid)

    assert isinstance(result, ClusterSummary)
    assert result.theme != ""
    assert result.risk_description != ""
    assert len(result.top_incidents) == 3


def test_cache_prevents_second_api_call():
    members = _make_members()
    centroid = _make_centroid()
    cluster = _fake_cluster()

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(
        theme="Disk I/O saturation",
        risk_description="Persistent disk I/O latency affecting write throughput.",
        top_incidents=["Service 1 degraded", "Service 2 degraded", "Service 3 degraded"],
    )

    with patch("app.summarizer._get_client", return_value=mock_client):
        summarize_cluster(cluster, members, centroid)
        summarize_cluster(cluster, members, centroid)

    mock_client.chat.completions.create.assert_called_once()


def test_different_centroid_calls_api_twice():
    members = _make_members()
    centroid_a = _make_centroid()
    rng = np.random.default_rng(99)
    centroid_b = rng.random(384).astype(np.float32)
    cluster = _fake_cluster()

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(
        theme="Network latency spikes",
        risk_description="Intermittent packet loss causing timeout errors.",
        top_incidents=["Service 1 degraded", "Service 2 degraded", "Service 3 degraded"],
    )

    with patch("app.summarizer._get_client", return_value=mock_client):
        summarize_cluster(cluster, members, centroid_a)
        summarize_cluster(cluster, members, centroid_b)

    assert mock_client.chat.completions.create.call_count == 2


def test_ollama_base_url_override(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "ollama")

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _mock_response(
            theme="CPU throttling event",
            risk_description="Sustained CPU throttling causing latency.",
            top_incidents=["Service 1 degraded", "Service 2 degraded", "Service 3 degraded"],
        )

        import app.summarizer as mod
        mod._CLIENT = None  # force rebuild

        summarize_cluster(_fake_cluster(), _make_members(), _make_centroid())

        call_kwargs = mock_openai_cls.call_args
        assert call_kwargs.kwargs.get("base_url") == "http://localhost:11434/v1"


def test_malformed_json_fallback():
    members = _make_members()
    centroid = _make_centroid()
    cluster = _fake_cluster()

    mock_client = MagicMock()
    bad_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not valid json at all!!!"))]
    )
    mock_client.chat.completions.create.return_value = bad_response

    with patch("app.summarizer._get_client", return_value=mock_client):
        result = summarize_cluster(cluster, members, centroid)

    assert isinstance(result, ClusterSummary)
    assert isinstance(result.theme, str)
    assert isinstance(result.risk_description, str)
    assert len(result.top_incidents) == 3
