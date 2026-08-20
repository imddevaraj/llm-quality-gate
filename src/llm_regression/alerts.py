from typing import Any

import httpx

from .config import settings
from .domain import EvaluationReport
from .redaction import redact


async def send_alert(report: EvaluationReport, report_url: str | None = None) -> None:
    if report.status.value not in {"REGRESSION", "ERROR"}:
        return
    details = redact("\n".join(report.failures), settings.redaction_patterns)
    text = f"LLM regression: {report.feature_name}\nStatus: {report.status.value}\nGit SHA: {report.git_sha or 'unknown'}\nModels: {report.baseline_model} -> {report.candidate_model}\nFailures:\n{details}\nReport: {report_url or 'local CLI output'}"
    urls: list[tuple[str, dict[str, Any]]] = []
    if settings.slack_webhook_url:
        urls.append((settings.slack_webhook_url, {"text": text}))
    if settings.teams_webhook_url:
        urls.append((settings.teams_webhook_url, {"text": text}))
    async with httpx.AsyncClient(timeout=15) as client:
        for url, payload in urls:
            try:
                await client.post(url, json=payload)
            except httpx.HTTPError:
                continue
