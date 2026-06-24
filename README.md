# IncidentLens — Emerging Risk Clusters from Incident Streams

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Every team drowns in incident tickets. Manual review is too slow to catch emerging patterns, and keyword search is too brittle for noisy, free-form text. IncidentLens uses sentence embeddings and clustering to automatically surface **risk clusters** from your incident stream, then calls an LLM to write a crisp, human-readable summary of each cluster.

## Status

**M2 — Synthetic dataset + ingestion pipeline (current)**

- `demo/generate_dataset.py` produces 500 reproducible fictional incident tickets across 8 hidden risk themes (auth failures, payment errors, latency spikes, data pipeline, disk pressure, deployment issues, network flap, security alerts)
- `app/models.py` — `Incident` Pydantic v2 model with validated severity enum
- `app/ingestion.py` — `load_incidents(source)` reads CSV or JSONL (or stdin via `"-"`), skips and warns on bad rows
- All tests pass: `pytest tests/ -v`
- `make demo` generates `demo/incidents.csv`

M1 (scaffold): Python package layout, FastAPI skeleton, `GET /healthz`, pinned deps.

Embedder, clusterer, risk scorer, LLM summarizer, and dashboard ship in M3–M5.

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
│   └── ingestion.py     # load_incidents(CSV/JSONL)   (M2)
├── demo/
│   ├── __init__.py
│   ├── .gitkeep
│   └── generate_dataset.py   # 500 synthetic incidents (M2)
├── tests/
│   ├── __init__.py
│   ├── test_smoke.py         # healthz smoke test
│   └── test_ingestion.py     # generator + ingestion tests (M2)
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
| M3 | Embedding + clustering: MiniLM embedder, HDBSCAN clusterer, in-memory store | <!-- TODO --> |
| M4 | Risk scoring + LLM summarizer: recency-weighted scorer, OpenAI/Ollama summarizer | <!-- TODO --> |
| M5 | Dashboard: Jinja2 risk-ranked cluster cards, `GET /clusters` endpoint | <!-- TODO --> |

## License

MIT — see [LICENSE](LICENSE).
