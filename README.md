# IncidentLens — Emerging Risk Clusters from Incident Streams

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Every team drowns in incident tickets. Manual review is too slow to catch emerging patterns, and keyword search is too brittle for noisy, free-form text. IncidentLens uses sentence embeddings and clustering to automatically surface **risk clusters** from your incident stream, then calls an LLM to write a crisp, human-readable summary of each cluster.

## Status

**M4 — LLM summarizer (current)**

- `app/summarizer.py` — `summarize_cluster(cluster, members, centroid)` calls `gpt-4o-mini` via the OpenAI chat completions API and returns a `ClusterSummary` with a theme (≤6 words), a one-sentence risk description, and the top 3 incident titles
- Set `OPENAI_BASE_URL=http://localhost:11434/v1` (and `OPENAI_API_KEY=ollama`) to route requests through a local Ollama instance instead
- Summaries are cached in-process, keyed by SHA-256 hash of the cluster centroid, so repeated calls for the same cluster avoid redundant API round-trips
- `app/models.py` now exports `ClusterSummary` (Pydantic v2 model added in M4)
- All tests pass: `pytest tests/ -v -m "not slow"` (OpenAI calls are mocked in `test_summarizer.py`)

M3 (embedding + clustering): MiniLM embedder, HDBSCAN clusterer, recency-weighted risk scorer.
M2 (data layer): synthetic dataset generator, CSV/JSONL ingest, Pydantic model.
M1 (scaffold): Python package layout, FastAPI skeleton, `GET /healthz`, pinned deps.

Dashboard ships in M5.

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
│   ├── models.py        # Incident, ClusterSummary Pydantic v2 models (M2, M4)
│   ├── ingestion.py     # load_incidents(CSV/JSONL)   (M2)
│   ├── embedder.py      # embed(incidents) → ndarray  (M3)
│   ├── clusterer.py     # cluster() → ClusterResult[] (M3)
│   └── summarizer.py    # summarize_cluster() → ClusterSummary (M4)
├── demo/
│   ├── __init__.py
│   ├── .gitkeep
│   └── generate_dataset.py   # 500 synthetic incidents (M2)
├── tests/
│   ├── __init__.py
│   ├── test_smoke.py         # healthz smoke test
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
| M5 | Dashboard: Jinja2 risk-ranked cluster cards, `GET /clusters` endpoint | <!-- TODO --> |

## License

MIT — see [LICENSE](LICENSE).
