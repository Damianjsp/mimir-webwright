"""Tests for mimir_webwright.cli entry point."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mimir_webwright.cli import _run, main


# ---------------------------------------------------------------------------
# _run() unit tests (no subprocess / model calls)
# ---------------------------------------------------------------------------


def test_run_unknown_task_returns_1() -> None:
    rc = _run("nonexistent-task")
    assert rc == 1


def test_run_placeholder_football_returns_0(capsys: pytest.CaptureFixture[str]) -> None:
    rc = _run("football")
    assert rc == 0
    captured = capsys.readouterr()
    assert "placeholder" in captured.err


def test_run_pisos_calls_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_result: dict[str, Any] = {"task": "pisos", "steps": [], "result": "done"}

    mock_runner = MagicMock()
    mock_runner.run.return_value = fake_result

    with patch("mimir_webwright.cli.Runner", return_value=mock_runner):
        rc = _run("pisos")

    assert rc == 0
    mock_runner.run.assert_called_once()
    # Verify the prompt mentions pisos.com
    call_args = mock_runner.run.call_args[0][0]
    assert "pisos.com" in call_args.lower()


# ---------------------------------------------------------------------------
# main() / argparse integration tests
# ---------------------------------------------------------------------------


def test_main_run_pisos_exits_0(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_result: dict[str, Any] = {"task": "pisos", "steps": [], "result": "ok"}
    mock_runner = MagicMock()
    mock_runner.run.return_value = fake_result

    with patch("mimir_webwright.cli.Runner", return_value=mock_runner):
        with pytest.raises(SystemExit) as exc_info:
            main(["run", "--task", "pisos"])

    assert exc_info.value.code == 0


def test_main_run_football_placeholder_exits_0() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--task", "football"])

    assert exc_info.value.code == 0


def test_main_run_unknown_task_exits_1() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--task", "does-not-exist"])

    assert exc_info.value.code == 1


def test_main_no_subcommand_exits_1() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 1


def test_main_missing_task_flag_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["run"])

    assert exc_info.value.code != 0
