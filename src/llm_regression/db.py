from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .config import settings


class Base(DeclarativeBase):
    pass


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(20), default="ERROR")
    feature_name: Mapped[str] = mapped_column(String(200))
    git_sha: Mapped[str | None] = mapped_column(String(100))
    branch: Mapped[str | None] = mapped_column(String(200))
    report: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), unique=True)
    path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StoredConfig(Base):
    __tablename__ = "stored_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200), unique=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


engine = create_engine(settings.database_url, future=True)
Base.metadata.create_all(engine)


def save_run(report: dict[str, Any]) -> str:
    with Session(engine) as session:
        run = EvaluationRun(feature_name=report["feature_name"], status=report["status"], git_sha=report.get("git_sha"), branch=report.get("branch"), report=report)
        session.add(run)
        session.commit()
        return run.id


def get_run(run_id: str) -> dict[str, Any] | None:
    with Session(engine) as session:
        run = session.scalar(select(EvaluationRun).where(EvaluationRun.id == run_id))
        return {"id": run.id, **run.report} if run else None
