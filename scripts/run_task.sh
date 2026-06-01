#!/bin/bash
# Generic task runner for mimir-webwright.
# Usage: run_task.sh <task-name> [extra args...]
set -e

TASK=$1
if [ -z "$TASK" ]; then
    echo "Usage: $0 <task-name> [args...]" >&2
    exit 1
fi

REPO_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"
VENV_PYTHON="$REPO_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "ERROR: venv not found at $REPO_DIR/.venv — run: pip install -e . inside the venv" >&2
    exit 1
fi

exec "$VENV_PYTHON" -m mimir_webwright.cli run --task "$TASK" "${@:2}"
