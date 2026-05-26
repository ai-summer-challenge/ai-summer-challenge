import json
from typing import Any, Protocol

from pcf_pdf_extractor.domain import PCFRecord, assess_minimum_requirements


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


class LlmPcfExtractor:
    """Extract PCF information from PDF text with an LLM and validate the result."""

    def __init__(self, client: JsonLlmClient, max_input_chars: int = 120_000) -> None:
        self._client = client
        self._max_input_chars = max_input_chars

    def extract(self, text: str) -> PCFRecord:
        schema = PCFRecord.model_json_schema()
        truncated_text = text[: self._max_input_chars]
        was_truncated = len(text) > len(truncated_text)

        payload = self._client.complete_json(
            system_prompt=self._system_prompt(),
            user_prompt=self._user_prompt(truncated_text, schema, was_truncated),
            response_schema=schema,
        )
        payload = self._normalize_payload(payload)
        record = PCFRecord.model_validate(payload)
        record.extraction_notes = [
            *record.extraction_notes,
            "Extracted with an LLM. Human review is required before shipping.",
        ]
        if was_truncated:
            record.extraction_notes.append(
                f"LLM input was truncated to {self._max_input_chars} characters."
            )
        record.minimum_requirements = assess_minimum_requirements(record)
        return record

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)

        if normalized.get("gwp100") is None:
            normalized["gwp100"] = {}

        for field_name in [
            "standards",
            "secondary_databases",
            "minimum_requirements",
            "extraction_notes",
        ]:
            if normalized.get(field_name) is None:
                normalized[field_name] = []

        return normalized

    def _system_prompt(self) -> str:
        return (
            "You extract Product Carbon Footprint data from supplier documentation text and "
            "assess whether the documentation fulfills minimum requirements. "
            "Return only a valid JSON object. Do not infer facts that are not in the text. "
            "Use null for unknown scalar fields, [] for unknown list fields, and {} for "
            "unknown nested objects. "
            "PCF GWP 100 values must be numbers only; put units in gwp100.unit. "
            "Extract biogenic_carbon_content when stated, and set "
            "is_fossil_or_non_biobased_product only when the text says the product is fossil, "
            "not biobased, non-biobased, or has zero biogenic carbon content. "
            "Preserve standard names and impact assessment method names as written, for example "
            "TfS, ISO 14040, ISO 14044, ISO 14067, IPCC AR6, CML2001. "
            "For secondary emission factor databases, return one object per database with name "
            "and version when a version is available. "
            "For minimum_requirements, return exactly one check for each criterion_id: "
            "pcf_gwp100_values, system_boundary, accepted_standard, production_location, "
            "reference_year, impact_assessment_method, secondary_databases. "
            "Mark fulfilled true only when the supplier documentation contains enough evidence. "
            "For pcf_gwp100_values, fulfilled true requires both GWP 100 values including and "
            "excluding biogenic carbon, except that one value excluding biogenic carbon is enough "
            "only when the documentation indicates the product is fossil or not biobased, for "
            "example biogenic carbon content equals 0. "
            "For accepted_standard, fulfilled true only for TfS guideline, ISO 14040/14044 "
            "together, or ISO 14067. Other standards do not fulfill this criterion. "
            "For secondary_databases, fulfilled true only when database names and versions are "
            "documented. "
            "Missing, ambiguous, or unsupported evidence means fulfilled false. "
            "Each check must include concise evidence and reason. "
            "Add short extraction_notes for uncertain fields, missing fields, or ambiguous wording."
        )

    def _user_prompt(
        self,
        pdf_text: str,
        schema: dict[str, Any],
        was_truncated: bool,
    ) -> str:
        truncation_note = (
            "The PDF text was truncated because it is long. Extract only from the text below."
            if was_truncated
            else "The complete extracted PDF text is below."
        )
        return (
            f"{truncation_note}\n\n"
            "Minimum requirement checklist to assess:\n"
            "1. pcf_gwp100_values: two product PCF GWP 100 values are required, one including "
            "and one excluding biogenic carbon. Exception: if the documentation indicates the "
            "product is fossil or not biobased, such as biogenic carbon content = 0, one value "
            "excluding biogenic carbon is sufficient.\n"
            "2. system_boundary: the PCF calculation system boundary must be documented, for "
            "example cradle-to-gate.\n"
            "3. accepted_standard: only TfS guideline, ISO 14040/14044 together, or ISO 14067 "
            "are accepted.\n"
            "4. production_location: country or region must be documented.\n"
            "5. reference_year: reference year of data collection must be documented.\n"
            "6. impact_assessment_method: PCF impact assessment method must be documented, "
            "for example IPCC AR6, CML2001, ISO14067, or another named method.\n"
            "7. secondary_databases: secondary emission factor database names and versions "
            "must be documented.\n\n"
            "For every checklist item, add one minimum_requirements entry with fulfilled true "
            "or false. When evidence is missing or ambiguous, fulfilled must be false.\n\n"
            "Return JSON matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "PDF text:\n"
            "```text\n"
            f"{pdf_text}\n"
            "```"
        )
