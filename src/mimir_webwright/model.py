from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class LiteLLMConfig:
    """Configuration for the LiteLLM OpenAI-compatible endpoint."""

    base_url: str = "http://localhost:4000/v1"
    api_key: str = ""
    model: str = "litellm/gpt-5.4"
    timeout_seconds: float = 120.0

    @classmethod
    def from_env(cls) -> LiteLLMConfig:
        return cls(
            base_url=os.environ.get("LITELLM_BASE_URL", cls.base_url),
            api_key=os.environ.get("LITELLM_API_KEY", ""),
            model=os.environ.get("LITELLM_MODEL", cls.model),
        )


class LiteLLMClient:
    """Minimal chat-completions client for LiteLLM's OpenAI-compatible API."""

    def __init__(
        self,
        config: LiteLLMConfig | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config or LiteLLMConfig.from_env()
        self._transport = transport
        if not self.config.api_key:
            raise RuntimeError("Missing LITELLM_API_KEY.")

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(
            timeout=self.config.timeout_seconds,
            transport=self._transport,
        ) as client:
            response = client.post(
                f"{self.config.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise RuntimeError("Expected string content from LiteLLM response.")
        parsed = httpx.Response(200, text=content).json()
        if not isinstance(parsed, dict):
            raise RuntimeError("Expected JSON object from LiteLLM response.")
        return parsed
