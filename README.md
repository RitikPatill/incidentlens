# IncidentLens — Emerging Risk Clusters from Incident Streams

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Every team drowns in incident tickets. Manual review is too slow to catch emerging patterns, and keyword search is too brittle for noisy, free-form text. IncidentLens uses sentence embeddings and clustering to automatically surface **risk clusters** from your incident stream, then calls an LLM to write a crisp, human-readable summary of each cluster.

## Status

**M1 — Scaffold (current)**

- Python package layout initialized (`app/`, `demo/`, `tests/`)
- FastAPI application skeleton boots; `GET /healthz` returns `{"status": "ok"}`
- Smoke tests pass: `make test`
- All runtime and dev dependencies pinned in `requirements.txt`
- `Makefile` targets: `install`, `run`, `test`, `demo` (demo requires M2)
- MIT license and `.gitignore` in place

Pipeline code (embedder, clusterer, risk scorer, LLM summarizer, dashboard) ships in M2–M5.

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

To run the demo with synthetic data (requires M2):

```bash
make demo   # generates demo/incidents.csv — demo/generate_dataset.py ships in M2
# Then POST it via the dashboard or curl
```

## Project Layout

```
incidentlens/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI app entry point
├── demo/
│   ├── __init__.py
│   ├── .gitkeep
│   └── generate_dataset.py   # generates 500 synthetic incidents (M2)
├── tests/
│   ├── __init__.py
│   └── test_smoke.py    # import + healthz smoke test
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
| M2 | Data layer: synthetic dataset generator, CSV/JSONL ingest endpoint | <!-- TODO --> |
| M3 | Embedding + clustering: MiniLM embedder, HDBSCAN clusterer, in-memory store | <!-- TODO --> |
| M4 | Risk scoring + LLM summarizer: recency-weighted scorer, OpenAI/Ollama summarizer | <!-- TODO --> |
| M5 | Dashboard: Jinja2 risk-ranked cluster cards, `GET /clusters` endpoint | <!-- TODO --> |

## License

MIT — see [LICENSE](LICENSE).
