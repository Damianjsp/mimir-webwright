"""LiteLLM-compatible model adapter."""

from __future__ import annotations

import os
import re
from typing import Final

from openai import OpenAI

DEFAULT_BASE_URL: Final[str] = "http://localhost:4000"
DEFAULT_MODEL: Final[str] = "gpt-5.4"


class ModelEndpoint:
    """Adapter for an OpenAI-compatible LiteLLM endpoint."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL) -> None:
        self.client = OpenAI(
            base_url=base_url,
            api_key=os.environ.get("LITELLM_API_KEY", "dummy"),
        )
        self.model = model

    def complete(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        """Return the model's parsed thinking and bash command."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        content = response.choices[0].message.content or ""
        return self._parse_response(content)

    def _parse_response(self, content: str) -> tuple[str, str]:
        """Extract <thinking> and <bash> blocks from a model response."""
        thinking_match = re.search(r"<thinking>(.*?)</thinking>", content, re.DOTALL)
        bash_match = re.search(r"<bash>(.*?)</bash>", content, re.DOTALL)
        return (
            thinking_match.group(1).strip() if thinking_match else "",
            bash_match.group(1).strip() if bash_match else content.strip(),
        )
