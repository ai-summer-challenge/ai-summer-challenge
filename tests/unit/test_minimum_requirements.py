from pcf_pdf_extractor.domain import (
    BooleanRequirementCheck,
    MinimumRequirements,
    PCFRecord,
    PcfValueRequirementCheck,
    PcfValueResult,
    StandardsRequirementCheck,
    TextRequirementCheck,
    YearRequirementCheck,
)
from pcf_pdf_extractor.domain.minimum_requirements import assess_minimum_requirements


def _requirements(
    *,
    gwp100_excluding_biogenic: PcfValueResult | None = None,
    gwp100_including_biogenic: PcfValueResult | None = None,
    system_boundary: str | None = None,
    standards: list[str] | None = None,
    production_location: str | None = None,
    reference_year: int | None = None,
    impact_assessment_method: str | None = None,
    secondary_databases: bool | None = None,
    oil_and_gas_update: bool | None = None,
) -> MinimumRequirements:
    return MinimumRequirements(
        gwp100_excluding_biogenic=PcfValueRequirementCheck(
            fulfilled=False,
            result=gwp100_excluding_biogenic,
            evidence=None,
            reason="",
        ),
        gwp100_including_biogenic=PcfValueRequirementCheck(
            fulfilled=False,
            result=gwp100_including_biogenic,
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
        secondary_databases=BooleanRequirementCheck(
            fulfilled=secondary_databases is True,
            result=secondary_databases,
            evidence=None,
            reason="",
        ),
        oil_and_gas_update=BooleanRequirementCheck(
            fulfilled=oil_and_gas_update is True,
            result=oil_and_gas_update,
            evidence=None,
            reason="",
        ),
    )


def _assessed(record: PCFRecord):
    return assess_minimum_requirements(record)


def test_assessment_fulfills_all_requirements_with_two_pcf_values() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100_excluding_biogenic=PcfValueResult(
                value=1.45,
                unit="kg CO2e/kg product",
            ),
            gwp100_including_biogenic=PcfValueResult(
                value=1.23,
                unit="kg CO2e/kg product",
            ),
            system_boundary="cradle-to-gate",
            standards=["ISO 14040", "ISO 14044"],
            production_location="France",
            reference_year=2024,
            impact_assessment_method="IPCC AR6",
            secondary_databases=True,
            oil_and_gas_update=True,
        ),
    )

    checks = _assessed(record)

    assert all(check["fulfilled"] for check in checks.model_dump().values())


def test_assessment_requires_including_biogenic_value_when_absent() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100_excluding_biogenic=PcfValueResult(
                value=1.45,
                unit="kg CO2e/kg product",
            ),
        ),
    )

    checks = _assessed(record)

    assert checks.gwp100_excluding_biogenic.fulfilled is True
    assert checks.gwp100_including_biogenic.fulfilled is False


def test_assessment_rejects_unaccepted_standard_and_missing_database_version() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100_excluding_biogenic=PcfValueResult(
                value=1.45,
                unit="kg CO2e/kg product",
            ),
            standards=["GHG Protocol"],
            secondary_databases=False,
        ),
    )

    checks = _assessed(record)

    assert checks.accepted_standard.fulfilled is False
    assert checks.secondary_databases.fulfilled is False


def test_assessment_accepts_sphera_managed_content_2024() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100_excluding_biogenic=PcfValueResult(
                value=1.45,
                unit="kg CO2e/kg product",
            ),
            secondary_databases=True,
        ),
    )

    checks = _assessed(record)

    assert checks.secondary_databases.fulfilled is True


def test_secondary_database_requirement_false_when_not_compliant() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100_excluding_biogenic=PcfValueResult(
                value=1.45,
                unit="kg CO2e/kg product",
            ),
            secondary_databases=False,
        ),
    )

    checks = _assessed(record)

    assert checks.secondary_databases.fulfilled is False


def test_secondary_database_requirement_true_when_compliant() -> None:
    record = PCFRecord(
        minimum_requirements=_requirements(
            gwp100_excluding_biogenic=PcfValueResult(
                value=1.45,
                unit="kg CO2e/kg product",
            ),
            secondary_databases=True,
        ),
    )

    checks = _assessed(record)

    assert checks.secondary_databases.fulfilled is True
