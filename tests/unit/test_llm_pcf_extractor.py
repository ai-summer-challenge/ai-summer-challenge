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
        assert "Source text" in user_prompt
        return self.payload


def test_llm_extractor_validates_json_payload() -> None:
    client = FakeLlmClient(
        {
            "records": [
                {
                    "company_name": "Example Chemicals",
                    "product_name": "Solvent X",
                    "minimum_requirements": {
                        "gwp100_excluding_biogenic": {
                            "fulfilled": True,
                            "result": {"value": 1.45, "unit": "kg CO2e/kg product"},
                            "evidence": (
                                "PCF GWP 100 without biogenic carbon: "
                                "1.45 kg CO2e/kg product"
                            ),
                            "reason": "Value found.",
                        },
                        "gwp100_including_biogenic": {
                            "fulfilled": True,
                            "result": {"value": 1.23, "unit": "kg CO2e/kg product"},
                            "evidence": "PCF GWP 100 with biogenic carbon: 1.23 kg CO2e/kg product",
                            "reason": "Value found.",
                        },
                        "system_boundary": {
                            "fulfilled": True,
                            "result": "cradle-to-gate",
                            "evidence": "System boundary: cradle-to-gate",
                            "reason": "Boundary found.",
                        },
                        "accepted_standard": {
                            "fulfilled": True,
                            "result": ["ISO 14040", "ISO 14044", "ISO 14067", "TfS"],
                            "evidence": "Standard used: ISO 14040, ISO 14044, ISO 14067, TfS",
                            "reason": "Accepted standards found.",
                        },
                        "production_location": {
                            "fulfilled": True,
                            "result": "France",
                            "evidence": "Product location: France",
                            "reason": "Location found.",
                        },
                        "reference_year": {
                            "fulfilled": True,
                            "result": 2024,
                            "evidence": "Reference year: 2024",
                            "reason": "Year found.",
                        },
                        "impact_assessment_method": {
                            "fulfilled": True,
                            "result": "IPCC AR6",
                            "evidence": "Impact assessment method: IPCC AR6",
                            "reason": "Method found.",
                        },
                        "secondary_databases": {
                            "fulfilled": True,
                            "result": [{"name": "ecoinvent", "version": "3.9"}],
                            "evidence": "Secondary database: ecoinvent 3.9",
                            "reason": "Database and version found.",
                        },
                    },
                    "extraction_notes": ["The source uses a supplier declaration format."],
                }
            ],
        }
    )

    records = LlmPcfExtractor(client=client).extract("Company: Example Chemicals")
    record = records[0]

    assert len(records) == 1
    assert record.company_name == "Example Chemicals"
    assert record.minimum_requirements.gwp100_excluding_biogenic.fulfilled is True
    assert record.minimum_requirements.gwp100_excluding_biogenic.result is not None
    assert record.minimum_requirements.gwp100_excluding_biogenic.result.value == 1.45
    assert record.minimum_requirements.gwp100_including_biogenic.fulfilled is True
    assert record.minimum_requirements.gwp100_including_biogenic.result is not None
    assert record.minimum_requirements.gwp100_including_biogenic.result.value == 1.23
    assert record.minimum_requirements.secondary_databases.result[0].version == "3.9"
    assert "Extracted with an LLM. Human review is required before shipping." in record.extraction_notes
    assert client.response_schema is not None


def test_llm_extractor_normalizes_null_collection_fields() -> None:
    client = FakeLlmClient(
        {
            "company_name": "Example Chemicals",
            "gwp100": 1.45,
            "gwp100_unit": "kg CO2e/kg product",
            "extraction_notes": None,
        }
    )

    records = LlmPcfExtractor(client=client).extract("Company: Example Chemicals")
    record = records[0]

    assert len(records) == 1
    assert record.minimum_requirements.gwp100_excluding_biogenic.fulfilled is True
    assert record.minimum_requirements.gwp100_excluding_biogenic.result is not None
    assert record.minimum_requirements.gwp100_excluding_biogenic.result.value == 1.45
    assert record.minimum_requirements.gwp100_including_biogenic.fulfilled is False


def test_llm_extractor_accepts_legacy_gwp100_object_payload() -> None:
    client = FakeLlmClient(
        {
            "company_name": "Example Chemicals",
            "gwp100": {
                "with_biogenic_carbon": 1.23,
                "without_biogenic_carbon": 1.45,
                "unit": "kg CO2e/kg product",
            },
        }
    )

    records = LlmPcfExtractor(client=client).extract("Company: Example Chemicals")
    record = records[0]

    assert len(records) == 1
    assert record.minimum_requirements.gwp100_excluding_biogenic.result is not None
    assert record.minimum_requirements.gwp100_excluding_biogenic.result.value == 1.45
    assert record.minimum_requirements.gwp100_including_biogenic.result is not None
    assert record.minimum_requirements.gwp100_including_biogenic.result.value == 1.23
    assert record.minimum_requirements.gwp100_excluding_biogenic.result.unit == (
        "kg CO2e/kg product"
    )


def test_llm_extractor_returns_one_record_per_chemical() -> None:
    client = FakeLlmClient(
        {
            "records": [
                {
                    "company_name": "Supplier",
                    "product_name": "Chemical A",
                    "gwp100": 1.1,
                    "gwp100_unit": "kg CO2e/kg product",
                },
                {
                    "company_name": "Supplier",
                    "product_name": "Chemical B",
                    "gwp100": 2.2,
                    "gwp100_unit": "kg CO2e/kg product",
                },
            ]
        }
    )

    records = LlmPcfExtractor(client=client).extract("two chemicals")

    assert [record.product_name for record in records] == ["Chemical A", "Chemical B"]
    assert records[0].minimum_requirements.gwp100_excluding_biogenic.result is not None
    assert records[0].minimum_requirements.gwp100_excluding_biogenic.result.value == 1.1
    assert records[1].minimum_requirements.gwp100_excluding_biogenic.result is not None
    assert records[1].minimum_requirements.gwp100_excluding_biogenic.result.value == 2.2
