import io
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.models import ClusterSummary


@pytest.fixture(autouse=True)
def _clear_state():
    main_module._state = []
    yield
    main_module._state = []


def test_app_title():
    assert app.title == "IncidentLens"


def test_healthz():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_clusters_empty():
    client = TestClient(app)
    response = client.get("/clusters")
    assert response.status_code == 200
    assert response.json() == []


_TINY_CSV = """\
id,timestamp,title,description,severity,source
INC001,2024-01-01T00:00:00Z,DB connection timeout,Database pool exhausted,high,db-monitor
INC002,2024-01-01T01:00:00Z,DB connection timeout,Connection refused to primary,high,db-monitor
INC003,2024-01-01T02:00:00Z,DB connection timeout,Read replica lag spike,medium,db-monitor
INC004,2024-01-01T03:00:00Z,API 500 errors,Service returning 500,critical,api-monitor
INC005,2024-01-01T04:00:00Z,API 500 errors,Gateway timeout upstream,high,api-monitor
INC006,2024-01-01T05:00:00Z,Disk full,Root partition at 98%,high,infra-monitor
INC007,2024-01-01T06:00:00Z,Disk full,Log rotation failed,medium,infra-monitor
INC008,2024-01-01T07:00:00Z,Memory leak,JVM heap growing unbounded,critical,jvm-monitor
INC009,2024-01-01T08:00:00Z,Memory leak,OOM killer triggered,critical,infra-monitor
INC010,2024-01-01T09:00:00Z,Network packet loss,20% packet loss on eth0,high,net-monitor
""".encode()

_FIXED_SUMMARY = ClusterSummary(
    cluster_id=0,
    size=10,
    risk_score=9.5,
    top_severity="high",
    theme="Database connectivity issues",
    risk_description="Repeated DB connection failures indicate a systemic risk.",
    top_incidents=["DB connection timeout", "API 500 errors", "Disk full"],
)


def test_ingest_and_clusters():
    client = TestClient(app)

    fake_embeddings = np.random.rand(10, 384).astype(np.float32)

    with (
        patch("app.main.embed", return_value=fake_embeddings),
        patch("app.main.summarize_cluster", return_value=_FIXED_SUMMARY),
    ):
        response = client.post(
            "/ingest",
            files={"file": ("incidents.csv", io.BytesIO(_TINY_CSV), "text/csv")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ingested"] == 10
    assert data["clusters"] >= 1

    clusters_response = client.get("/clusters")
    assert clusters_response.status_code == 200
    clusters = clusters_response.json()
    assert len(clusters) >= 1
    assert clusters[0]["theme"] == "Database connectivity issues"


def test_dashboard_renders():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
