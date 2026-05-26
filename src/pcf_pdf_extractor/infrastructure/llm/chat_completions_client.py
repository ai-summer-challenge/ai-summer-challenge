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
        payload = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
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
            response.raise_for_status()

        response_payload = response.json()
        content = response_payload["choices"][0]["message"]["content"]
        parsed = self._parse_json_object(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response was valid JSON but not a JSON object")
        return parsed

    def _parse_json_object(self, content: str) -> Any:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if match is None:
                raise
            return json.loads(match.group(0))
