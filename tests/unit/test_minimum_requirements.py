from pcf_pdf_extractor.domain import (
    BooleanRequirementCheck,
    MinimumRequirements,
    PCFRecord,
    PcfValueRequirementCheck,
    PcfValueResult,
    SecondaryDatabase,
    SecondaryDatabasesRequirementCheck,
    StandardsRequirementCheck,
    TextRequirementCheck,
    YearRequirementCheck,
)
from pcf_pdf_extractor.domain.minimum_requirements import assess_minimum_requirements


def _requirements(
    *,
    gwp100: PcfValueResult | None = None,
    gwp100_biogenic: PcfValueResult | None = None,
    system_boundary: str | None = None,
    standards: list[str] | None = None,
    production_location: str | None = None,
    reference_year: int | None = None,
    impact_assessment_method: str | None = None,
    secondary_databases: list[SecondaryDatabase] | None = None,
    oil_and_gas_update: bool = False,
) -> MinimumRequirements:
    return MinimumRequirements(
        gwp100=PcfValueRequirementCheck(
            fulfilled=False,
            result=gwp100,
            evidence=None,
            reason="",
        ),
        gwp100_biogenic=PcfValueRequirementCheck(
            fulfilled=False,
            result=gwp100_biogenic,
            evidence=None,
            reason="",
        ),
        system_boundary=TextRequirementCheck(
            fulfilled=False,
            result=system_boundary,
            evidence=None,
            reason="",
        ),
        accepted_standard=StandardsRequirementCheck(
            fulfilled=False,
            result=standards or [],
            evidence=None,
            reason="",
        ),
        production_location=TextRequirementCheck(
            fulfilled=False,
            result=production_location,
            evidence=None,
            reason="",
        ),
        reference_year=YearRequirementCheck(
            fulfilled=False,
            result=reference_year,
            evidence=None,
            reason="",
        ),
        impact_assessment_method=TextRequirementCheck(
            fulfilled=False,
            result=impact_assessment_method,
            evidence=None,
            reason="",
        ),
        secondary_databases=SecondaryDatabasesRequirementCheck(
            fulfilled=False,
            result=secondary_databases or [],
            evidence=None,
            reason="",
        ),
        oil_and_gas_update=BooleanRequirementCheck(
            fulfilled=False,
            result=oil_and_gas_update,
            evidence=None,
            reason="",
        ),
        approved_secondary_database=SecondaryDatabasesRequirementCheck(
            fulfilled=False,
            result=[],
            evidence=None,
            reason="",
        ),
    )


def _assessed(record: PCFRecord):
    return assess_minimum_requirements(record)


def test_assessment_fulfills_all_requirements_with_two_pcf_values() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100=PcfValueResult(value=1.45, unit="kg CO2e/kg product"),
            gwp100_biogenic=PcfValueResult(value=1.23, unit="kg CO2e/kg product"),
            system_boundary="cradle-to-gate",
            standards=["ISO 14040", "ISO 14044"],
            production_location="France",
            reference_year=2024,
            impact_assessment_method="IPCC AR6",
            secondary_databases=[SecondaryDatabase(name="ecoinvent", version="3.10")],
            oil_and_gas_update=True,
        ),
    )

    checks = _assessed(record)

    assert all(check["fulfilled"] for check in checks.model_dump().values())


def test_assessment_accepts_one_pcf_value_for_fossil_exception() -> None:
    record = PCFRecord(
        biogenic_carbon_content="0%",
        minimum_requirements=_requirements(
            gwp100=PcfValueResult(value=1.45, unit="kg CO2e/kg product"),
        ),
    )

    checks = _assessed(record)

    assert checks.gwp100.fulfilled is True
    assert checks.gwp100_biogenic.fulfilled is True


def test_assessment_rejects_unaccepted_standard_and_missing_database_version() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100=PcfValueResult(value=1.45, unit="kg CO2e/kg product"),
            standards=["GHG Protocol"],
            secondary_databases=[SecondaryDatabase(name="ecoinvent")],
        ),
    )

    checks = _assessed(record)

    assert checks.accepted_standard.fulfilled is False
    assert checks.secondary_databases.fulfilled is False


def test_assessment_accepts_sphera_managed_content_2024() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100=PcfValueResult(value=1.45, unit="kg CO2e/kg product"),
            secondary_databases=[
                SecondaryDatabase(name="Sphera Managed Content", version="2024")
            ],
        ),
    )

    checks = _assessed(record)

    assert checks.approved_secondary_database.fulfilled is True
    assert checks.approved_secondary_database.result[0].name == "Sphera Managed Content"
    assert checks.secondary_databases.fulfilled is True


def test_secondary_database_requirement_rejects_other_versions_even_when_database_is_known() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100=PcfValueResult(value=1.45, unit="kg CO2e/kg product"),
            secondary_databases=[SecondaryDatabase(name="ecoinvent", version="3.9")],
        ),
    )

    checks = _assessed(record)

    assert checks.secondary_databases.fulfilled is False
    assert checks.approved_secondary_database.fulfilled is False
