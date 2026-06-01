from __future__ import annotations

from pathlib import Path

from mimir_webwright.tasks.pisos_scraper import (
    PisoListing,
    PisosFilters,
    _extract_listing_from_card,
    ensure_generated_script,
    write_results,
)


def test_ensure_generated_script_reuses_same_file(tmp_path: Path) -> None:
    first = ensure_generated_script(tmp_path)
    second = ensure_generated_script(tmp_path)

    assert first == second
    assert first.name == "pisos_com_madrid.py"
    assert "script_entrypoint" in first.read_text(encoding="utf-8")


def test_write_results_outputs_json_and_csv(tmp_path: Path) -> None:
    listings = [
        PisoListing(
            title="Piso reformado en Tetuán",
            price_eur=1050,
            rooms=2,
            area_m2=68,
            zone="Tetuán, Madrid",
            url="https://www.pisos.com/example",
        )
    ]

    json_path = tmp_path / "results.json"
    csv_path = tmp_path / "results.csv"
    write_results(listings, json_path, csv_path)

    json_text = json_path.read_text(encoding="utf-8")
    csv_text = csv_path.read_text(encoding="utf-8")

    assert "Tetuán" in json_text
    assert "price_eur" in csv_text
    assert "https://www.pisos.com/example" in csv_text


def test_filters_defaults_match_requested_search_window() -> None:
    filters = PisosFilters()

    assert filters.zone == "madrid"
    assert filters.max_price == 1100
    assert filters.min_rooms == 2
    assert filters.max_rooms == 3


class _FakeLeaf:
    def __init__(self, text: str = "", href: str | None = None) -> None:
        self._text = text
        self._href = href

    def count(self) -> int:
        return 1 if self._text or self._href else 0

    def inner_text(self, timeout: int = 1000) -> str:
        del timeout
        return self._text

    def get_attribute(self, name: str, timeout: int = 1000) -> str | None:
        del timeout
        if name == "href":
            return self._href
        if name == "alt":
            return self._text
        return None


class _FakeLocator:
    def __init__(self, leaves: list[_FakeLeaf]) -> None:
        self._leaves = leaves

    @property
    def first(self) -> _FakeLeaf:
        return self._leaves[0] if self._leaves else _FakeLeaf()

    def all_inner_texts(self) -> list[str]:
        return [leaf.inner_text() for leaf in self._leaves if leaf.count()]


class _FakeCard:
    def __init__(self) -> None:
        self._mapping = {
            "a.ad-preview__title": [
                _FakeLeaf("Piso en calle de Miami", "/alquilar/piso-san_blas/123/"),
            ],
            ".ad-preview__price": [_FakeLeaf("1.050 €")],
            ".ad-preview__char": [
                _FakeLeaf("2 habs."),
                _FakeLeaf("2 baños"),
                _FakeLeaf("90 m²"),
            ],
            ".ad-preview__subtitle": [_FakeLeaf("Salvador (Distrito San Blas. Madrid Capital)")],
            "img": [_FakeLeaf("Piso en calle de Miami")],
        }

    def locator(self, selector: str) -> _FakeLocator:
        return _FakeLocator(self._mapping.get(selector, []))

    def get_attribute(self, name: str, timeout: int = 1000) -> str | None:
        del timeout
        if name == "data-lnk-href":
            return "/alquilar/piso-san_blas/123/"
        return None


def test_extract_listing_from_ad_preview_card() -> None:
    listing = _extract_listing_from_card(_FakeCard())

    assert listing is not None
    assert listing.title == "Piso en calle de Miami"
    assert listing.price_eur == 1050
    assert listing.rooms == 2
    assert listing.area_m2 == 90
    assert listing.zone == "Salvador (Distrito San Blas. Madrid Capital)"
    assert listing.url == "https://www.pisos.com/alquilar/piso-san_blas/123/"
