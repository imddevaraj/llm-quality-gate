from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .alerts import send_alert
from .db import Dataset, StoredConfig, engine, get_run, save_run
from .runner import run_evaluation
from sqlalchemy.orm import Session

app = FastAPI(title="LLM Regression Detection", version="0.1.0")


class EvaluationRequest(BaseModel):
    baseline: str
    candidate: str
    dataset: str
    repeats: int = 1


class ConfigRequest(BaseModel):
    kind: str
    name: str
    config: dict


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/datasets")
def create_dataset(name: str, path: str) -> dict[str, str]:
    with Session(engine) as session:
        item = Dataset(name=name, path=path)
        session.add(item)
        session.commit()
        return {"id": item.id, "name": item.name, "path": item.path}


@app.get("/datasets")
def list_datasets() -> list[dict[str, str]]:
    with Session(engine) as session:
        return [{"id": item.id, "name": item.name, "path": item.path} for item in session.query(Dataset).all()]


@app.post("/configs")
def create_config(request: ConfigRequest) -> dict:
    if request.kind not in {"prompt", "model", "retrieval", "tool", "policy"}:
        raise HTTPException(status_code=400, detail="unsupported config kind")
    with Session(engine) as session:
        item = StoredConfig(kind=request.kind, name=request.name, config=request.config)
        session.add(item)
        session.commit()
        return {"id": item.id, "kind": item.kind, "name": item.name, "config": item.config}


@app.get("/configs")
def list_configs(kind: str | None = None) -> list[dict]:
    with Session(engine) as session:
        query = session.query(StoredConfig)
        if kind:
            query = query.filter(StoredConfig.kind == kind)
        return [{"id": item.id, "kind": item.kind, "name": item.name, "config": item.config} for item in query.all()]


@app.put("/policies/{name}")
def configure_policy(name: str, thresholds: dict[str, float]) -> dict:
    with Session(engine) as session:
        item = session.query(StoredConfig).filter(StoredConfig.name == name).first()
        if item:
            item.config = {"thresholds": thresholds}
            item.kind = "policy"
        else:
            item = StoredConfig(kind="policy", name=name, config={"thresholds": thresholds})
            session.add(item)
        session.commit()
        return {"id": item.id, "kind": item.kind, "name": item.name, "config": item.config}


@app.post("/runs")
async def start_run(request: EvaluationRequest) -> dict:
    try:
        report = await run_evaluation(request.baseline, request.candidate, request.dataset, request.repeats)
        data = report.as_dict()
        data["run_id"] = save_run(data)
        await send_alert(report, f"/runs/{data['run_id']}/report")
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/runs/{run_id}")
def read_run(run_id: str) -> dict:
    report = get_run(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="run not found")
    return report


@app.get("/runs/{run_id}/report")
def read_report(run_id: str) -> dict:
    return read_run(run_id)
