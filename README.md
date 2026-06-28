# IncidentLens — Emerging Risk Clusters from Incident Streams

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Every team drowns in incident tickets. Manual review is too slow to catch emerging patterns, and keyword search is too brittle for noisy, free-form text. IncidentLens uses sentence embeddings and clustering to automatically surface **risk clusters** from your incident stream, then calls an LLM to write a crisp, human-readable summary of each cluster.

## Status

**M5 — FastAPI backend + HTML dashboard (current)**

- `POST /ingest` — upload a CSV or JSONL file; runs the full pipeline (load → embed → cluster → summarize) and stores results in-memory
- `GET /clusters` — returns risk-ranked `ClusterSummary` list as JSON
- `GET /` — Jinja2 dashboard showing risk-ranked cluster cards with theme, score badge, risk description, and sample incidents
- `GET /health` (and `/healthz` alias) — health check endpoint
- `app/templates/dashboard.html` — plain HTML + inline CSS, no JS framework, no CDN

M4 (LLM summarizer): `summarize_cluster()` via OpenAI/Ollama, centroid-keyed in-memory cache.
M3 (embedding + clustering): MiniLM embedder, HDBSCAN clusterer, recency-weighted risk scorer.
M2 (data layer): synthetic dataset generator, CSV/JSONL ingest, Pydantic model.
M1 (scaffold): Python package layout, FastAPI skeleton, `GET /healthz`, pinned deps.

## Architecture

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

To ingest data and view results:

```bash
make demo   # writes demo/incidents.csv (500 rows, 8 risk themes)

# Upload and run the full pipeline
curl -X POST http://localhost:8000/ingest \
     -F "file=@demo/incidents.csv"
# {"ingested": 500, "clusters": 8}

# View risk-ranked clusters as JSON
curl http://localhost:8000/clusters

# Or open the HTML dashboard
open http://localhost:8000
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
│   ├── main.py          # FastAPI app — /ingest, /clusters, / dashboard (M5)
│   ├── models.py        # Incident, ClusterSummary Pydantic v2 models (M2, M4)
│   ├── ingestion.py     # load_incidents(CSV/JSONL)   (M2)
│   ├── embedder.py      # embed(incidents) → ndarray  (M3)
│   ├── clusterer.py     # cluster() → ClusterResult[] (M3)
│   ├── summarizer.py    # summarize_cluster() → ClusterSummary (M4)
│   └── templates/
│       └── dashboard.html   # Jinja2 risk-ranked cluster cards (M5)
├── demo/
│   ├── __init__.py
│   ├── .gitkeep
│   └── generate_dataset.py   # 500 synthetic incidents (M2)
├── tests/
│   ├── __init__.py
│   ├── test_smoke.py         # M5 endpoint tests: /health, /clusters, /ingest, dashboard
│   ├── test_ingestion.py     # generator + ingestion tests (M2)
│   ├── test_clustering.py    # embedder + clusterer tests  (M3)
│   └── test_summarizer.py    # summarizer tests, OpenAI mocked (M4)
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
| M4 | LLM summarizer: OpenAI/Ollama cluster summarizer, centroid-keyed cache, `ClusterSummary` model | done |
| M5 | FastAPI backend: `POST /ingest`, `GET /clusters`, Jinja2 risk dashboard | done |

## License

MIT — see [LICENSE](LICENSE).
