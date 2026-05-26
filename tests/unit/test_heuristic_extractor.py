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
    Secondary database: ecoinvent 3.9
    """

    record = HeuristicPcfExtractor().extract(text)

    assert record.company_name == "Example Chemicals"
    assert record.product_name == "Solvent X"
    assert record.gwp100.with_biogenic_carbon == 1.23
    assert record.gwp100.without_biogenic_carbon == 1.45
    assert record.system_boundary == "cradle-to-gate"
    assert "ISO 14067" in record.standards
    assert record.product_location == "France"
    assert record.reference_year == 2024
    assert record.impact_assessment_method == "IPCC AR6"
    assert record.secondary_databases[0].name == "ecoinvent"
    assert record.secondary_databases[0].version == "3.9"
    assert all(check.fulfilled for check in record.minimum_requirements)
