from __future__ import annotations

from pathlib import Path

from mimir_webwright.tasks.football_odds import DEFAULT_SCRIPT_NAME, ensure_generated_script


def test_ensure_generated_script_writes_file(tmp_path: Path) -> None:
    scripts_dir = tmp_path / "scripts"
    script_path = ensure_generated_script(scripts_dir)

    assert script_path.exists()
    assert script_path.name == DEFAULT_SCRIPT_NAME
    content = script_path.read_text(encoding="utf-8")
    assert "playwright" in content
    assert "football_odds" in content
