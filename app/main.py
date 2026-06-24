from fastapi import FastAPI

app = FastAPI(title="IncidentLens")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
