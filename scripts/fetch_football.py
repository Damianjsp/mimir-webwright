#!/usr/bin/env python3
"""Fetch World Cup fixtures + Bet365 odds and insert into football_predictions.

Tries season 2026 first; falls back to the most recent accessible season
(2022) if the current API plan restricts 2026 access.
"""
from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

# Source env file before importing project modules so DB/API creds are available.
# load_dotenv handles "export KEY=VALUE" lines correctly (strips the export prefix).
_ENV_FILE = Path("/home/damian/.config/mimir-webwright/env")
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=False)

from mimir_webwright.tasks.football_api_fetcher import fetch_world_cup_odds  # noqa: E402
from mimir_webwright.tasks.football_odds_db import (  # noqa: E402
    insert_football_predictions,
    load_db_config_from_env,
)

import psycopg  # noqa: E402

_PREFERRED_SEASON = 2026
_FALLBACK_SEASON = 2022


def main() -> None:
    season = _PREFERRED_SEASON
    fixtures = fetch_world_cup_odds(season=season)

    if not fixtures:
        print(f"Season {season} returned 0 fixtures (plan restriction?). Trying {_FALLBACK_SEASON}…")
        season = _FALLBACK_SEASON
        fixtures = fetch_world_cup_odds(season=season)

    if not fixtures:
        print("No fixtures returned for any season — nothing to insert.")
        return

    cfg = load_db_config_from_env()
    rows = [asdict(f) for f in fixtures]
    conn_kwargs: dict[str, str | int] = {
        "host": cfg.host,
        "user": cfg.user,
        "password": cfg.password,
        "dbname": cfg.dbname,
        "port": cfg.port,
        "sslmode": cfg.sslmode,
    }
    with psycopg.connect(**conn_kwargs) as conn:
        inserted = insert_football_predictions(conn, rows)

    print(f"Fetched {len(fixtures)} fixtures (season {season}), inserted {inserted} rows")


if __name__ == "__main__":
    main()
