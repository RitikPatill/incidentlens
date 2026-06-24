"""Tests for M2: dataset generator and ingestion pipeline."""
import textwrap
import warnings
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_csv(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "test.csv"
    p.write_text(textwrap.dedent(content))
    return p


def _write_jsonl(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "test.jsonl"
    p.write_text("\n".join(lines))
    return p


# ---------------------------------------------------------------------------
# test_generate_dataset_shape
# ---------------------------------------------------------------------------

def test_generate_dataset_shape():
    from demo.generate_dataset import generate

    df = generate()
    assert len(df) == 500, f"Expected 500 rows, got {len(df)}"

    required_columns = {"id", "timestamp", "title", "description", "severity", "source"}
    assert required_columns.issubset(set(df.columns)), f"Missing columns: {required_columns - set(df.columns)}"

    for col in required_columns:
        null_count = df[col].isnull().sum()
        assert null_count == 0, f"Column '{col}' has {null_count} null values"


# ---------------------------------------------------------------------------
# test_load_csv_happy_path
# ---------------------------------------------------------------------------

def test_load_csv_happy_path(tmp_path):
    from app.ingestion import load_incidents

    csv_path = _write_csv(
        tmp_path,
        """\
        id,timestamp,title,description,severity,source
        INC-0001,2024-06-01T10:00:00+00:00,Login failed,SSO auth error,high,security
        INC-0002,2024-06-01T11:00:00+00:00,Payment declined,Card declined,critical,monitoring
        INC-0003,2024-06-01T12:00:00+00:00,Disk full,Storage at 95%,medium,on-call
        """,
    )

    incidents = load_incidents(csv_path)
    assert len(incidents) == 3
    for inc in incidents:
        assert isinstance(inc.timestamp, datetime)
    assert incidents[0].id == "INC-0001"
    assert incidents[1].severity == "critical"


# ---------------------------------------------------------------------------
# test_load_jsonl_happy_path
# ---------------------------------------------------------------------------

def test_load_jsonl_happy_path(tmp_path):
    from app.ingestion import load_incidents

    jsonl_path = _write_jsonl(
        tmp_path,
        [
            '{"id":"INC-0001","timestamp":"2024-06-01T10:00:00+00:00","title":"Login failed","description":"SSO error","severity":"high","source":"security"}',
            '{"id":"INC-0002","timestamp":"2024-06-01T11:00:00+00:00","title":"Payment declined","description":"Card rejected","severity":"critical","source":"monitoring"}',
            '{"id":"INC-0003","timestamp":"2024-06-01T12:00:00+00:00","title":"Disk full","description":"Storage at 95%","severity":"medium","source":"on-call"}',
        ],
    )

    incidents = load_incidents(jsonl_path)
    assert len(incidents) == 3
    for inc in incidents:
        assert isinstance(inc.timestamp, datetime)


# ---------------------------------------------------------------------------
# test_load_skips_bad_row
# ---------------------------------------------------------------------------

def test_load_skips_bad_row(tmp_path):
    from app.ingestion import load_incidents

    csv_path = _write_csv(
        tmp_path,
        """\
        id,timestamp,title,description,severity,source
        INC-0001,2024-06-01T10:00:00+00:00,Login failed,SSO auth error,high,security
        INC-0002,2024-06-01T11:00:00+00:00,Payment declined,Card declined,INVALID_SEVERITY,monitoring
        INC-0003,2024-06-01T12:00:00+00:00,Disk full,Storage at 95%,medium,on-call
        """,
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        incidents = load_incidents(csv_path)

    assert len(incidents) == 2
    assert any("INC-0002" in str(w.message) for w in caught), "Expected warning for bad row"


# ---------------------------------------------------------------------------
# test_incident_severity_validation
# ---------------------------------------------------------------------------

def test_incident_severity_validation():
    from app.models import Incident

    with pytest.raises(ValidationError):
        Incident(
            id="INC-0001",
            timestamp="2024-06-01T10:00:00+00:00",
            title="Test",
            description="Test description",
            severity="invalid",
            source="monitoring",
        )
