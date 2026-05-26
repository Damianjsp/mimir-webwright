"""CLI entry point for mimir-webwright tasks.

Provides ``python -m mimir_webwright.cli run --task <name>`` used by
the systemd services and the ``scripts/run_task.sh`` wrapper.

Supported tasks
---------------
- ``pisos``     — Pisos.com rental listing scraper (runs the full runner loop)
- ``football``  — Football odds scraper (placeholder; activates when the
                  football-odds task PR is merged)
"""
from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from mimir_webwright.runner import Runner

# Human-readable task prompts sent to the Runner loop.
_TASK_PROMPTS: dict[str, str] = {
    "pisos": (
        "Scrape rental listings from https://www.pisos.com/alquiler/pisos-madrid_capital_zona_urbana/ "
        "for flats in Madrid with max rent 1100 EUR, 2-3 bedrooms. "
        "Return a JSON array with title, price_eur, rooms, area_m2, zone, and url for each listing."
    ),
}

_PLACEHOLDER_TASKS: frozenset[str] = frozenset({"football"})


def _run(task: str) -> int:
    if task in _PLACEHOLDER_TASKS:
        print(
            f"Task '{task}' is a placeholder — it will be enabled once "
            "the football-odds PR is merged.",
            file=sys.stderr,
        )
        return 0

    prompt = _TASK_PROMPTS.get(task)
    if prompt is None:
        known = sorted(_TASK_PROMPTS.keys() | _PLACEHOLDER_TASKS)
        print(f"Unknown task: '{task}'.  Known tasks: {', '.join(known)}", file=sys.stderr)
        return 1

    runner = Runner()
    result = runner.run(prompt)
    print(result)
    return 0


def main(argv: list[str] | None = None) -> NoReturn:
    parser = argparse.ArgumentParser(
        prog="mimir-webwright",
        description="mimir-webwright task launcher",
    )
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Run a registered task")
    run_p.add_argument("--task", required=True, help="Task name to execute")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        sys.exit(_run(args.task))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
