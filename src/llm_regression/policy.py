from statistics import median, quantiles
from typing import Any

from .domain import CaseResult, EvaluationReport, Status


def _median_metric(results: list[CaseResult], name: str) -> float:
    values = [item.metrics[name] for item in results if name in item.metrics]
    return float(median(values)) if values else 0.0


def _median_score(results: list[CaseResult]) -> float:
    values = [item.candidate_score for item in results if item.candidate_score is not None]
    return float(median(values)) if values else 0.0


def _median_tokens(results: list[CaseResult]) -> float:
    values = [item.total_tokens for item in results if item.total_tokens is not None]
    return float(median(values)) if values else 0.0


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) < 2:
        return values[0]
    return float(quantiles(values, n=100, method="inclusive")[94])


def compare_reports(baseline: EvaluationReport, candidate: EvaluationReport, policy: dict[str, Any]) -> EvaluationReport:
    thresholds = policy.get("thresholds", {})
    case_results: list[CaseResult] = []
    failures: list[str] = []
    all_features = candidate.feature_name
    for result in candidate.case_results:
        before = next((item for item in baseline.case_results if item.case_id == result.case_id), None)
        baseline_score = before.candidate_score if before else None
        candidate_score = result.candidate_score
        delta = round(candidate_score - baseline_score, 4) if baseline_score is not None and candidate_score is not None else None
        status = result.status
        if result.error:
            status = Status.ERROR
        elif result.severity == "critical" and result.failures:
            status = Status.REGRESSION
        elif delta is not None and delta < -float(thresholds.get("quality_drop", 0.03)):
            status = Status.REGRESSION
        elif result.failures:
            status = Status.WARNING
        if status in {Status.REGRESSION, Status.ERROR}:
            failures.append(f"{result.case_id}: {', '.join(result.failures) or result.error or 'regression'}")
        case_results.append(CaseResult(**{**result.__dict__, "baseline_score": baseline_score, "score_delta": delta, "status": status}))
    baseline_quality = _median_score(baseline.case_results)
    candidate_quality = _median_score(candidate.case_results)
    baseline_latency = _p95([item.latency_ms for item in baseline.case_results if item.latency_ms is not None])
    candidate_latency = _p95([item.latency_ms for item in candidate.case_results if item.latency_ms is not None])
    baseline_cost = _median_tokens(baseline.case_results)
    candidate_cost = _median_tokens(candidate.case_results)
    baseline_json = _median_metric(baseline.case_results, "json_validity")
    candidate_json = _median_metric(candidate.case_results, "json_validity")
    metrics = {
        "baseline_quality": baseline_quality,
        "candidate_quality": candidate_quality,
        "quality_delta": round(candidate_quality - baseline_quality, 4),
        "baseline_json_validity": baseline_json,
        "candidate_json_validity": candidate_json,
        "baseline_p95_latency_ms": baseline_latency,
        "candidate_p95_latency_ms": candidate_latency,
        "baseline_cost": baseline_cost,
        "candidate_cost": candidate_cost,
    }
    quality_drop = float(thresholds.get("quality_drop", 0.03))
    json_minimum = thresholds.get("json_validity_min")
    latency_increase = thresholds.get("p95_latency_increase")
    cost_increase = thresholds.get("cost_increase")
    if candidate_quality < baseline_quality - quality_drop:
        failures.append(f"quality dropped by more than {quality_drop:.2%}")
    if json_minimum is not None and candidate_json < float(json_minimum):
        failures.append(f"JSON validity {candidate_json:.2%} is below {float(json_minimum):.2%}")
    if latency_increase is not None and baseline_latency and candidate_latency > baseline_latency * (1 + float(latency_increase)):
        failures.append(f"p95 latency increased beyond {float(latency_increase):.2%}")
    if cost_increase is not None and baseline_cost and candidate_cost > baseline_cost * (1 + float(cost_increase)):
        failures.append(f"cost increased beyond {float(cost_increase):.2%}")
    status = Status.ERROR if any(item.status == Status.ERROR for item in case_results) else Status.REGRESSION if failures else Status.PASS
    if any(x.status == Status.FLAKY for x in case_results):
        status = Status.FLAKY if status == Status.PASS else status
    return EvaluationReport(status=status, feature_name=all_features, case_results=case_results, metrics=metrics, failures=failures, git_sha=candidate.git_sha, branch=candidate.branch, baseline_model=baseline.baseline_model, candidate_model=candidate.candidate_model)
