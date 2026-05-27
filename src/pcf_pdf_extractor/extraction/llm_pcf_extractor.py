import json
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


class LlmPcfExtractor:
    """Extract PCF information from PDF text with an LLM and validate the result."""

    def __init__(self, client: JsonLlmClient, max_input_chars: int = 120_000) -> None:
        self._client = client
        self._max_input_chars = max_input_chars

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
        legacy_gwp100 = normalized.pop("gwp100", None)
        legacy_gwp100_biogenic = normalized.pop("gwp100_biogenic", None)
        legacy_gwp100_unit = normalized.pop("gwp100_unit", None)

        if isinstance(legacy_gwp100, dict):
            legacy_gwp100_biogenic = legacy_gwp100.get("with_biogenic_carbon")
            legacy_gwp100_unit = legacy_gwp100.get("unit")
            legacy_gwp100 = legacy_gwp100.get("without_biogenic_carbon")

        for field_name in [
            "extraction_notes",
        ]:
            if normalized.get(field_name) is None:
                normalized[field_name] = []

        minimum_requirements = normalized.get("minimum_requirements")
        if not isinstance(minimum_requirements, dict):
            minimum_requirements = {}
            normalized["minimum_requirements"] = minimum_requirements

        self._set_legacy_pcf_requirement(
            minimum_requirements,
            field_name="gwp100",
            value=legacy_gwp100,
            unit=legacy_gwp100_unit,
        )
        self._set_legacy_pcf_requirement(
            minimum_requirements,
            field_name="gwp100_biogenic",
            value=legacy_gwp100_biogenic,
            unit=legacy_gwp100_unit,
        )
        self._fill_missing_requirement_defaults(minimum_requirements)

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

    def _fill_missing_requirement_defaults(self, minimum_requirements: dict[str, Any]) -> None:
        for field_name in [
            "gwp100",
            "gwp100_biogenic",
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

        for field_name in ["accepted_standard", "secondary_databases"]:
            minimum_requirements.setdefault(
                field_name,
                {
                    "fulfilled": False,
                    "result": [],
                    "evidence": None,
                    "reason": "No value was extracted.",
                },
            )

        minimum_requirements.setdefault(
            "approved_secondary_database",
            {
                "fulfilled": False,
                "result": [],
                "evidence": None,
                "reason": (
                    "Neither ecoinvent 3.10 nor Sphera Managed Content 2024 was found among "
                    "the secondary databases."
                ),
            },
        )

    def _system_prompt(self) -> str:
        return (
            "You extract Product Carbon Footprint data from supplier documentation text and "
            "assess whether the documentation fulfills minimum requirements. "
            "Return only a valid JSON object with a top-level records array. "
            "Create one records item for each distinct chemical or product with PCF data in "
            "the supplier documentation. Do not merge different chemicals into one record. "
            "If a document contains several chemicals/products in a table, return several "
            "records. If document-level facts such as system boundary, standard, production "
            "location, reference year, impact method, or databases apply to every chemical, "
            "repeat those facts in each relevant record. "
            "Do not infer facts that are not in the text. "
            "Use null for unknown scalar fields and [] for unknown list fields. "
            "For every record, return source_file and raw_text_sha256 as null; the application "
            "fills them after the LLM response. "
            "Do not return top-level fields named gwp100, gwp100_biogenic, gwp100_unit, "
            "system_boundary, standards, product_location, reference_year, "
            "impact_assessment_method, or secondary_databases. Put those extracted values "
            "inside minimum_requirements.<field>.result. "
            "minimum_requirements.gwp100.result must be an object with value and unit for "
            "the product PCF GWP 100 value excluding biogenic carbon. "
            "minimum_requirements.gwp100_biogenic.result must be an object with value and "
            "unit when the product PCF GWP 100 value including biogenic carbon is reported. "
            "If the document reports only one GWP 100 value and clearly indicates the product "
            "is fossil or not biobased, put that value in minimum_requirements.gwp100.result "
            "and leave minimum_requirements.gwp100_biogenic.result null while marking the "
            "biogenic requirement fulfilled by exception. "
            "Extract biogenic_carbon_content when stated, and set "
            "is_fossil_or_non_biobased_product only when the text says the product is fossil, "
            "not biobased, non-biobased, or has zero biogenic carbon content. "
            "Preserve standard names and impact assessment method names as written, for example "
            "TfS, ISO 14040, ISO 14044, ISO 14067, IPCC AR6, CML2001. "
            "For secondary emission factor databases, only ecoinvent 3.10 and Sphera "
            "Managed Content 2024 are accepted. These are the only allowed secondary "
            "databases. Return extracted secondary database objects with name and version in "
            "minimum_requirements.secondary_databases.result, and mark fulfilled false if any "
            "database other than ecoinvent 3.10 or Sphera Managed Content 2024 is used. "
            "Also check whether the exact phrase or clear wording 'oil and gas update' is "
            "mentioned anywhere in the documentation; put that boolean answer in "
            "minimum_requirements.oil_and_gas_update.result. "
            "Also check whether ecoinvent 3.10 or Sphera Managed Content 2024 is used as a "
            "secondary emission factor database; put matching database objects in "
            "minimum_requirements.approved_secondary_database.result. "
            "For minimum_requirements, return a named object, not a list. Do not include "
            "criterion_id. It must contain these fields: gwp100, gwp100_biogenic, "
            "system_boundary, accepted_standard, production_location, reference_year, "
            "impact_assessment_method, secondary_databases, oil_and_gas_update, "
            "approved_secondary_database. "
            "Every minimum_requirements field must contain fulfilled, result, evidence, "
            "and reason. If fulfilled is true, result must contain the extracted value or "
            "values. For example, production_location.result can be 'US', "
            "system_boundary.result can be 'cradle-to-gate', reference_year.result can be "
            "2024, and accepted_standard.result can be ['ISO 14067']. "
            "Mark fulfilled true only when the supplier documentation contains enough evidence. "
            "For minimum_requirements.gwp100, fulfilled true requires a numeric GWP 100 value "
            "excluding biogenic carbon in result.value. "
            "For minimum_requirements.gwp100_biogenic, fulfilled true requires a numeric "
            "GWP 100 value including biogenic carbon in result.value, except that it is also "
            "fulfilled with result null when the documentation indicates the product is fossil "
            "or not biobased, for example biogenic carbon content equals 0. "
            "For accepted_standard, fulfilled true only for TfS guideline, ISO 14040/14044 "
            "together, or ISO 14067. Other standards do not fulfill this criterion. "
            "For secondary_databases, fulfilled true only when the documented secondary "
            "databases are limited to ecoinvent 3.10 and/or Sphera Managed Content 2024. "
            "Any other database or version means fulfilled false. "
            "For oil_and_gas_update, fulfilled and result must both be true only when oil and "
            "gas update is mentioned; otherwise fulfilled false and result false. "
            "For approved_secondary_database, fulfilled true only when the secondary databases "
            "include ecoinvent version 3.10 or Sphera Managed Content version 2024. "
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
            "1. gwp100: mandatory numeric product PCF GWP 100 value excluding biogenic carbon. "
            "If fulfilled, result must be {\"value\": number, \"unit\": string or null}.\n"
            "2. gwp100_biogenic: numeric product PCF GWP 100 value including biogenic carbon. "
            "Exception: if the documentation indicates the product is fossil or not biobased, "
            "such as biogenic carbon content = 0, gwp100 alone is sufficient and this "
            "requirement is fulfilled by the exception. If a value is present, result must be "
            "{\"value\": number, \"unit\": string or null}; if fulfilled by exception, "
            "result must be null.\n"
            "3. system_boundary: the PCF calculation system boundary must be documented, for "
            "example cradle-to-gate.\n"
            "4. accepted_standard: only TfS guideline, ISO 14040/14044 together, or ISO 14067 "
            "are accepted.\n"
            "5. production_location: country or region must be documented.\n"
            "6. reference_year: reference year of data collection must be documented.\n"
            "7. impact_assessment_method: PCF impact assessment method must be documented, "
            "for example IPCC AR6, CML2001, ISO14067, or another named method.\n"
            "8. secondary_databases: secondary emission factor databases must be documented "
            "and must be limited to ecoinvent 3.10 and/or Sphera Managed Content 2024. "
            "Any other database or version fails this requirement.\n"
            "9. oil_and_gas_update: whether 'oil and gas update' is mentioned anywhere in "
            "the documentation. Use result true or false.\n"
            "10. approved_secondary_database: whether ecoinvent 3.10 or Sphera Managed "
            "Content 2024 is used as a secondary emission factor database. Use result as a "
            "list of matching database objects.\n\n"
            "For every checklist item, add one named minimum_requirements field with fulfilled true "
            "or false. When evidence is missing or ambiguous, fulfilled must be false. "
            "When fulfilled is true, include the extracted answer in result, except for "
            "gwp100_biogenic fulfilled by fossil/non-biobased exception where result is null.\n\n"
            "Return JSON matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "PDF text:\n"
            "```text\n"
            f"{pdf_text}\n"
            "```"
        )
