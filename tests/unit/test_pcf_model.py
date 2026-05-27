import pytest
from pydantic import ValidationError

from pcf_pdf_extractor.domain import (
    BooleanRequirementCheck,
    MinimumRequirements,
    PCFRecord,
    PcfValueRequirementCheck,
    PcfValueResult,
    SecondaryDatabasesRequirementCheck,
    StandardsRequirementCheck,
    TextRequirementCheck,
    YearRequirementCheck,
)


def _minimum_requirements(reference_year: int | None = None) -> MinimumRequirements:
    return MinimumRequirements(
        gwp100_excluding_biogenic=PcfValueRequirementCheck(
            fulfilled=True,
            result=PcfValueResult(value=1.45, unit="kg CO2e/kg product"),
            evidence=None,
            reason="Value found.",
        ),
        gwp100_including_biogenic=PcfValueRequirementCheck(
            fulfilled=False,
            result=None,
            evidence=None,
            reason="Value not found.",
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
            fulfilled=False,
            result=None,
            evidence=None,
            reason="",
        ),
        reference_year=YearRequirementCheck(
            fulfilled=reference_year is not None,
            result=reference_year,
            evidence=None,
            reason="",
        ),
        impact_assessment_method=TextRequirementCheck(
            fulfilled=False,
            result=None,
            evidence=None,
            reason="",
        ),
        secondary_databases=SecondaryDatabasesRequirementCheck(
            fulfilled=False,
            result=[],
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


def test_reference_year_accepts_recent_year() -> None:
    record = PCFRecord(minimum_requirements=_minimum_requirements(reference_year=2024))

    assert record.minimum_requirements.reference_year.result == 2024


def test_reference_year_rejects_unreasonable_year() -> None:
    with pytest.raises(ValidationError):
        PCFRecord(minimum_requirements=_minimum_requirements(reference_year=1800))


def test_minimum_requirements_are_required() -> None:
    with pytest.raises(ValidationError):
        PCFRecord()
