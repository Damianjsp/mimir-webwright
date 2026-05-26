from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from mimir_webwright.environment import WorkspaceEnvironment
from mimir_webwright.tasks.football_odds import (
    DEFAULT_SCRIPT_NAME as FOOTBALL_SCRIPT_NAME,
    ensure_generated_script as ensure_football_script,
)
from mimir_webwright.tasks.pisos_scraper import (
    DEFAULT_SCRIPT_NAME,
    PisosFilters,
    ensure_generated_script,
)

app = typer.Typer(help="Mimir Webwright runner")
console = Console()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@app.command("pisos-scraper")
def pisos_scraper_command(
    zone: str = typer.Option("madrid", help="Zone or neighborhood filter"),
    max_price: int = typer.Option(1100, help="Maximum monthly rent in EUR"),
    min_rooms: int = typer.Option(2, help="Minimum bedrooms"),
    max_rooms: int = typer.Option(3, help="Maximum bedrooms"),
    headful: bool = typer.Option(False, help="Run browser with UI"),
) -> None:
    """Run the reusable Pisos.com scraper task."""

    environment = WorkspaceEnvironment(root_dir=_repo_root())
    run_paths = environment.prepare_run("pisos_scraper")
    script_path = ensure_generated_script(run_paths.scripts_dir)
    filters = PisosFilters(
        zone=zone,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
    )
    completed = environment.run_python_script(
        script_path,
        run_paths,
        [
            "--zone",
            filters.zone,
            "--max-price",
            str(filters.max_price),
            "--min-rooms",
            str(filters.min_rooms),
            "--max-rooms",
            str(filters.max_rooms),
            *( ["--headful"] if headful else []),
        ],
    )
    if completed.returncode != 0:
        console.print(f"[red]Task failed.[/red] See {run_paths.log_path}")
        raise typer.Exit(code=completed.returncode)

    console.print(f"[green]Script reused:[/green] {run_paths.scripts_dir / DEFAULT_SCRIPT_NAME}")
    console.print(f"[green]JSON:[/green] {run_paths.json_path}")
    console.print(f"[green]CSV:[/green] {run_paths.csv_path}")
    console.print(f"[green]Log:[/green] {run_paths.log_path}")


@app.command("football-odds")
def football_odds_command(
    headful: bool = typer.Option(False, help="Run browser with UI"),
) -> None:
    """Generate+run the football odds scraper.

    The generated Playwright script is stored in workspace/scripts/football_odds_scraper.py
    and writes JSON to workspace/runs/<timestamp>/football_odds.json
    """

    environment = WorkspaceEnvironment(root_dir=_repo_root())
    run_paths = environment.prepare_run("football_odds")
    script_path = ensure_football_script(run_paths.scripts_dir)

    completed = environment.run_python_script(
        script_path,
        run_paths,
        [*( ["--headful"] if headful else [])],
    )
    if completed.returncode != 0:
        console.print(f"[red]Task failed.[/red] See {run_paths.log_path}")
        raise typer.Exit(code=completed.returncode)

    console.print(f"[green]Script generated:[/green] {run_paths.scripts_dir / FOOTBALL_SCRIPT_NAME}")
    console.print(f"[green]JSON:[/green] {run_paths.run_dir / 'football_odds.json'}")
    console.print(f"[green]Log:[/green] {run_paths.log_path}")


@app.command("run-task")
def run_task(task_name: str) -> None:
    """Compatibility entrypoint for future task registry expansion."""

    if task_name == "pisos-scraper":
        pisos_scraper_command()
        return
    if task_name == "football-odds":
        football_odds_command()
        return

    raise typer.BadParameter("Supported tasks: 'pisos-scraper', 'football-odds'.")


if __name__ == "__main__":
    app()
