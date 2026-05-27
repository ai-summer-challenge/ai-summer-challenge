from pcf_pdf_extractor.extraction import HeuristicPcfExtractor


def test_heuristic_extractor_finds_common_pcf_fields() -> None:
    text = """
    Company: Example Chemicals
    Product name: Solvent X
    PCF GWP 100 with biogenic carbon: 1.23 kg CO2e/kg product
    PCF GWP 100 without biogenic carbon: 1.45 kg CO2e/kg product
    System boundary: cradle-to-gate
    Standard used: ISO 14040, ISO 14044, ISO 14067, TfS
    Product location: France
    Reference year of data collection: 2024
    Impact assessment method: IPCC AR6
    Secondary database: ecoinvent 3.10
    """

    records = HeuristicPcfExtractor().extract(text)
    record = records[0]

    assert len(records) == 1
    assert record.company_name == "Example Chemicals"
    assert record.product_name == "Solvent X"
    assert record.minimum_requirements.gwp100_excluding_biogenic.result is not None
    assert record.minimum_requirements.gwp100_excluding_biogenic.result.value == 1.45
    assert record.minimum_requirements.gwp100_including_biogenic.result is not None
    assert record.minimum_requirements.gwp100_including_biogenic.result.value == 1.23
    assert record.minimum_requirements.gwp100_excluding_biogenic.result.unit == (
        "kg CO2e/kg product"
    )
    assert record.minimum_requirements.system_boundary.result == "cradle-to-gate"
    assert "ISO 14067" in record.minimum_requirements.accepted_standard.result
    assert record.minimum_requirements.production_location.result == "France"
    assert record.minimum_requirements.reference_year.result == 2024
    assert record.minimum_requirements.impact_assessment_method.result == "IPCC AR6"
    assert record.minimum_requirements.secondary_databases.result[0].name == "ecoinvent"
    assert record.minimum_requirements.secondary_databases.result[0].version == "3.10"
    assert all(check["fulfilled"] for check in record.minimum_requirements.model_dump().values())
