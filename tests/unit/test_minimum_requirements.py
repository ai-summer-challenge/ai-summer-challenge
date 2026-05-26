from pcf_pdf_extractor.domain import Gwp100Values, PCFRecord, SecondaryDatabase
from pcf_pdf_extractor.domain.minimum_requirements import assess_minimum_requirements


def _checks_by_id(record: PCFRecord) -> dict[str, bool]:
    return {check.criterion_id: check.fulfilled for check in assess_minimum_requirements(record)}


def test_assessment_fulfills_all_requirements_with_two_pcf_values() -> None:
    record = PCFRecord(
        gwp100=Gwp100Values(
            with_biogenic_carbon=1.23,
            without_biogenic_carbon=1.45,
            unit="kg CO2e/kg product",
        ),
        system_boundary="cradle-to-gate",
        standards=["ISO 14040", "ISO 14044"],
        product_location="France",
        reference_year=2024,
        impact_assessment_method="IPCC AR6",
        secondary_databases=[SecondaryDatabase(name="ecoinvent", version="3.9")],
    )

    assert all(_checks_by_id(record).values())


def test_assessment_accepts_one_pcf_value_for_fossil_exception() -> None:
    record = PCFRecord(
        biogenic_carbon_content="0%",
        gwp100=Gwp100Values(without_biogenic_carbon=1.45, unit="kg CO2e/kg product"),
    )

    checks = _checks_by_id(record)

    assert checks["pcf_gwp100_values"] is True


def test_assessment_rejects_unaccepted_standard_and_missing_database_version() -> None:
    record = PCFRecord(
        standards=["GHG Protocol"],
        secondary_databases=[SecondaryDatabase(name="ecoinvent")],
    )

    checks = _checks_by_id(record)

    assert checks["accepted_standard"] is False
    assert checks["secondary_databases"] is False
