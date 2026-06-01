from __future__ import annotations

import os
import time
from datetime import UTC, datetime

import requests

from mimir_webwright.tasks.football_odds import FootballOdds

_BASE_URL = "https://v3.football.api-sports.io"
_WORLD_CUP_LEAGUE = 1
_BOOKMAKER_BET365 = 8

# API-Football free plan: 10 requests/minute. Leave headroom.
_REQUEST_INTERVAL_SECS = 6.5


def _get_api_key() -> str:
    key = os.environ.get("API_FOOTBALL_KEY", "")
    if not key:
        raise RuntimeError("Missing env var: API_FOOTBALL_KEY")
    return key


def _to_float(s: str | None) -> float | None:
    try:
        return float(s) if s else None
    except (TypeError, ValueError):
        return None


def _api_get(path: str, params: dict[str, object], api_key: str) -> dict:  # type: ignore[type-arg]
    """GET from API-Football with a single 429-retry after a 61-second back-off."""
    url = f"{_BASE_URL}{path}"
    headers = {"x-apisports-key": api_key}
    for attempt in range(2):
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 429 and attempt == 0:
            time.sleep(61)
            continue
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]
    resp.raise_for_status()  # satisfies type checker; unreachable in practice
    return {}


def _fetch_fixtures(api_key: str, season: int) -> dict[int, dict]:  # type: ignore[type-arg]
    """Return mapping of fixture_id -> fixture metadata. Empty if plan-restricted."""
    data = _api_get(
        "/fixtures",
        {"league": _WORLD_CUP_LEAGUE, "season": season},
        api_key,
    )
    if data.get("errors"):
        return {}
    fixtures: dict[int, dict] = {}  # type: ignore[type-arg]
    for entry in data.get("response", []):
        fid = entry["fixture"]["id"]
        fixtures[fid] = entry
    return fixtures


def _fetch_odds(api_key: str, season: int) -> dict[int, dict[str, float | None]]:
    """Return fixture_id -> {odds_home, odds_draw, odds_away} from Bet365 1x2 market."""
    data = _api_get(
        "/odds",
        {"league": _WORLD_CUP_LEAGUE, "season": season, "bookmaker": _BOOKMAKER_BET365},
        api_key,
    )
    if data.get("errors"):
        return {}
    odds_map: dict[int, dict[str, float | None]] = {}
    for entry in data.get("response", []):
        fid = entry["fixture"]["id"]
        bookmakers = entry.get("bookmakers", [])
        if not bookmakers:
            continue
        bm = bookmakers[0]
        bets = bm.get("bets", [])
        market: dict | None = None  # type: ignore[type-arg]
        for bet in bets:
            if bet.get("name") == "Match Winner":
                market = bet
                break
        if market is None:
            continue
        values = {v["value"]: v["odd"] for v in market.get("values", [])}
        odds_map[fid] = {
            "odds_home": _to_float(values.get("Home")),
            "odds_draw": _to_float(values.get("Draw")),
            "odds_away": _to_float(values.get("Away")),
        }
    return odds_map


def _pct_to_implied_odd(pct_str: str | None) -> float | None:
    """Convert "45%" -> 2.22 (implied decimal odd). Returns None if unparseable."""
    if not pct_str:
        return None
    try:
        pct = float(pct_str.rstrip("%"))
        if pct <= 0:
            return None
        return round(100.0 / pct, 4)
    except (TypeError, ValueError):
        return None


def _fetch_predictions_as_odds(
    api_key: str,
    fixture_ids: list[int],
    max_fixtures: int = 16,
) -> dict[int, dict[str, float | None]]:
    """Fallback: derive implied odds from /predictions endpoint.

    Respects the 10-req/min rate limit with a sleep between calls.
    Capped at ``max_fixtures`` to avoid exhausting the daily quota.
    """
    odds_map: dict[int, dict[str, float | None]] = {}
    for fid in fixture_ids[:max_fixtures]:
        try:
            data = _api_get("/predictions", {"fixture": fid}, api_key)
        except requests.HTTPError:
            time.sleep(_REQUEST_INTERVAL_SECS)
            continue
        if data.get("errors") or not data.get("response"):
            time.sleep(_REQUEST_INTERVAL_SECS)
            continue
        pred = data["response"][0].get("predictions", {})
        pct = pred.get("percent", {})
        odds_map[fid] = {
            "odds_home": _pct_to_implied_odd(pct.get("home")),
            "odds_draw": _pct_to_implied_odd(pct.get("draw")),
            "odds_away": _pct_to_implied_odd(pct.get("away")),
        }
        time.sleep(_REQUEST_INTERVAL_SECS)
    return odds_map


def fetch_world_cup_odds(season: int = 2026, predictions_limit: int = 16) -> list[FootballOdds]:
    """Fetch World Cup fixtures + Bet365 1x2 odds for the given season.

    Falls back to /predictions-derived implied odds when the bookmaker odds
    endpoint returns no data (free-plan accounts or pre-season).
    Returns empty list if the season is not accessible on the current plan.

    ``predictions_limit`` caps per-run API calls when using the predictions
    fallback (free plan: 100 req/day, 10 req/min).
    """
    api_key = _get_api_key()
    fixtures = _fetch_fixtures(api_key, season)
    if not fixtures:
        return []

    time.sleep(_REQUEST_INTERVAL_SECS)  # respect 10 req/min between top-level calls
    odds_map = _fetch_odds(api_key, season)

    if not odds_map:
        # No Bet365 odds — derive implied odds from model predictions
        time.sleep(_REQUEST_INTERVAL_SECS)
        odds_map = _fetch_predictions_as_odds(
            api_key, list(fixtures.keys()), max_fixtures=predictions_limit
        )

    scraped_at = datetime.now(tz=UTC).isoformat()
    results: list[FootballOdds] = []

    for fid, entry in fixtures.items():
        fixture = entry["fixture"]
        teams = entry["teams"]
        league_info = entry.get("league", {})
        odds = odds_map.get(fid, {})

        kickoff_raw = fixture.get("date")
        kickoff_utc: str | None = None
        if kickoff_raw:
            try:
                kickoff_utc = (
                    datetime.fromisoformat(kickoff_raw.replace("Z", "+00:00"))
                    .astimezone(UTC)
                    .isoformat()
                )
            except ValueError:
                kickoff_utc = kickoff_raw

        match_url = f"https://www.api-football.com/fixture/{fid}"

        results.append(
            FootballOdds(
                home_team=teams["home"]["name"],
                away_team=teams["away"]["name"],
                kickoff_utc=kickoff_utc,
                league=league_info.get("name"),
                odds_home=odds.get("odds_home"),
                odds_draw=odds.get("odds_draw"),
                odds_away=odds.get("odds_away"),
                match_url=match_url,
                fixture_id=fid,
                source="api-football",
                scraped_at_utc=scraped_at,
            )
        )

    return results
