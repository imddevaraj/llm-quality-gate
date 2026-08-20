import json
import os
from statistics import median, pvariance
from typing import Any

import yaml

from .domain import CaseResult, EvaluationReport, Status
from .evaluators import evaluate_case
from .judge import semantic_judge
from .policy import compare_reports
from .providers import OpenAICompatibleProvider, ProviderConfig
from .validation import load_jsonl, validate_config


def load_config(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if not isinstance(config, dict):
        raise ValueError(f"{path}: configuration must be an object")
    validate_config(config, path)
    return config


def load_dataset(path: str) -> list[dict[str, Any]]:
    return load_jsonl(path)


async def evaluate_config(config: dict[str, Any], cases: list[dict[str, Any]], repeats: int = 1) -> EvaluationReport:
    provider_cfg = ProviderConfig(**config["provider"])
    api_key = os.getenv(config["provider"].get("api_key_env", "OPENAI_API_KEY"), "")
    provider = OpenAICompatibleProvider(provider_cfg, api_key)
    judge_provider = None
    if config.get("judge"):
        provider_keys = {"model", "prompt", "temperature", "max_tokens", "base_url", "api_key_env"}
        judge_cfg = ProviderConfig(**{key: value for key, value in config["judge"].items() if key in provider_keys})
        judge_key = os.getenv(config["judge"].get("api_key_env", "OPENAI_API_KEY"), "")
        judge_provider = OpenAICompatibleProvider(judge_cfg, judge_key)
    results: list[CaseResult] = []
    for case in cases:
        runs: list[CaseResult] = []
        for _ in range(repeats):
            try:
                prompt = provider_cfg.prompt.format(input=case["input"])
                generation = await provider.generate(prompt)
                score, metrics, failures = evaluate_case(generation.text, case, generation.latency_ms, generation.total_tokens)
                if judge_provider and case.get("evaluation_rubric"):
                    judge_score, judge_reason = await semantic_judge(judge_provider, case["evaluation_rubric"], case["input"], generation.text)
                    metrics["semantic_quality"] = judge_score
                    score = sum(metrics.values()) / len(metrics)
                    if judge_score < float(config["judge"].get("minimum_score", 0.7)):
                        failures.append(judge_reason or "semantic judge score below minimum")
                runs.append(CaseResult(case["id"], case["feature_name"], Status.PASS if not failures else Status.WARNING, score, score, 0, metrics, failures, latency_ms=generation.latency_ms, total_tokens=generation.total_tokens, output=generation.text, tags=case.get("tags", []), severity=case.get("severity", "normal")))
            except Exception as exc:
                runs.append(CaseResult(case["id"], case["feature_name"], Status.ERROR, None, None, None, error=str(exc), tags=case.get("tags", []), severity=case.get("severity", "normal")))
        valid = [item for item in runs if item.candidate_score is not None]
        if not valid:
            results.append(runs[-1])
            continue
        selected = valid[0]
        selected.candidate_score = median([item.candidate_score for item in valid])
        selected.latency_ms = median([item.latency_ms for item in valid if item.latency_ms is not None])
        if len(valid) > 1 and pvariance([item.candidate_score for item in valid]) > 0.01:
            selected.status = Status.FLAKY
            selected.failures.append("score variance exceeds 0.01")
        results.append(selected)
    feature = cases[0]["feature_name"] if cases else "unknown"
    return EvaluationReport(Status.PASS, feature, results, {}, [])


async def run_evaluation(baseline_path: str, candidate_path: str, dataset_path: str, repeats: int = 1) -> EvaluationReport:
    cases = load_dataset(dataset_path)
    baseline = await evaluate_config(load_config(baseline_path), cases, repeats)
    candidate_config = load_config(candidate_path)
    candidate = await evaluate_config(candidate_config, cases, repeats)
    candidate.git_sha = os.getenv("GITHUB_SHA") or os.getenv("GIT_SHA")
    candidate.branch = os.getenv("GITHUB_REF_NAME") or os.getenv("GIT_BRANCH")
    candidate.baseline_model = load_config(baseline_path)["provider"]["model"]
    candidate.candidate_model = candidate_config["provider"]["model"]
    return compare_reports(baseline, candidate, candidate_config.get("policy", {}))
