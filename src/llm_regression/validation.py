import json
import re
from typing import Any

from jsonschema import SchemaError, validators


class ValidationError(ValueError):
    """Raised when an evaluation input cannot be executed safely."""


def validate_config(config: dict[str, Any], source: str = "config") -> None:
    provider = config.get("provider")
    if not isinstance(provider, dict):
        raise ValidationError(f"{source}: provider must be an object")
    for key in ("model", "prompt"):
        if not provider.get(key):
            raise ValidationError(f"{source}: provider.{key} is required")
    if not isinstance(provider.get("temperature", 0), (int, float)) or not 0 <= provider.get("temperature", 0) <= 2:
        raise ValidationError(f"{source}: provider.temperature must be between 0 and 2")
    if config.get("judge"):
        judge = config["judge"]
        if not isinstance(judge, dict) or not judge.get("model"):
            raise ValidationError(f"{source}: judge.model is required")
        minimum_score = judge.get("minimum_score", 0.7)
        if not isinstance(minimum_score, (int, float)) or not 0 <= minimum_score <= 1:
            raise ValidationError(f"{source}: judge.minimum_score must be between 0 and 1")
    thresholds = config.get("policy", {}).get("thresholds", {})
    for name, value in thresholds.items():
        if not isinstance(value, (int, float)) or value < 0:
            raise ValidationError(f"{source}: policy threshold {name} must be a non-negative number")


def validate_dataset(cases: list[dict[str, Any]], source: str = "dataset") -> None:
    if not cases:
        raise ValidationError(f"{source}: must contain at least one case")
    seen: set[str] = set()
    allowed_severity = {"normal", "high", "critical"}
    for index, case in enumerate(cases, start=1):
        prefix = f"{source}: line {index}"
        for key in ("id", "feature_name", "input"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                raise ValidationError(f"{prefix}: {key} is required")
        if case["id"] in seen:
            raise ValidationError(f"{prefix}: duplicate id {case['id']}")
        seen.add(case["id"])
        if case.get("severity", "normal") not in allowed_severity:
            raise ValidationError(f"{prefix}: severity must be normal, high, or critical")
        checks = case.get("checks", {})
        if not isinstance(checks, dict):
            raise ValidationError(f"{prefix}: checks must be an object")
        if "regex" in checks:
            try:
                re.compile(checks["regex"])
            except re.error as exc:
                raise ValidationError(f"{prefix}: invalid regex: {exc}") from exc
        if "json_schema" in checks:
            try:
                validators.validator_for(checks["json_schema"]).check_schema(checks["json_schema"])
            except SchemaError as exc:
                raise ValidationError(f"{prefix}: invalid JSON schema: {exc.message}") from exc
        if "required_terms" in checks and not isinstance(checks["required_terms"], list):
            raise ValidationError(f"{prefix}: required_terms must be a list")
        if "expected_output" not in case and "evaluation_rubric" not in case and not checks:
            raise ValidationError(f"{prefix}: expected_output, evaluation_rubric, or checks is required")


def load_jsonl(path: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValidationError(f"dataset: line {index}: invalid JSON: {exc.msg}") from exc
                if not isinstance(value, dict):
                    raise ValidationError(f"dataset: line {index}: case must be an object")
                cases.append(value)
    except OSError as exc:
        raise ValidationError(f"dataset: cannot read {path}: {exc}") from exc
    validate_dataset(cases, path)
    return cases
