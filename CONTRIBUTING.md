# Contributing

Thanks for contributing to LLM Regression Detection.

## Development setup

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[test,dev]'
.venv/bin/poe check
```

The `check` task runs tests, compiles the source, and validates the sample configuration and dataset without making LLM provider calls.

## Pull requests

- Keep changes focused and explain behavior changes in the pull request description.
- Add or update tests for changed behavior.
- Do not commit API keys, webhook URLs, local databases, reports, or generated environments.
- Run `.venv/bin/poe check` before opening a pull request.
- For provider-facing changes, include mocked tests so CI does not require credentials.

## Commit messages

Use concise imperative messages, for example `Add dataset schema validation`.
