# IncidentLens — LLM-Powered Risk Discovery from Noisy Incident Streams

> Cluster noisy support tickets or system alerts, surface emerging risk patterns, and get LLM-written summaries — all locally.

<!-- TODO: replace with a 5-10 second demo gif. Record with ScreenToGif on
     Windows or peek on macOS. Save to docs/demo.gif and update path here. -->
![demo](docs/demo.gif)

## What it is

IncidentLens ingests a CSV or JSONL file of customer support tickets, system alerts, or any free-form incident text and automatically groups them into semantically coherent risk clusters. Each cluster is scored by volume and recency, then passed to an LLM (OpenAI or a local Ollama model) to produce a plain-English summary of what the cluster is about and why it might warrant attention.

The pipeline runs entirely on CPU. No GPU, no proprietary data pipeline, no persistent database — just a FastAPI server that holds results in memory for the duration of the session. The included synthetic dataset of 500 fictional incidents lets you run a full end-to-end demo in under a minute.

## Quickstart

```bash
git clone https://github.com/RitikPatill/incidentlens.git
cd incidentlens

pip install -r requirements.txt

# Set your LLM credentials (or point at a local Ollama instance — see below)
export OPENAI_API_KEY=sk-...

# Start the server
uvicorn app.main:app --reload
# Open http://localhost:8000
```

To run the full demo:

```bash
make demo                      # generates demo/incidents.csv (500 rows, 8 risk themes)

curl -X POST http://localhost:8000/ingest \
     -F "file=@demo/incidents.csv"
# {"ingested": 500, "clusters": 8}

# Risk-ranked clusters as JSON
curl http://localhost:8000/clusters

# Or open the HTML dashboard
open http://localhost:8000      # macOS; use xdg-open on Linux, start on Windows
```

**Ollama (fully local, no API key):**

```bash
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama   # any non-empty string
uvicorn app.main:app --reload
```

## Usage

Upload any CSV or JSONL file that has at least an `id`, `title`, `description`, and `timestamp` column via `POST /ingest`. The server embeds every row with MiniLM, clusters with HDBSCAN, scores each cluster, and calls the LLM once per cluster. Results are available immediately at `GET /clusters` as a JSON array sorted by risk score descending.

The HTML dashboard at `GET /` shows the same data as risk-ranked cards — each card displays the cluster theme, risk score badge, LLM-written description, and three representative sample incidents. No page reload is needed between ingests; the in-memory state is replaced on each `POST /ingest` call.

Run the smoke tests:

```bash
make test
```

## Architecture

```
CSV / JSONL
    │
    ▼
Embedder (MiniLM-L6-v2, CPU)
    │  384-dim sentence vectors
    ▼
Clusterer (HDBSCAN or KMeans)
    │  cluster assignments
    ▼
Risk Scorer  (size × recency decay)
    │  scored ClusterResult[]
    ▼
LLM Summarizer  (OpenAI / Ollama)
    │  ClusterSummary[]
    ▼
FastAPI  ─── POST /ingest
         ─── GET  /clusters  (JSON)
         ─── GET  /          (Jinja2 dashboard)
```

## Project structure

```
incidentlens/
├── app/                    # FastAPI application package
│   ├── main.py             # route handlers: /ingest, /clusters, / dashboard
│   ├── models.py           # Pydantic v2 models: Incident, ClusterSummary
│   ├── ingestion.py        # CSV/JSONL loader
│   ├── embedder.py         # MiniLM sentence embeddings → ndarray
│   ├── clusterer.py        # HDBSCAN/KMeans + risk scoring
│   ├── summarizer.py       # LLM summarization with centroid-keyed cache
│   └── templates/
│       └── dashboard.html  # plain HTML + inline CSS, no JS framework
├── demo/
│   └── generate_dataset.py # synthetic 500-row incident dataset
├── tests/                  # pytest suite (smoke, ingestion, clustering, summarizer)
├── requirements.txt        # pinned runtime + dev deps
├── Makefile                # install / run / demo / test / gif targets
└── LICENSE                 # MIT
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | API key for OpenAI or any OpenAI-compatible provider |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Override to use a local [Ollama](https://ollama.com) instance |
| `N_CLUSTERS` | `8` | KMeans cluster count (ignored when HDBSCAN is used) |

## Roadmap

- [ ] Streaming ingest: accept newline-delimited JSON over a persistent connection instead of full-file upload
- [ ] Incremental re-clustering: add new incidents to an existing session without re-embedding the full corpus
- [ ] Trend detection: track cluster risk scores across multiple ingest runs and flag clusters whose score is rising
- [ ] Export: `GET /clusters.csv` and `GET /clusters.json` download endpoints
- [ ] Configurable embedding model: swap MiniLM for a larger model via an environment variable

## License

MIT — see [LICENSE](LICENSE).

---

Built autonomously by [autodev](https://github.com/RitikPatill/autodev),
a multi-agent orchestrator I designed. Each commit in this repo was
authored by me; the implementation work was performed by Sonnet under
the orchestrator's control. Read the orchestrator's README to see how.
