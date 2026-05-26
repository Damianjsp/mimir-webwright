"""Task prompt for generating a pisos.com scraper with Playwright."""

PISOS_TASK = """
Write and execute a Playwright Python script that:
1. Goes to https://www.pisos.com/alquiler/pisos-madrid_capital_zona_urbana/
2. Filters: 2-3 bedrooms, max price 1100 EUR/month
3. Extracts from first 20 listings: title, price, bedrooms, sqm, neighborhood, URL
4. Saves results to workspace/runs/<timestamp>/pisos_results.json
5. Prints a summary

Save the final working script to workspace/scripts/pisos_scraper.py
""".strip()


def get_task() -> str:
    """Return the pisos.com scraping task prompt."""
    return PISOS_TASK
