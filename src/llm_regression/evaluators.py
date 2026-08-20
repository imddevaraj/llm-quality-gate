import json
import re
from typing import Any

from jsonschema import ValidationError, validate


def exact_match(output: str, expected: str) -> tuple[float, str | None]:
    ok = output.strip() == expected.strip()
    return float(ok), None if ok else "exact match failed"


def contains_terms(output: str, terms: list[str]) -> tuple[float, str | None]:
    missing = [term for term in terms if term.lower() not in output.lower()]
    return (1.0 if not missing else 0.0, None if not missing else f"missing terms: {', '.join(missing)}")


def regex_match(output: str, pattern: str) -> tuple[float, str | None]:
    ok = re.search(pattern, output) is not None
    return float(ok), None if ok else "regex validation failed"


def json_schema_valid(output: str, schema: dict[str, Any]) -> tuple[float, str | None]:
    try:
        validate(json.loads(output), schema)
    except (json.JSONDecodeError, ValidationError) as exc:
        return 0.0, f"JSON schema validation failed: {exc.message if hasattr(exc, 'message') else exc}"
    return 1.0, None


def latency_score(latency_ms: float, maximum_ms: float) -> tuple[float, str | None]:
    ok = latency_ms <= maximum_ms
    return (1.0 if ok else 0.0, None if ok else f"latency {latency_ms:.0f}ms exceeds {maximum_ms:.0f}ms")


def cost_score(total_tokens: int, maximum_tokens: int) -> tuple[float, str | None]:
    ok = total_tokens <= maximum_tokens
    return (1.0 if ok else 0.0, None if ok else f"token usage {total_tokens} exceeds {maximum_tokens}")


def evaluate_case(output: str, case: dict[str, Any], latency_ms: float, total_tokens: int) -> tuple[float, dict[str, float], list[str]]:
    checks = case.get("checks", {})
    metrics: dict[str, float] = {}
    failures: list[str] = []
    if "expected_output" in case:
        score, failure = exact_match(output, str(case["expected_output"]))
        metrics["exact_match"] = score
        if failure:
            failures.append(failure)
    if "required_terms" in checks:
        score, failure = contains_terms(output, checks["required_terms"])
        metrics["contains_terms"] = score
        if failure:
            failures.append(failure)
    if "regex" in checks:
        score, failure = regex_match(output, checks["regex"])
        metrics["regex"] = score
        if failure:
            failures.append(failure)
    if "json_schema" in checks:
        score, failure = json_schema_valid(output, checks["json_schema"])
        metrics["json_validity"] = score
        if failure:
            failures.append(failure)
    if "max_latency_ms" in checks:
        score, failure = latency_score(latency_ms, checks["max_latency_ms"])
        metrics["latency"] = score
        if failure:
            failures.append(failure)
    if "max_tokens" in checks:
        score, failure = cost_score(total_tokens, checks["max_tokens"])
        metrics["cost"] = score
        if failure:
            failures.append(failure)
    return (sum(metrics.values()) / len(metrics) if metrics else 1.0, metrics, failures)
