"""Main Webwright runner loop."""

from __future__ import annotations

from .environment import Environment
from .model import ModelEndpoint

SYSTEM_PROMPT = """You are a web agent. Given a task, write Playwright Python scripts to accomplish it.
Always respond with:
<thinking>your reasoning</thinking>
<bash>the bash command to run</bash>

When done, respond with <done>final result summary</done>"""


class Runner:
    """Coordinate model planning with shell execution and observations."""

    def __init__(
        self,
        model: ModelEndpoint | None = None,
        env: Environment | None = None,
        max_steps: int = 10,
    ) -> None:
        self.model = model or ModelEndpoint()
        self.env = env or Environment()
        self.max_steps = max_steps

    def run(self, task: str) -> dict[str, object]:
        """Execute the plan/act/observe loop for a single task."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        steps: list[dict[str, str]] = []
        final_result = ""

        for _ in range(self.max_steps):
            thinking, command = self.model.complete(messages)
            if "<done>" in command:
                final_result = command
                break

            observation = self.env.run(command)
            steps.append(
                {
                    "thinking": thinking,
                    "command": command,
                    "observation": observation,
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": f"<thinking>{thinking}</thinking><bash>{command}</bash>",
                }
            )
            messages.append({"role": "user", "content": f"<observation>{observation}</observation>"})

        return {"task": task, "steps": steps, "final_result": final_result}
