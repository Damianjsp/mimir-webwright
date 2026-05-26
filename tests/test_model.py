from __future__ import annotations

import json

import httpx
import pytest
from mimir_webwright.model import LiteLLMClient, LiteLLMConfig


def test_complete_json_posts_openai_compatible_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"bash_command": "echo hello", "done": False})
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = LiteLLMClient(
        LiteLLMConfig(base_url="http://localhost:4000/v1", api_key="test-key"),
        transport=transport,
    )
    result = client.complete_json(system_prompt="sys", user_prompt="user")

    assert captured["url"] == "http://localhost:4000/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "litellm/gpt-5.4"
    assert payload["response_format"] == {"type": "json_object"}
    assert result == {"bash_command": "echo hello", "done": False}


def test_missing_api_key_raises() -> None:
    with pytest.raises(RuntimeError, match="Missing LITELLM_API_KEY"):
        LiteLLMClient(LiteLLMConfig(api_key=""))
