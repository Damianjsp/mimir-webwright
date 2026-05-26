from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright

DEFAULT_SCRIPT_NAME = "pisos_com_madrid.py"
DEFAULT_URL = "https://www.pisos.com/alquiler/pisos-madrid_capital_zona_urbana/"
CARD_SELECTOR_CANDIDATES = [
    "div.ad-preview",
    "article.card, article.ad-preview, div.card__content, div.box-inline, div.re-Card",
    "article",
]
TITLE_SELECTORS = ["a.ad-preview__title", "a.card__title", "h3 a", "a"]
PRICE_SELECTORS = [".ad-preview__price", ".price", ".card__price", "[class*='price']"]
DETAIL_SELECTORS = [
    ".ad-preview__char",
    ".card__detail",
    ".feature",
    "[class*='feature']",
    "li",
]
ZONE_SELECTORS = [
    ".ad-preview__subtitle",
    ".card__location",
    ".location",
    "[class*='location']",
]


@dataclass(frozen=True)
class PisosFilters:
    zone: str = "madrid"
    max_price: int = 1100
    min_rooms: int = 2
    max_rooms: int = 3


@dataclass(frozen=True)
class PisoListing:
    title: str
    price_eur: int | None
    rooms: int | None
    area_m2: int | None
    zone: str
    url: str


def generated_script_source() -> str:
    return '''from mimir_webwright.tasks.pisos_scraper import script_entrypoint

if __name__ == "__main__":
    raise SystemExit(script_entrypoint())
'''


def ensure_generated_script(scripts_dir: Path) -> Path:
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / DEFAULT_SCRIPT_NAME
    if not script_path.exists():
        script_path.write_text(generated_script_source(), encoding="utf-8")
    return script_path


def _parse_first_int(text: str) -> int | None:
    match = re.search(r"(\d+[\.,]?\d*)", text.replace(".", "").replace(",", "."))
    if match is None:
        return None
    try:
        return int(float(match.group(1)))
    except ValueError:
        return None


def _parse_detail_value(details_text: str, pattern: str) -> int | None:
    match = re.search(pattern, details_text, flags=re.IGNORECASE)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _normalize_url(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/"):
        return f"https://www.pisos.com{value}"
    return value


def _extract_listing_from_card(card: Any) -> PisoListing | None:
    title = ""
    url = ""
    for selector in TITLE_SELECTORS:
        locator = card.locator(selector).first
        if locator.count():
            title = locator.inner_text(timeout=1000).strip()
            href = locator.get_attribute("href", timeout=1000) or ""
            url = _normalize_url(href)
            break

    if not url:
        container_href = card.get_attribute("data-lnk-href", timeout=1000) or ""
        if container_href:
            url = _normalize_url(container_href)
    if not title:
        image_alt = card.locator("img").first.get_attribute("alt", timeout=1000) or ""
        title = image_alt.strip()
    if not title or not url:
        return None

    price_text = ""
    for selector in PRICE_SELECTORS:
        locator = card.locator(selector).first
        if locator.count():
            price_text = locator.inner_text(timeout=1000).strip()
            if price_text:
                break

    details_text = " ".join(
        text.strip()
        for selector in DETAIL_SELECTORS
        for text in card.locator(selector).all_inner_texts()
        if text.strip()
    )
    zone_text = ""
    for selector in ZONE_SELECTORS:
        locator = card.locator(selector).first
        if locator.count():
            zone_text = locator.inner_text(timeout=1000).strip()
            if zone_text:
                break

    rooms = _parse_detail_value(details_text, r"(\d+)\s*habs?\.")
    area_m2 = _parse_detail_value(details_text, r"(\d+)\s*m(?:²|2)")

    return PisoListing(
        title=title,
        price_eur=_parse_first_int(price_text),
        rooms=rooms,
        area_m2=area_m2,
        zone=zone_text or "Madrid",
        url=url,
    )


def scrape_pisos(
    filters: PisosFilters,
    screenshots_dir: Path,
    *,
    headless: bool = True,
) -> list[PisoListing]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            page = browser.new_page()
            return _run_scrape(page, browser, filters, screenshots_dir)
        finally:
            browser.close()


def _run_scrape(
    page: Page,
    browser: Browser,
    filters: PisosFilters,
    screenshots_dir: Path,
) -> list[PisoListing]:
    del browser
    page.goto(DEFAULT_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(3_000)
    page.screenshot(path=str(screenshots_dir / "landing.png"), full_page=True)

    listings: list[PisoListing] = []
    seen_urls: set[str] = set()
    cards = None
    for selector in CARD_SELECTOR_CANDIDATES:
        locator = page.locator(selector)
        if locator.count() > 0:
            cards = locator
            break
    if cards is None:
        return listings

    count = min(cards.count(), 60)
    for index in range(count):
        listing = _extract_listing_from_card(cards.nth(index))
        if listing is None or listing.url in seen_urls:
            continue
        seen_urls.add(listing.url)
        if listing.price_eur is not None and listing.price_eur > filters.max_price:
            continue
        if listing.rooms is not None and listing.rooms < filters.min_rooms:
            continue
        if listing.rooms is not None and listing.rooms > filters.max_rooms:
            continue
        zone_filter = filters.zone.lower()
        if zone_filter not in listing.zone.lower() and zone_filter not in listing.title.lower():
            continue
        listings.append(listing)

    page.screenshot(path=str(screenshots_dir / "results.png"), full_page=True)
    return listings


def write_results(listings: list[PisoListing], json_path: Path, csv_path: Path) -> None:
    json_path.write_text(
        json.dumps([asdict(listing) for listing in listings], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["title", "price_eur", "rooms", "area_m2", "zone", "url"],
        )
        writer.writeheader()
        for listing in listings:
            writer.writerow(asdict(listing))


def script_entrypoint(argv: list[str] | None = None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Scrape Pisos.com rental listings for Madrid")
    parser.add_argument("--zone", default="madrid")
    parser.add_argument("--max-price", type=int, default=1100)
    parser.add_argument("--min-rooms", type=int, default=2)
    parser.add_argument("--max-rooms", type=int, default=3)
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args(argv)

    results_json = Path(os.environ["MIMIR_WEBWRIGHT_RESULTS_JSON"])
    results_csv = Path(os.environ["MIMIR_WEBWRIGHT_RESULTS_CSV"])
    screenshots_dir = Path(os.environ["MIMIR_WEBWRIGHT_SCREENSHOTS_DIR"])

    listings = scrape_pisos(
        PisosFilters(
            zone=args.zone,
            max_price=args.max_price,
            min_rooms=args.min_rooms,
            max_rooms=args.max_rooms,
        ),
        screenshots_dir,
        headless=not args.headful,
    )
    write_results(listings, results_json, results_csv)
    print(
        json.dumps(
            {"count": len(listings), "results_json": str(results_json)},
            ensure_ascii=False,
        )
    )
    return 0
