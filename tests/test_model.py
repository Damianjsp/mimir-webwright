from __future__ import annotations

from mimir_webwright.model import ModelEndpoint


def test_parse_response_extracts_thinking_and_bash() -> None:
    endpoint = ModelEndpoint()
    thinking, command = endpoint._parse_response(
        "<thinking>inspect the site</thinking><bash>python script.py</bash>"
    )

    assert thinking == "inspect the site"
    assert command == "python script.py"


def test_parse_response_falls_back_to_raw_content() -> None:
    endpoint = ModelEndpoint()
    thinking, command = endpoint._parse_response("plain output")

    assert thinking == ""
    assert command == "plain output"
