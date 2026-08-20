from llm_regression.domain import CaseResult, EvaluationReport, Status
from llm_regression.policy import compare_reports


def test_policy_marks_quality_drop_as_regression():
    baseline = EvaluationReport(Status.PASS, "support", [CaseResult("1", "support", Status.PASS, 1.0, 1.0, 0, {})], {}, [])
    candidate = EvaluationReport(Status.PASS, "support", [CaseResult("1", "support", Status.PASS, 0.9, 0.9, 0, {})], {}, [])
    report = compare_reports(baseline, candidate, {"thresholds": {"quality_drop": 0.03}})
    assert report.status == Status.REGRESSION
    assert report.case_results[0].score_delta == -0.1


def test_policy_blocks_json_validity_and_latency_thresholds():
    baseline = EvaluationReport(
        Status.PASS,
        "support",
        [CaseResult("1", "support", Status.PASS, 1.0, 1.0, 0, {"json_validity": 1.0}, latency_ms=100)],
        {},
        [],
    )
    candidate = EvaluationReport(
        Status.PASS,
        "support",
        [CaseResult("1", "support", Status.PASS, 0.95, 0.95, 0, {"json_validity": 0.0}, latency_ms=150)],
        {},
        [],
    )
    report = compare_reports(
        baseline,
        candidate,
        {"thresholds": {"json_validity_min": 0.99, "p95_latency_increase": 0.2}},
    )
    assert report.status == Status.REGRESSION
    assert any("JSON validity" in failure for failure in report.failures)
    assert any("p95 latency" in failure for failure in report.failures)


def test_policy_blocks_token_cost_increase():
    baseline = EvaluationReport(
        Status.PASS,
        "support",
        [CaseResult("1", "support", Status.PASS, 1.0, 1.0, 0, {}, total_tokens=100)],
        {},
        [],
    )
    candidate = EvaluationReport(
        Status.PASS,
        "support",
        [CaseResult("1", "support", Status.PASS, 1.0, 1.0, 0, {}, total_tokens=130)],
        {},
        [],
    )
    report = compare_reports(baseline, candidate, {"thresholds": {"cost_increase": 0.15}})
    assert report.status == Status.REGRESSION
    assert any("cost increased" in failure for failure in report.failures)
