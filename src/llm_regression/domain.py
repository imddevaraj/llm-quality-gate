from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    PASS = "PASS"
    REGRESSION = "REGRESSION"
    WARNING = "WARNING"
    FLAKY = "FLAKY"
    ERROR = "ERROR"


@dataclass
class Generation:
    text: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = "unknown"

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class CaseResult:
    case_id: str
    feature_name: str
    status: Status
    baseline_score: float | None
    candidate_score: float | None
    score_delta: float | None
    metrics: dict[str, float] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    error: str | None = None
    latency_ms: float | None = None
    total_tokens: int | None = None
    output: str | None = None
    tags: list[str] = field(default_factory=list)
    severity: str = "normal"


@dataclass
class EvaluationReport:
    status: Status
    feature_name: str
    case_results: list[CaseResult]
    metrics: dict[str, float]
    failures: list[str]
    git_sha: str | None = None
    branch: str | None = None
    baseline_model: str | None = None
    candidate_model: str | None = None
    run_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "feature_name": self.feature_name,
            "run_id": self.run_id,
            "git_sha": self.git_sha,
            "branch": self.branch,
            "baseline_model": self.baseline_model,
            "candidate_model": self.candidate_model,
            "metrics": self.metrics,
            "failures": self.failures,
            "cases": [
                {**result.__dict__, "status": result.status.value}
                for result in self.case_results
            ],
        }
