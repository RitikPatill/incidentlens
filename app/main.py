import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from app.models import ClusterSummary
from app.ingestion import load_incidents
from app.embedder import embed
from app.clusterer import cluster
from app.summarizer import summarize_cluster

app = FastAPI(title="IncidentLens")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

_state: list[ClusterSummary] = []


@app.get("/health")
def health():
    return {"status": "ok"}


app.add_api_route("/healthz", health)


def _run_pipeline(contents: bytes, filename: str) -> tuple[list[ClusterSummary], int]:
    """Run full pipeline. Returns (summaries, incident_count)."""
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(contents)
        tmp = f.name
    try:
        incidents = load_incidents(tmp)
        if not incidents:
            return [], 0
        embeddings = embed(incidents)
        results = cluster(incidents, embeddings)
        id_to_idx = {inc.id: i for i, inc in enumerate(incidents)}
        id_to_inc = {inc.id: inc for inc in incidents}
        summaries = []
        for cr in results:
            idxs = [id_to_idx[iid] for iid in cr.incident_ids]
            centroid = embeddings[idxs].mean(axis=0)
            members = [id_to_inc[iid] for iid in cr.incident_ids]
            summaries.append(summarize_cluster(cr, members, centroid))
        return summaries, len(incidents)
    finally:
        os.unlink(tmp)


@app.post("/ingest")
def ingest(file: UploadFile = File(...)) -> dict:
    global _state
    contents = file.file.read()
    summaries, n_incidents = _run_pipeline(contents, file.filename or "upload.csv")
    _state = summaries
    return {"ingested": n_incidents, "clusters": len(summaries)}


@app.get("/clusters")
def get_clusters() -> list[ClusterSummary]:
    return _state


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    clusters = [c.model_dump() for c in _state]
    ingested_count = sum(c["size"] for c in clusters)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"clusters": clusters, "ingested_count": ingested_count},
    )
