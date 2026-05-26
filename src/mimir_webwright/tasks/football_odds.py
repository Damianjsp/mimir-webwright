from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

DEFAULT_SCRIPT_NAME = "football_odds_scraper.py"
DEFAULT_URL = "https://www.sofascore.com/football"


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
    source: str = "sofascore"
    scraped_at_utc: str = datetime.now(tz=UTC).isoformat()


class SupportsWriteText(Protocol):
    def write_text(self, data: str, *, encoding: str) -> Any: ...


def generated_script_source() -> str:
    return '''from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import typer
from playwright.sync_api import sync_playwright

from mimir_webwright.tasks.football_odds import (
    DEFAULT_URL,
    FootballOdds,
)

app = typer.Typer(add_completion=False)


def _env_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return Path(value)


def _first_float(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = (
        value.strip()
        .replace("\u2212", "-")
        .replace(",", ".")
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_url(href: str) -> str:
    href = (href or "").strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("/"):
        return f"https://www.sofascore.com{href}"
    return href


def _scrape_from_page(page) -> list[FootballOdds]:
    """Best-effort extraction.

    NOTE: Sofascore is highly dynamic; selectors may drift.
    We keep this resilient and return empty list on mismatch.
    """

    page.goto(DEFAULT_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(3_000)

    matches: list[FootballOdds] = []

    # Candidate selectors for event cards/rows
    card_selectors = [
        "a[href*='/event/']",
        "a[href*='/match/']",
        "a[href*='/football/']",
    ]

    anchors = None
    for sel in card_selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            anchors = loc
            break

    if anchors is None:
        return matches

    count = min(anchors.count(), 80)
    seen: set[str] = set()

    for idx in range(count):
        a = anchors.nth(idx)
        href = a.get_attribute("href", timeout=1000) or ""
        url = _normalize_url(href)
        if not url or url in seen:
            continue
        seen.add(url)

        text = " ".join(t.strip() for t in a.all_inner_texts() if t.strip())
        if not text:
            continue

        # Extremely heuristic: look for something like "Team A - Team B"
        if " - " not in text:
            continue
        maybe_home, maybe_away = text.split(" - ", 1)
        home = maybe_home.strip()
        away = maybe_away.strip().split("\n")[0].strip()
        if len(home) < 2 or len(away) < 2:
            continue

        # Odds are often present as 3 numbers nearby; try to read from sibling spans.
        container = a.locator("xpath=ancestor-or-self::*[self::a or self::div][1]")
        odds_texts = [t.strip() for t in container.locator("span").all_inner_texts() if t.strip()]
        floats = [_first_float(t) for t in odds_texts]
        floats = [f for f in floats if f and 1.0 <= f <= 1000.0]
        odds_home = floats[0] if len(floats) >= 1 else None
        odds_draw = floats[1] if len(floats) >= 2 else None
        odds_away = floats[2] if len(floats) >= 3 else None

        matches.append(
            FootballOdds(
                home_team=home,
                away_team=away,
                kickoff_utc=None,
                league=None,
                odds_home=odds_home,
                odds_draw=odds_draw,
                odds_away=odds_away,
                match_url=url,
                scraped_at_utc=datetime.now(tz=UTC).isoformat(),
            )
        )

    return matches


@app.command()
def main(headful: bool = typer.Option(False, help="Run browser with UI")) -> int:
    run_dir = _env_path("MIMIR_WEBWRIGHT_RUN_DIR")
    screenshots_dir = _env_path("MIMIR_WEBWRIGHT_SCREENSHOTS_DIR")
    out_json = run_dir / "football_odds.json"

    screenshots_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        try:
            page = browser.new_page()
            matches = _scrape_from_page(page)
            page.screenshot(path=str(screenshots_dir / "football_landing.png"), full_page=True)
        finally:
            browser.close()

    payload = [asdict(m) for m in matches]
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(app())
'''


def ensure_generated_script(scripts_dir: Path) -> Path:
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / DEFAULT_SCRIPT_NAME
    script_path.write_text(generated_script_source(), encoding="utf-8")
    return script_path


def write_results_json(results_path: SupportsWriteText, rows: list[FootballOdds]) -> None:
    results_path.write_text(
        json.dumps([asdict(row) for row in rows], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
