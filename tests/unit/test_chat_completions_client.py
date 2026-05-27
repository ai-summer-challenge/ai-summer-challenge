import httpx
import pytest

from pcf_pdf_extractor.infrastructure.llm.chat_completions_client import ChatCompletionsLlmClient


def test_strict_schema_sanitizer_removes_defaults_and_requires_all_properties() -> None:
    client = ChatCompletionsLlmClient(
        base_url="https://example.test/v1",
        api_key="test",
        model="test-model",
    )
    schema = {
        "title": "Example",
        "type": "object",
        "properties": {
            "gwp100": {"title": "GWP 100", "type": "number"},
            "gwp100_biogenic": {
                "default": None,
                "anyOf": [{"type": "number"}, {"type": "null"}],
            },
            "nested": {
                "type": "object",
                "properties": {"fulfilled": {"type": "boolean", "default": False}},
            },
        },
        "required": ["gwp100"],
    }

    sanitized = client._to_openai_strict_schema(schema)

    assert "title" not in sanitized
    assert sanitized["required"] == ["gwp100", "gwp100_biogenic", "nested"]
    assert sanitized["additionalProperties"] is False
    assert "default" not in sanitized["properties"]["gwp100_biogenic"]
    assert sanitized["properties"]["nested"]["required"] == ["fulfilled"]
    assert sanitized["properties"]["nested"]["additionalProperties"] is False


def test_strict_schema_sanitizer_removes_ref_sibling_keywords() -> None:
    client = ChatCompletionsLlmClient(
        base_url="https://example.test/v1",
        api_key="test",
        model="test-model",
    )
    schema = {
        "type": "object",
        "properties": {
            "minimum_requirements": {
                "$ref": "#/$defs/MinimumRequirements",
                "description": "Named checklist.",
            }
        },
        "$defs": {
            "MinimumRequirements": {
                "type": "object",
                "properties": {
                    "gwp100": {
                        "$ref": "#/$defs/RequirementCheck",
                        "description": "Mandatory GWP 100 value.",
                    }
                },
            },
            "RequirementCheck": {
                "type": "object",
                "properties": {"fulfilled": {"type": "boolean"}},
            },
        },
    }

    sanitized = client._to_openai_strict_schema(schema)

    assert sanitized["properties"]["minimum_requirements"] == {
        "$ref": "#/$defs/MinimumRequirements"
    }
    assert sanitized["$defs"]["MinimumRequirements"]["properties"]["gwp100"] == {
        "$ref": "#/$defs/RequirementCheck"
    }


def test_http_error_detail_uses_openai_error_message() -> None:
    client = ChatCompletionsLlmClient(
        base_url="https://example.test/v1",
        api_key="test",
        model="test-model",
    )
    response = httpx.Response(
        status_code=400,
        json={"error": {"message": "Invalid schema for response_format."}},
        request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
    )

    detail = client._response_error_detail(response)

    assert detail == "Invalid schema for response_format."


def test_complete_json_wraps_network_errors() -> None:
    client = ChatCompletionsLlmClient(
        base_url="https://example.test/v1",
        api_key="test",
        model="test-model",
    )

    original_post = httpx.Client.post

    def failing_post(*args, **kwargs):
        request = httpx.Request("POST", "https://example.test/v1/chat/completions")
        raise httpx.ConnectError("socket denied", request=request)

    httpx.Client.post = failing_post
    try:
        with pytest.raises(RuntimeError, match="LLM API network request failed"):
            client.complete_json(
                system_prompt="sys",
                user_prompt="usr",
                response_schema={"type": "object", "properties": {}},
            )
    finally:
        httpx.Client.post = original_post
