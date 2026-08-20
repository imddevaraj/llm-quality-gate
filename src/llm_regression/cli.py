import asyncio
import json
from pathlib import Path

import typer

from .alerts import send_alert
from .db import save_run, get_run
from .runner import load_config, load_dataset, run_evaluation

app = typer.Typer(no_args_is_help=True)


@app.command()
def run(
    baseline: str = typer.Option(..., help="Baseline YAML configuration."),
    candidate: str = typer.Option(..., help="Candidate YAML configuration."),
    dataset: str = typer.Option(..., help="Golden JSONL dataset."),
    repeats: int = typer.Option(1, min=1),
    output: str = typer.Option("json", help="Report format: json or markdown."),
) -> None:
    """Evaluate baseline and candidate configs against a JSONL dataset."""
    try:
        report = asyncio.run(run_evaluation(baseline, candidate, dataset, repeats))
    except Exception as exc:
        typer.echo(f"execution error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    data = report.as_dict()
    data["run_id"] = save_run(data)
    asyncio.run(send_alert(report))
    if output == "markdown":
        typer.echo(f"## LLM regression report: {data['status']}\n\n- Feature: {data['feature_name']}\n- Quality delta: {data['metrics'].get('quality_delta', 0):.3f}\n- Failures: {len(data['failures'])}")
    else:
        typer.echo(json.dumps(data, indent=2))
    exit_code = 0 if data["status"] == "PASS" else 2 if data["status"] == "ERROR" else 1
    raise typer.Exit(code=exit_code)


@app.command()
def validate(
    config: str = typer.Option(..., help="YAML configuration to validate."),
    dataset: str = typer.Option(..., help="Golden JSONL dataset to validate."),
) -> None:
    """Validate an evaluation config and JSONL dataset without calling an LLM."""
    try:
        load_config(config)
        cases = load_dataset(dataset)
    except Exception as exc:
        typer.echo(f"validation error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"valid: {config} ({len(cases)} cases from {dataset})")


@app.command()
def report(run_id: str) -> None:
    """Print a saved evaluation report."""
    data = get_run(run_id)
    if not data:
        raise typer.BadParameter("run not found")
    typer.echo(json.dumps(data, indent=2))


if __name__ == "__main__":
    app()
