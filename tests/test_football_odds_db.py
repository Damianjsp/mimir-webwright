from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mimir_webwright.tasks.football_odds_db import (
    _build_market_id,
    fetch_table_schema,
    insert_football_predictions,
    load_db_config_from_env,
    load_odds_rows,
)


def test_load_db_config_from_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MIMIR_DB_HOST", raising=False)
    monkeypatch.delenv("MIMIR_DB_USER", raising=False)
    monkeypatch.delenv("MIMIR_DB_PASSWORD", raising=False)
    monkeypatch.delenv("MIMIR_DB_NAME", raising=False)

    with pytest.raises(RuntimeError) as exc:
        load_db_config_from_env()

    assert "MIMIR_DB_HOST" in str(exc.value)


def test_load_odds_rows_reads_list(tmp_path: Path) -> None:
    json_path = tmp_path / "football_odds.json"
    json_path.write_text(
        '[{"home_team":"A","away_team":"B","odds_home":1.2,"odds_draw":3.3,"odds_away":4.4,"match_url":"https://x"}]',
        encoding="utf-8",
    )
    rows = load_odds_rows(json_path)
    assert rows[0]["home_team"] == "A"


class _FakeCursor:
    def __init__(self, schema: list[tuple[str, str]]) -> None:
        self._schema = schema
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list[tuple[str, str]]:
        return self._schema


class _FakeConn:
    def __init__(self, schema: list[tuple[str, str]]) -> None:
        self._schema = schema
        self.cursor_obj = _FakeCursor(schema)
        self.committed = False

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True


def test_fetch_table_schema_reads_information_schema() -> None:
    conn = _FakeConn(schema=[("home_team", "text")])
    schema = fetch_table_schema(conn, "football_predictions")  # type: ignore[arg-type]
    assert schema == [("home_team", "text")]


def test_build_market_id_uses_match_identity() -> None:
    market_id = _build_market_id(
        {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "kickoff_utc": "2026-05-27T19:00:00Z",
        }
    )

    assert market_id == "real_madrid_vs_barcelona_2026-05-27"


def test_insert_football_predictions_upserts_schema_columns() -> None:
    conn = _FakeConn(
        schema=[
            ("market_id", "text"),
            ("market_question", "text"),
            ("home_team", "text"),
            ("away_team", "text"),
            ("fixture_id", "bigint"),
            ("kickoff_utc", "timestamp with time zone"),
            ("prob_home", "double precision"),
            ("prob_draw", "double precision"),
            ("prob_away", "double precision"),
            ("model_version", "text"),
        ]
    )

    inserted = insert_football_predictions(
        conn,  # type: ignore[arg-type]
        [
            {
                "home_team": "A",
                "away_team": "B",
                "fixture_id": "12345",
                "kickoff_utc": "2026-05-27T19:00:00Z",
                "odds_home": 2.0,
                "odds_draw": 4.0,
                "odds_away": 4.0,
            }
        ],
    )

    assert inserted == 1
    assert conn.committed is True

    inserts = [item for item in conn.cursor_obj.executed if item[0].lstrip().startswith("INSERT")]
    assert len(inserts) == 1

    sql, params = inserts[0]
    assert "football_predictions" in sql
    assert "ON CONFLICT (market_id, model_version) DO UPDATE" in sql
    assert params is not None
    assert params[0] == "a_vs_b_2026-05-27"
    assert params[1] == "A vs B"
    assert params[2] == "A"
    assert params[3] == "B"
    assert params[4] == 12345
    assert params[5] == "2026-05-27T19:00:00Z"
    assert params[6] == pytest.approx(0.5)
    assert params[7] == pytest.approx(0.25)
    assert params[8] == pytest.approx(0.25)
    assert params[9] == "webwright-v1"


def test_insert_football_predictions_skips_rows_without_valid_odds() -> None:
    conn = _FakeConn(schema=[])

    inserted = insert_football_predictions(
        conn,  # type: ignore[arg-type]
        [
            {
                "home_team": "A",
                "away_team": "B",
                "kickoff_utc": "2026-05-27T19:00:00Z",
                "odds_home": 0,
                "odds_draw": None,
                "odds_away": "bad",
            }
        ],
    )

    assert inserted == 0
    assert conn.committed is True
    inserts = [item for item in conn.cursor_obj.executed if item[0].lstrip().startswith("INSERT")]
    assert inserts == []
