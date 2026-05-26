from typing import Any

from pcf_pdf_extractor.extraction import LlmPcfExtractor


class FakeLlmClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.response_schema: dict[str, Any] | None = None

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.response_schema = response_schema
        assert "Product Carbon Footprint" in system_prompt
        assert "PDF text" in user_prompt
        return self.payload


def test_llm_extractor_validates_json_payload() -> None:
    client = FakeLlmClient(
        {
            "company_name": "Example Chemicals",
            "product_name": "Solvent X",
            "gwp100": {
                "with_biogenic_carbon": 1.23,
                "without_biogenic_carbon": 1.45,
                "unit": "kg CO2e/kg product",
            },
            "system_boundary": "cradle-to-gate",
            "standards": ["ISO 14040", "ISO 14044", "ISO 14067", "TfS"],
            "product_location": "France",
            "reference_year": 2024,
            "impact_assessment_method": "IPCC AR6",
            "secondary_databases": [{"name": "ecoinvent", "version": "3.9"}],
            "extraction_notes": ["The source uses a supplier declaration format."],
        }
    )

    record = LlmPcfExtractor(client=client).extract("Company: Example Chemicals")

    assert record.company_name == "Example Chemicals"
    assert record.gwp100.without_biogenic_carbon == 1.45
    assert record.secondary_databases[0].version == "3.9"
    assert record.minimum_requirements[0].criterion_id == "pcf_gwp100_values"
    assert record.minimum_requirements[0].fulfilled is True
    assert "Extracted with an LLM. Human review is required before shipping." in record.extraction_notes
    assert client.response_schema is not None


def test_llm_extractor_normalizes_null_collection_fields() -> None:
    client = FakeLlmClient(
        {
            "company_name": "Example Chemicals",
            "gwp100": None,
            "standards": None,
            "secondary_databases": None,
            "extraction_notes": None,
        }
    )

    record = LlmPcfExtractor(client=client).extract("Company: Example Chemicals")

    assert record.gwp100.with_biogenic_carbon is None
    assert record.standards == []
    assert record.secondary_databases == []
    assert record.minimum_requirements[0].fulfilled is False
