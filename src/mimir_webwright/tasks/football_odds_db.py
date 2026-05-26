from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import psycopg


@dataclass(frozen=True)
class DbConfig:
    host: str
    user: str
    password: str
    dbname: str


def load_db_config_from_env() -> DbConfig:
    missing: list[str] = []

    def _get(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            missing.append(name)
            return ""
        return value

    cfg = DbConfig(
        host=_get("MIMIR_DB_HOST"),
        user=_get("MIMIR_DB_USER"),
        password=_get("MIMIR_DB_PASSWORD"),
        dbname=_get("MIMIR_DB_NAME"),
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
        sslmode="require",
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


def insert_football_predictions(
    conn: psycopg.Connection[Any],
    rows: Iterable[dict[str, Any]],
) -> int:
    """Insert scraped rows.

    This is intentionally conservative: we only map fields that exist.
    Unknown columns are ignored.
    """

    schema = fetch_table_schema(conn, "football_predictions")
    columns = {name for name, _ in schema}

    # Minimal mapping: best-effort based on existing schema
    mapping: dict[str, str] = {
        "home_team": "home_team",
        "away_team": "away_team",
        "kickoff_utc": "kickoff_utc",
        "league": "league",
        "odds_home": "odds_home",
        "odds_draw": "odds_draw",
        "odds_away": "odds_away",
        "match_url": "match_url",
        "source": "source",
        "scraped_at_utc": "scraped_at_utc",
    }

    target_cols = [dst for dst in mapping.values() if dst in columns]
    if not target_cols:
        raise RuntimeError("No compatible columns found in football_predictions")

    placeholders = ", ".join(["%s"] * len(target_cols))
    insert_sql = (
        f"INSERT INTO football_predictions ({', '.join(target_cols)}) "
        f"VALUES ({placeholders})"
    )

    inserted = 0
    with conn.cursor() as cur:
        for row in rows:
            values = [row.get(src) for src, dst in mapping.items() if dst in columns]
            if not values:
                continue
            cur.execute(insert_sql, tuple(values))
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
