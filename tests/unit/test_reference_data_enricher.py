from pathlib import Path
from typing import Any

from openpyxl import Workbook

from pcf_pdf_extractor.domain import (
    BooleanRequirementCheck,
    MinimumRequirements,
    PCFRecord,
    PcfValueRequirementCheck,
    StandardsRequirementCheck,
    TextRequirementCheck,
    YearRequirementCheck,
)
from pcf_pdf_extractor.enrichment import BafuReferenceData, ReferenceDataEnricher


class FakeMappingClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.user_prompt: str | None = None

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        assert "chemical mapping" in system_prompt
        assert response_schema["properties"]["bafu_row"]["anyOf"]
        self.user_prompt = user_prompt
        return self.payload


def test_bafu_candidate_lookup_uses_simple_chemical_synonyms(tmp_path: Path) -> None:
    bafu_path = _write_bafu_workbook(tmp_path)
    reference = BafuReferenceData.from_excel(bafu_path)

    candidates = reference.candidate_rows(product_name="Natronlauge 50%", limit=3)

    assert candidates[0].row_number == 3
    assert candidates[0].product == "Sodium hydroxide, 50% in H2O, at plant {RER}"


def test_reference_data_enricher_adds_expected_gwp_and_oil_gas_flag(
    tmp_path: Path,
) -> None:
    bafu_path = _write_bafu_workbook(tmp_path)
    oil_gas_path = tmp_path / "EclasseswithOilGasRelevance.txt"
    oil_gas_path.write_text("Natronlauge\nAmmoniak\n", encoding="utf-8")
    prompt_path = tmp_path / "prompt_mapping.txt"
    prompt_path.write_text("You are an expert in chemical mapping.", encoding="utf-8")
    client = FakeMappingClient(
        {
            "bafu_row": 3,
            "oil_gas_relevant": True,
            "clarification_needed": False,
            "reason": "",
        }
    )
    record = PCFRecord(
        product_name="Natronlauge 50%",
        production_information="Produced as a 50% aqueous sodium hydroxide solution.",
        minimum_requirements=_minimum_requirements(
            production_location="Europe",
            secondary_databases=True,
        ),
    )

    enricher = ReferenceDataEnricher.from_paths(
        client=client,
        bafu_path=bafu_path,
        oil_gas_path=oil_gas_path,
        prompt_path=prompt_path,
        candidate_limit=5,
    )
    enriched = enricher.enrich(record)

    assert enriched.expected_gwp100_value is not None
    assert enriched.expected_gwp100_value.fulfilled is True
    assert enriched.expected_gwp100_value.result is not None
    assert enriched.expected_gwp100_value.result.value == 0.62
    assert enriched.expected_gwp100_value.result.unit == "kg CO2 eq/kg"
    assert enriched.expected_gwp100_value.reason
    assert enriched.oil_gas_relevant is not None
    assert enriched.oil_gas_relevant.fulfilled is True
    assert enriched.oil_gas_relevant.result is True
    assert enriched.oil_gas_relevant.reason
    assert enriched.is_benchmarch_ok is False
    assert enriched.oil_and_gas_check_ok is True
    assert client.user_prompt is not None
    assert "BAFU_CANDIDATE_ROWS" in client.user_prompt
    assert "Produced as a 50% aqueous sodium hydroxide solution." in client.user_prompt
    assert "Sodium hydroxide, 50% in H2O, at plant {RER}" in client.user_prompt


def test_oil_and_gas_check_passes_when_product_is_not_oil_gas_relevant(
    tmp_path: Path,
) -> None:
    bafu_path = _write_bafu_workbook(tmp_path)
    oil_gas_path = tmp_path / "EclasseswithOilGasRelevance.txt"
    oil_gas_path.write_text("Ammoniak\n", encoding="utf-8")
    prompt_path = tmp_path / "prompt_mapping.txt"
    prompt_path.write_text("You are an expert in chemical mapping.", encoding="utf-8")
    client = FakeMappingClient(
        {
            "bafu_row": 3,
            "oil_gas_relevant": False,
            "clarification_needed": False,
            "reason": "",
        }
    )
    record = PCFRecord(
        product_name="Natronlauge 50%",
        minimum_requirements=_minimum_requirements(
            production_location="Europe",
            secondary_databases=False,
        ),
    )

    enriched = ReferenceDataEnricher.from_paths(
        client=client,
        bafu_path=bafu_path,
        oil_gas_path=oil_gas_path,
        prompt_path=prompt_path,
        candidate_limit=5,
    ).enrich(record)

    assert enriched.oil_gas_relevant is not None
    assert enriched.oil_gas_relevant.result is False
    assert enriched.oil_and_gas_check_ok is True


def _write_bafu_workbook(tmp_path: Path) -> Path:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append([None, None, None, None, None, None, None, "IPCC 2021"])
    worksheet.append(
        [
            "Product",
            "Unit",
            "Category",
            "Sub-category 1",
            "Sub-category 2",
            "Sub-category 3",
            "Sub-category 4",
            "GWP 100 [kg CO2 eq]",
        ]
    )
    worksheet.append(
        [
            "Sodium hydroxide, 50% in H2O, at plant {RER}",
            "kg",
            "chemicals",
            "inorganic",
            None,
            None,
            None,
            0.62,
        ]
    )
    worksheet.append(
        [
            "Sodium chloride, powder, at plant {RER}",
            "kg",
            "chemicals",
            "inorganic",
            None,
            None,
            None,
            0.12,
        ]
    )
    path = tmp_path / "BAFU Extract.xlsx"
    workbook.save(path)
    return path


def _minimum_requirements(
    production_location: str | None = None,
    secondary_databases: bool | None = None,
) -> MinimumRequirements:
    return MinimumRequirements(
        gwp100_excluding_biogenic=PcfValueRequirementCheck(
            fulfilled=False,
            result=None,
            evidence=None,
            reason="",
        ),
        gwp100_including_biogenic=PcfValueRequirementCheck(
            fulfilled=False,
            result=None,
            evidence=None,
            reason="",
        ),
        system_boundary=TextRequirementCheck(
            fulfilled=False,
            result=None,
            evidence=None,
            reason="",
        ),
        accepted_standard=StandardsRequirementCheck(
            fulfilled=False,
            result=[],
            evidence=None,
            reason="",
        ),
        production_location=TextRequirementCheck(
            fulfilled=production_location is not None,
            result=production_location,
            evidence=None,
            reason="",
        ),
        reference_year=YearRequirementCheck(
            fulfilled=False,
            result=None,
            evidence=None,
            reason="",
        ),
        impact_assessment_method=TextRequirementCheck(
            fulfilled=False,
            result=None,
            evidence=None,
            reason="",
        ),
        secondary_databases=BooleanRequirementCheck(
            fulfilled=secondary_databases is True,
            result=secondary_databases,
            evidence=None,
            reason="",
        ),
        oil_and_gas_update=BooleanRequirementCheck(
            fulfilled=False,
            result=False,
            evidence=None,
            reason="",
        ),
    )
