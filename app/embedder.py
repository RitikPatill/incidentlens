"""Sentence embedding for incidents using all-MiniLM-L6-v2."""
from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from app.models import Incident

_MODEL: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def embed(incidents: list[Incident]) -> np.ndarray:
    """Return float32 array of shape (len(incidents), 384).

    Concatenates title + ' ' + description as the text to encode.
    Lazily loads the model on first call and caches it.
    """
    texts = [f"{inc.title} {inc.description}" for inc in incidents]
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.astype(np.float32)
