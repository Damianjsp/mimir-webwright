from __future__ import annotations

from mimir_webwright.environment import Environment


def test_run_echo(tmp_path) -> None:
    env = Environment(workspace_dir=str(tmp_path / "workspace"))

    output = env.run("echo hello")

    assert output == "hello\n"


def test_save_script_and_new_run(tmp_path) -> None:
    env = Environment(workspace_dir=str(tmp_path / "workspace"))

    script_path = env.save_script("example", "print('ok')")
    run_dir = env.new_run()

    assert script_path.exists()
    assert script_path.read_text(encoding="utf-8") == "print('ok')"
    assert run_dir.exists()
    assert run_dir.parent.name == "runs"



def test_run_timeout_returns_descriptive_message(tmp_path) -> None:
    env = Environment(workspace_dir=str(tmp_path / "workspace"))

    output = env.run("sleep 2", timeout=1)

    assert "[timeout" in output



def test_run_non_zero_exit_includes_exit_code(tmp_path) -> None:
    env = Environment(workspace_dir=str(tmp_path / "workspace"))

    output = env.run("sh -c 'echo boom >&2; exit 1'")

    assert output.startswith("[exit 1]\n")
    assert "boom" in output
