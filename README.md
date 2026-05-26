# mimir-webwright

Webwright-inspired, terminal-native web automation harness for Mimir.

It keeps the artifact-first workflow from Microsoft Webwright:
- generate or reuse Playwright scripts in `workspace/scripts/`
- execute them in disposable browser sessions
- persist logs, screenshots, JSON, and CSV under `workspace/runs/<timestamp>/`

## Features

- LiteLLM/OpenAI-compatible model adapter pointing to `http://localhost:4000`
- Reusable runner loop for `plan -> script -> execute -> observe`
- First task: `pisos-scraper` for Pisos.com Madrid rentals
- Outputs both JSON and CSV
- Strict typing, pytest, ruff, mypy, GitHub Actions CI

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
playwright install chromium
export LITELLM_API_KEY=...
mimir-webwright pisos-scraper --zone madrid --max-price 1100 --min-rooms 2 --max-rooms 3
```

Artifacts are written to:

- `workspace/scripts/pisos_com_madrid.py`
- `workspace/runs/<timestamp>/results.json`
- `workspace/runs/<timestamp>/results.csv`
- `workspace/runs/<timestamp>/run.log`
- `workspace/runs/<timestamp>/screenshots/`

## CLI

```bash
mimir-webwright pisos-scraper --help
mimir-webwright run-task pisos-scraper
```

## Configuration

Environment variables:

- `LITELLM_BASE_URL` (default: `http://localhost:4000/v1`)
- `LITELLM_API_KEY` (required for model calls)
- `LITELLM_MODEL` (default: `litellm/gpt-5.4`)
- `MIMIR_WEBWRIGHT_HEADLESS` (`true` by default)

## Notes

- The current `pisos-scraper` task ships with a checked-in reusable Playwright script template so it can run deterministically from CI/dev machines.
- The LiteLLM adapter is ready for future task-planning flows, even though the first task uses a curated prompt + reusable script path rather than autonomous script synthesis.
- Web scraping targets can change their DOM at any time; selectors are isolated in one script file to keep maintenance surgical.
