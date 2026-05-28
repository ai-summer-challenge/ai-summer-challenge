import json
from pathlib import Path
from typing import Any, Protocol

from pcf_pdf_extractor.domain import PCFExtractionResult, PCFRecord, assess_minimum_requirements


class JsonLlmClient(Protocol):
    """Minimal client interface needed by the LLM extractor."""

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a JSON object produced by an LLM."""


_DEFAULT_SYSTEM_PROMPT = (
    "You extract Product Carbon Footprint data from supplier documentation text and "
    "assess whether the documentation fulfills minimum requirements. "
    "Return only a valid JSON object with a top-level records array."
)

_DEFAULT_USER_PROMPT_TEMPLATE = (
    "{truncation_note}\n\n"
    "Return JSON matching this schema:\n"
    "{schema}\n\n"
    "Source text:\n"
    "```text\n"
    "{source_text}\n"
    "```"
)


class LlmPcfExtractor:
    """Extract PCF information from normalized source text with an LLM."""

    def __init__(
        self,
        client: JsonLlmClient,
        max_input_chars: int = 120_000,
        system_prompt_path: Path | None = None,
        user_prompt_path: Path | None = None,
    ) -> None:
        self._client = client
        self._max_input_chars = max_input_chars
        self._system_prompt_template = _load_prompt_file(system_prompt_path, _DEFAULT_SYSTEM_PROMPT)
        self._user_prompt_template = _load_prompt_file(user_prompt_path, _DEFAULT_USER_PROMPT_TEMPLATE)

    def extract(self, text: str) -> list[PCFRecord]:
        schema = PCFExtractionResult.model_json_schema()
        truncated_text = text[: self._max_input_chars]
        was_truncated = len(text) > len(truncated_text)

        payload = self._client.complete_json(
            system_prompt=self._system_prompt(),
            user_prompt=self._user_prompt(truncated_text, schema, was_truncated),
            response_schema=schema,
        )
        payload = self._normalize_extraction_payload(payload)
        result = PCFExtractionResult.model_validate(payload)
        for record in result.records:
            record.extraction_notes = [
                *record.extraction_notes,
                "Extracted with an LLM. Human review is required before shipping.",
            ]
            if was_truncated:
                record.extraction_notes.append(
                    f"LLM input was truncated to {self._max_input_chars} characters."
                )
            record.minimum_requirements = assess_minimum_requirements(record)
        return result.records

    def _normalize_extraction_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        records = payload.get("records")
        if isinstance(records, list):
            return {
                "records": [
                    self._normalize_record_payload(record)
                    for record in records
                    if isinstance(record, dict)
                ]
            }

        return {"records": [self._normalize_record_payload(payload)]}

    def _normalize_record_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        normalized.pop("expected_gwp100_reason", None)
        normalized.pop("oil_gas_relevant_reason", None)
        legacy_gwp100 = normalized.pop("gwp100", None)
        legacy_gwp100_biogenic = normalized.pop("gwp100_biogenic", None)
        legacy_gwp100_unit = normalized.pop("gwp100_unit", None)

        if isinstance(legacy_gwp100, dict):
            legacy_gwp100_biogenic = legacy_gwp100.get("with_biogenic_carbon")
            legacy_gwp100_unit = legacy_gwp100.get("unit")
            legacy_gwp100 = legacy_gwp100.get("without_biogenic_carbon")

        for field_name in [
            "expected_gwp100_value",
            "oil_gas_relevant",
            "is_benchmarch_ok",
            "oil_and_gas_check_ok",
        ]:
            normalized.setdefault(field_name, None)

        for field_name in [
            "extraction_notes",
        ]:
            if normalized.get(field_name) is None:
                normalized[field_name] = []

        minimum_requirements = normalized.get("minimum_requirements")
        if not isinstance(minimum_requirements, dict):
            minimum_requirements = {}
            normalized["minimum_requirements"] = minimum_requirements
        else:
            secondary_databases = minimum_requirements.get("secondary_databases")
            if isinstance(secondary_databases, dict):
                secondary_result = secondary_databases.get("result")
                if isinstance(secondary_result, list):
                    fulfilled = secondary_databases.get("fulfilled")
                    secondary_databases["result"] = (
                        bool(fulfilled) if isinstance(fulfilled, bool) else bool(secondary_result)
                    )

        self._set_legacy_pcf_requirement(
            minimum_requirements,
            field_name="gwp100_excluding_biogenic",
            value=legacy_gwp100,
            unit=legacy_gwp100_unit,
        )
        self._set_legacy_pcf_requirement(
            minimum_requirements,
            field_name="gwp100_including_biogenic",
            value=legacy_gwp100_biogenic,
            unit=legacy_gwp100_unit,
        )
        self._rename_legacy_requirement(
            minimum_requirements,
            old_name="gwp100",
            new_name="gwp100_excluding_biogenic",
        )
        self._rename_legacy_requirement(
            minimum_requirements,
            old_name="gwp100_biogenic",
            new_name="gwp100_including_biogenic",
        )
        self._fill_missing_requirement_defaults(minimum_requirements)
        self._normalize_enrichment_fields(normalized)

        return normalized

    def _set_legacy_pcf_requirement(
        self,
        minimum_requirements: dict[str, Any],
        *,
        field_name: str,
        value: Any,
        unit: Any,
    ) -> None:
        if field_name in minimum_requirements or value is None:
            return
        minimum_requirements[field_name] = {
            "fulfilled": True,
            "result": {"value": value, "unit": unit},
            "evidence": None,
            "reason": "Migrated from legacy top-level PCF field.",
        }

    def _rename_legacy_requirement(
        self,
        minimum_requirements: dict[str, Any],
        *,
        old_name: str,
        new_name: str,
    ) -> None:
        if new_name in minimum_requirements or old_name not in minimum_requirements:
            return
        minimum_requirements[new_name] = minimum_requirements.pop(old_name)

    def _fill_missing_requirement_defaults(self, minimum_requirements: dict[str, Any]) -> None:
        for field_name in [
            "gwp100_excluding_biogenic",
            "gwp100_including_biogenic",
            "system_boundary",
            "production_location",
            "reference_year",
            "impact_assessment_method",
        ]:
            minimum_requirements.setdefault(
                field_name,
                {
                    "fulfilled": False,
                    "result": None,
                    "evidence": None,
                    "reason": "No value was extracted.",
                },
            )

        minimum_requirements.setdefault(
            "oil_and_gas_update",
            {
                "fulfilled": False,
                "result": False,
                "evidence": None,
                "reason": "'Oil and gas update' was not found in the supplier documentation.",
            },
        )

        minimum_requirements.setdefault(
            "accepted_standard",
            {
                "fulfilled": False,
                "result": [],
                "evidence": None,
                "reason": "No value was extracted.",
            },
        )
        minimum_requirements.setdefault(
            "secondary_databases",
            {
                "fulfilled": False,
                "result": False,
                "evidence": None,
                "reason": "No value was extracted.",
            },
        )

    def _normalize_enrichment_fields(self, normalized: dict[str, Any]) -> None:
        expected = normalized.get("expected_gwp100_value")
        if isinstance(expected, dict) and "fulfilled" not in expected and "result" not in expected:
            normalized["expected_gwp100_value"] = {
                "fulfilled": True,
                "result": expected,
                "evidence": None,
                "reason": "Migrated from legacy expected_gwp100_value structure.",
            }
        elif expected is None:
            normalized["expected_gwp100_value"] = {
                "fulfilled": False,
                "result": None,
                "evidence": None,
                "reason": "No expected_gwp100_value was extracted.",
            }

        oil_gas = normalized.get("oil_gas_relevant")
        if isinstance(oil_gas, bool):
            normalized["oil_gas_relevant"] = {
                "fulfilled": True,
                "result": oil_gas,
                "evidence": None,
                "reason": "Migrated from legacy oil_gas_relevant boolean field.",
            }
        elif oil_gas is None:
            normalized["oil_gas_relevant"] = {
                "fulfilled": False,
                "result": False,
                "evidence": None,
                "reason": "No oil_gas_relevant value was extracted.",
            }

    def _system_prompt(self) -> str:
        return self._system_prompt_template

    def _user_prompt(
        self,
        source_text: str,
        schema: dict[str, Any],
        was_truncated: bool,
    ) -> str:
        truncation_note = (
            "The source text was truncated because it is long. Extract only from the text below."
            if was_truncated
            else "The complete extracted source text is below."
        )
        return self._user_prompt_template.format(
            truncation_note=truncation_note,
            schema=json.dumps(schema, indent=2),
            source_text=source_text,
        )


def _load_prompt_file(path: Path | None, fallback: str) -> str:
    if path is None:
        return fallback
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError:
        return fallback
    return content or fallback
