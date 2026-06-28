"""LLM-based cluster summarization via OpenAI chat completions."""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import openai

from app.models import ClusterSummary, Incident

# Import ClusterResult from models-adjacent location to avoid circular imports with M5.
# clusterer.ClusterResult is imported lazily inside the function signature type hint only.

_CACHE: dict[str, ClusterSummary] = {}
_CLIENT: openai.OpenAI | None = None


def _centroid_hash(centroid: np.ndarray) -> str:
    """SHA-256 hex digest of centroid float32 bytes."""
    return hashlib.sha256(centroid.astype(np.float32).tobytes()).hexdigest()


def _get_client() -> openai.OpenAI:
    """Lazily build OpenAI client; picks up OPENAI_BASE_URL + OPENAI_API_KEY.

    When OPENAI_BASE_URL is set to an Ollama endpoint (e.g. http://localhost:11434/v1),
    set OPENAI_API_KEY=ollama (Ollama ignores the key but the client requires one).
    """
    global _CLIENT
    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY", "ollama" if base_url else None)
    # Rebuild if env vars may have changed (simple check: always rebuild when base_url present)
    if _CLIENT is None:
        kwargs: dict = {}
        if base_url:
            kwargs["base_url"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        _CLIENT = openai.OpenAI(**kwargs)
    return _CLIENT


def summarize_cluster(
    cluster,  # ClusterResult — avoid module-level import to prevent circular deps
    members: list[Incident],
    centroid: np.ndarray,
) -> ClusterSummary:
    """Return ClusterSummary, using cache if centroid was seen before.

    Args:
        cluster: ClusterResult with cluster_id, size, risk_score, top_severity.
        members: Incident objects belonging to this cluster.
        centroid: float32 ndarray of shape (384,) — mean of member embeddings.
    """
    cache_key = _centroid_hash(centroid)
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    # Sort by recency (newest first) and take up to 10 for the prompt
    sorted_members = sorted(members, key=lambda inc: inc.timestamp, reverse=True)[:10]
    incident_lines = "\n".join(
        f"- [{inc.severity.upper()}] {inc.title} ({inc.timestamp.date()})"
        for inc in sorted_members
    )

    system_msg = (
        "You are a site-reliability analyst. Respond with a JSON object containing exactly "
        "three keys: 'theme' (a ≤6-word cluster name), 'risk_description' (one sentence "
        "explaining the risk), and 'top_incidents' (a JSON array of exactly 3 incident titles "
        "from the list provided, verbatim)."
    )
    user_msg = (
        f"Cluster has {cluster.size} incidents, top severity: {cluster.top_severity}.\n"
        f"Recent incidents (newest first):\n{incident_lines}\n\n"
        "Identify the common theme and risk. Return valid JSON only."
    )

    theme = "Unknown cluster theme"
    risk_description = "No risk description available."
    top_incidents: list[str] = [inc.title for inc in sorted_members[:3]]

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw)
        theme = str(data.get("theme", theme))
        risk_description = str(data.get("risk_description", risk_description))
        parsed_incidents = data.get("top_incidents", [])
        if isinstance(parsed_incidents, list) and parsed_incidents:
            top_incidents = [str(t) for t in parsed_incidents[:3]]
    except Exception:
        pass  # fallback values already set above

    # Pad top_incidents to exactly 3 if fewer were returned
    while len(top_incidents) < 3:
        top_incidents.append("")

    summary = ClusterSummary(
        cluster_id=cluster.cluster_id,
        size=cluster.size,
        risk_score=cluster.risk_score,
        top_severity=cluster.top_severity,
        theme=theme,
        risk_description=risk_description,
        top_incidents=top_incidents[:3],
    )
    _CACHE[cache_key] = summary
    return summary
