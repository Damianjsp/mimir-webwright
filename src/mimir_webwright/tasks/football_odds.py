from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


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
