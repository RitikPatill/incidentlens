from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class Incident(BaseModel):
    id: str
    timestamp: datetime
    title: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    source: str

    @field_validator("id")
    @classmethod
    def id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("id must not be empty")
        return v.strip()


class ClusterSummary(BaseModel):
    cluster_id: int
    size: int
    risk_score: float
    top_severity: str
    theme: str                    # ≤6 words
    risk_description: str         # one sentence
    top_incidents: list[str]      # 3 incident titles
