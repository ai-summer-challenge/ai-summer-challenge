import json
import re
from typing import Any

import httpx

from pcf_pdf_extractor.config import Settings


class ChatCompletionsLlmClient:
    """Adapter for OpenAI-compatible chat completions APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "ChatCompletionsLlmClient":
        if settings.llm_api_base_url is None:
            raise ValueError("LLM_API_BASE_URL is required for LLM extraction")
        if settings.llm_api_key is None:
            raise ValueError("LLM_API_KEY is required for LLM extraction")
        if settings.llm_model is None:
            raise ValueError("LLM_MODEL is required for LLM extraction")

        return cls(
            base_url=str(settings.llm_api_base_url),
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        strict_schema = self._to_openai_strict_schema(response_schema)
        payload = {
            "model": self._model,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "pcf_record",
                    "strict": True,
                    "schema": strict_schema,
                },
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            self._raise_for_status(response)

        response_payload = response.json()
        content = response_payload["choices"][0]["message"]["content"]
        parsed = self._parse_json_object(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response was valid JSON but not a JSON object")
        return parsed

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._response_error_detail(response)
            raise RuntimeError(
                f"LLM API request failed with HTTP {response.status_code}: {detail}"
            ) from exc

    def _response_error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return response.text[:2_000]

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str):
                    return message
            return json.dumps(payload, ensure_ascii=False)[:2_000]
        return str(payload)[:2_000]

    def _to_openai_strict_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Convert a Pydantic JSON Schema into OpenAI strict Structured Outputs shape."""

        sanitized = self._sanitize_schema_node(schema)
        if not isinstance(sanitized, dict):
            raise ValueError("Response schema must be a JSON object schema")
        return sanitized

    def _sanitize_schema_node(self, node: Any) -> Any:
        if isinstance(node, list):
            return [self._sanitize_schema_node(item) for item in node]
        if not isinstance(node, dict):
            return node

        unsupported_keys = {
            "default",
            "examples",
            "readOnly",
            "writeOnly",
            "deprecated",
            "title",
            "format",
            "maximum",
            "maxItems",
            "maxLength",
            "minimum",
            "minItems",
            "minLength",
            "multipleOf",
            "pattern",
            "uniqueItems",
        }
        sanitized = {
            key: self._sanitize_schema_node(value)
            for key, value in node.items()
            if key not in unsupported_keys
        }

        if "$ref" in sanitized:
            return {"$ref": sanitized["$ref"]}

        properties = sanitized.get("properties")
        if isinstance(properties, dict):
            sanitized["additionalProperties"] = False
            sanitized["required"] = list(properties.keys())

        defs = sanitized.get("$defs")
        if isinstance(defs, dict):
            sanitized["$defs"] = {
                name: self._sanitize_schema_node(definition)
                for name, definition in defs.items()
            }

        return sanitized

    def _parse_json_object(self, content: str) -> Any:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if match is None:
                raise
            return json.loads(match.group(0))
