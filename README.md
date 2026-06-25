# IncidentLens — Emerging Risk Clusters from Incident Streams

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Every team drowns in incident tickets. Manual review is too slow to catch emerging patterns, and keyword search is too brittle for noisy, free-form text. IncidentLens uses sentence embeddings and clustering to automatically surface **risk clusters** from your incident stream, then calls an LLM to write a crisp, human-readable summary of each cluster.

## Status

**M3 — Embedding + clustering engine (current)**

- `app/embedder.py` — `embed(incidents)` encodes incident text with `all-MiniLM-L6-v2` (CPU, ~80 MB); model is lazily loaded and cached
- `app/clusterer.py` — `cluster(incidents, embeddings)` groups incidents with HDBSCAN (falls back to KMeans when hdbscan unavailable or >50% noise); returns `ClusterResult` list sorted by `risk_score = cluster_size × Σ exp(-age_days/7)`
- `N_CLUSTERS` env var controls KMeans k (default 8)
- All tests pass: `pytest tests/ -v -m "not slow"` (skip model-download tests in CI)

M2 (data layer): synthetic dataset generator, CSV/JSONL ingest, Pydantic model.
M1 (scaffold): Python package layout, FastAPI skeleton, `GET /healthz`, pinned deps.

Risk scorer integration, LLM summarizer, and dashboard ship in M4–M5.

## Planned Architecture

```
┌─────────────┐     ┌───────────────┐     ┌─────────────┐
│  CSV / JSONL │────▶│   Embedder    │────▶│  Clusterer  │
│  (upload or  │     │ (MiniLM-L6-v2)│     │  (HDBSCAN / │
│   stdin)     │     │  sentence-    │     │   KMeans)   │
└─────────────┘     │  transformers │     └──────┬──────┘
                    └───────────────┘            │
                                                 ▼
                                        ┌─────────────────┐
                                        │  Risk Scorer    │
                                        │  size × recency │
                                        └──────┬──────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │   LLM Summarizer     │
                                    │  (OpenAI / Ollama)   │
                                    └──────────┬───────────┘
                                               │
                                               ▼
                              ┌────────────────────────────┐
                              │   FastAPI  POST /ingest    │
                              │           GET  /clusters   │
                              └──────────────┬─────────────┘
                                             │
                                             ▼
                              ┌────────────────────────────┐
                              │   HTML Dashboard (Jinja2)  │
                              │   Risk-ranked cluster cards│
                              └────────────────────────────┘
```

## Quickstart

```bash
git clone <repo-url>
cd incidentlens
make install
make run
# Open http://localhost:8000
# GET /healthz  →  {"status": "ok"}
# GET /docs     →  OpenAPI spec (endpoints added each milestone)
```

To run the smoke tests:

```bash
make test
```

To generate the synthetic dataset:

```bash
make demo   # writes demo/incidents.csv (500 rows, 8 risk themes)
```

## Project Layout

```
incidentlens/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app entry point
│   ├── models.py        # Incident Pydantic v2 model  (M2)
│   ├── ingestion.py     # load_incidents(CSV/JSONL)   (M2)
│   ├── embedder.py      # embed(incidents) → ndarray  (M3)
│   └── clusterer.py     # cluster() → ClusterResult[] (M3)
├── demo/
│   ├── __init__.py
│   ├── .gitkeep
│   └── generate_dataset.py   # 500 synthetic incidents (M2)
├── tests/
│   ├── __init__.py
│   ├── test_smoke.py         # healthz smoke test
│   ├── test_ingestion.py     # generator + ingestion tests (M2)
│   └── test_clustering.py    # embedder + clusterer tests  (M3)
├── requirements.txt     # pinned runtime + dev deps
├── Makefile             # install / run / demo / test
├── LICENSE              # MIT
└── README.md
```

## Stack

| Component | Library | Notes |
|---|---|---|
| Embeddings | `sentence-transformers` 2.7.0 | `all-MiniLM-L6-v2`, CPU-only, ~80 MB |
| Clustering | `hdbscan` 0.8.38.post1 | density-based, no k needed |
| Web API | `fastapi` 0.111.0 + `uvicorn` 0.29.0 | async, OpenAPI docs at `/docs` |
| Templating | `jinja2` 3.1.4 | server-rendered dashboard |
| LLM client | `openai` 1.30.1 | set `OPENAI_BASE_URL` for Ollama |
| Data | `pandas` 2.2.2 | CSV/JSONL ingestion |

## Roadmap

| Milestone | Scope | Status |
|---|---|---|
| M1 | Scaffold: package layout, FastAPI skeleton, Makefile, pinned deps | done |
| M2 | Data layer: synthetic dataset generator, CSV/JSONL ingest, Pydantic model | done |
| M3 | Embedding + clustering: MiniLM embedder, HDBSCAN clusterer, risk scoring | done |
| M4 | LLM summarizer: OpenAI/Ollama cluster summarizer, `POST /ingest` + `GET /clusters` endpoints | <!-- TODO --> |
| M5 | Dashboard: Jinja2 risk-ranked cluster cards, `GET /clusters` endpoint | <!-- TODO --> |

## License

MIT — see [LICENSE](LICENSE).
