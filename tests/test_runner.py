from __future__ import annotations

from mimir_webwright.runner import Runner


class FakeModel:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        self.calls += 1
        if self.calls == 1:
            return "write script", "echo hello"
        return "", "<done>completed</done>"


class FakeEnvironment:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def run(self, command: str) -> str:
        self.commands.append(command)
        return "hello\n"


def test_runner_completes_loop_with_mocks() -> None:
    model = FakeModel()
    env = FakeEnvironment()
    runner = Runner(model=model, env=env, max_steps=3)

    result = runner.run("test task")

    assert result["task"] == "test task"
    assert result["final_result"] == "<done>completed</done>"
    assert env.commands == ["echo hello"]
    assert result["steps"] == [
        {
            "thinking": "write script",
            "command": "echo hello",
            "observation": "hello\n",
        }
    ]
