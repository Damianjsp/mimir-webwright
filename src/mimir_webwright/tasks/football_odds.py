from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_SCRIPT_NAME = "football_odds_scraper.py"


def generated_script_source() -> str:
    return '''"""Generated football_odds runner using playwright-backed API fetcher."""
from mimir_webwright.tasks.football_api_fetcher import script_entrypoint

if __name__ == "__main__":
    raise SystemExit(script_entrypoint())
'''


def ensure_generated_script(scripts_dir: Path) -> Path:
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / DEFAULT_SCRIPT_NAME
    if not script_path.exists():
        script_path.write_text(generated_script_source(), encoding="utf-8")
    return script_path


@dataclass(frozen=True)
class FootballOdds:
    home_team: str
    away_team: str
    kickoff_utc: str | None
    league: str | None
    odds_home: float | None
    odds_draw: float | None
    odds_away: float | None
    match_url: str
    fixture_id: int | None = None
    source: str = "api-football"
    scraped_at_utc: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
