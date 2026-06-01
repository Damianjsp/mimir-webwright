from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg


@dataclass(frozen=True)
class DbConfig:
    host: str
    user: str
    password: str
    dbname: str
    port: int = 5432
    sslmode: str = "require"


def load_db_config_from_env() -> DbConfig:
    missing: list[str] = []

    def _get(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            missing.append(name)
            return ""
        return value

    port_str = os.environ.get("MIMIR_DB_PORT", "5432")
    try:
        port = int(port_str)
    except ValueError:
        port = 5432

    cfg = DbConfig(
        host=_get("MIMIR_DB_HOST"),
        user=_get("MIMIR_DB_USER"),
        password=_get("MIMIR_DB_PASSWORD"),
        dbname=_get("MIMIR_DB_NAME"),
        port=port,
        sslmode=os.environ.get("MIMIR_DB_SSLMODE", "require"),
    )
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")
    return cfg


def _connect(cfg: DbConfig) -> psycopg.Connection[Any]:
    return psycopg.connect(
        host=cfg.host,
        user=cfg.user,
        password=cfg.password,
        dbname=cfg.dbname,
        port=cfg.port,
        sslmode=cfg.sslmode,
    )


def fetch_table_schema(conn: psycopg.Connection[Any], table_name: str) -> list[tuple[str, str]]:
    query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(query, (table_name,))
        rows = cur.fetchall()
    return [(str(col), str(dtype)) for col, dtype in rows]


def load_odds_rows(json_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Expected list payload")
    rows: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _kickoff_date_fragment(kickoff_utc: str | None) -> str:
    if not kickoff_utc:
        return "unknown-date"

    parsed = datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00"))
    return parsed.date().isoformat()


def _build_market_id(row: dict[str, Any]) -> str:
    home_team = str(row.get("home_team") or "unknown-home")
    away_team = str(row.get("away_team") or "unknown-away")
    kickoff_utc = row.get("kickoff_utc")

    return (
        f"{_slugify(home_team)}_vs_{_slugify(away_team)}_"
        f"{_kickoff_date_fragment(kickoff_utc if isinstance(kickoff_utc, str) else None)}"
    )


def _normalize_probability(odd: Any, total_inverse_odds: float) -> float | None:
    if odd is None:
        return None

    try:
        odd_value = float(odd)
    except (TypeError, ValueError):
        return None

    if odd_value <= 0:
        return None

    return (1.0 / odd_value) / total_inverse_odds


def _build_insert_row(row: dict[str, Any]) -> tuple[Any, ...] | None:
    home_team_raw = row.get("home_team")
    away_team_raw = row.get("away_team")
    kickoff_utc = row.get("kickoff_utc")

    if not isinstance(home_team_raw, str) or not home_team_raw.strip():
        return None
    if not isinstance(away_team_raw, str) or not away_team_raw.strip():
        return None
    if kickoff_utc is not None and not isinstance(kickoff_utc, str):
        return None

    inverse_odds: list[float] = []
    for field in ("odds_home", "odds_draw", "odds_away"):
        value = row.get(field)
        if value is None:
            continue
        try:
            odd_value = float(value)
        except (TypeError, ValueError):
            continue
        if odd_value <= 0:
            continue
        inverse_odds.append(1.0 / odd_value)

    if not inverse_odds:
        return None

    total_inverse_odds = sum(inverse_odds)
    home_team = home_team_raw.strip()
    away_team = away_team_raw.strip()

    fixture_id_raw = row.get("fixture_id")
    fixture_id: int | None
    if fixture_id_raw is None:
        fixture_id = None
    else:
        try:
            fixture_id = int(fixture_id_raw)
        except (TypeError, ValueError):
            fixture_id = None

    return (
        _build_market_id(row),
        f"{home_team} vs {away_team}",
        home_team,
        away_team,
        fixture_id,
        kickoff_utc,
        _normalize_probability(row.get("odds_home"), total_inverse_odds),
        _normalize_probability(row.get("odds_draw"), total_inverse_odds),
        _normalize_probability(row.get("odds_away"), total_inverse_odds),
        "webwright-v1",
    )


def insert_football_predictions(
    conn: psycopg.Connection[Any],
    rows: Iterable[dict[str, Any]],
) -> int:
    insert_sql = """
        INSERT INTO football_predictions (
            market_id,
            market_question,
            home_team,
            away_team,
            fixture_id,
            kickoff_utc,
            prob_home,
            prob_draw,
            prob_away,
            model_version
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (market_id, model_version) DO UPDATE
        SET
            market_question = EXCLUDED.market_question,
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            fixture_id = EXCLUDED.fixture_id,
            kickoff_utc = EXCLUDED.kickoff_utc,
            prob_home = EXCLUDED.prob_home,
            prob_draw = EXCLUDED.prob_draw,
            prob_away = EXCLUDED.prob_away
    """

    inserted = 0
    with conn.cursor() as cur:
        for row in rows:
            insert_row = _build_insert_row(row)
            if insert_row is None:
                continue
            cur.execute(insert_sql, insert_row)
            inserted += 1
    conn.commit()
    return inserted


def main(json_path: Path) -> int:
    cfg = load_db_config_from_env()
    rows = load_odds_rows(json_path)
    with _connect(cfg) as conn:
        inserted = insert_football_predictions(conn, rows)
    print(f"Inserted {inserted} rows into football_predictions")
    return 0
