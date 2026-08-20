from llm_regression.evaluators import evaluate_case


def test_evaluate_case_runs_deterministic_checks():
    score, metrics, failures = evaluate_case(
        '{"label":"billing","answer":"Contact support"}',
        {
            "checks": {
                "required_terms": ["billing", "support"],
                "json_schema": {
                    "type": "object",
                    "required": ["label", "answer"],
                },
                "max_latency_ms": 500,
                "max_tokens": 100,
            },
        },
        latency_ms=100,
        total_tokens=20,
    )
    assert score == 1.0
    assert metrics["json_validity"] == 1.0
    assert failures == []


def test_evaluate_case_reports_failures():
    score, _, failures = evaluate_case("nope", {"expected_output": "yes"}, 10, 2)
    assert score == 0.0
    assert "exact match failed" in failures
