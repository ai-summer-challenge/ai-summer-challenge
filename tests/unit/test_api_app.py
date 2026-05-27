from fastapi.testclient import TestClient

from pcf_pdf_extractor.api.app import app
from pcf_pdf_extractor.domain import (
    MinimumRequirements,
    PcfValueRequirementCheck,
    PcfValueResult,
    SecondaryDatabasesRequirementCheck,
    StandardsRequirementCheck,
    TextRequirementCheck,
    YearRequirementCheck,
)


def _minimum_requirements() -> MinimumRequirements:
    return MinimumRequirements(
        gwp100=PcfValueRequirementCheck(
            fulfilled=True,
            result=PcfValueResult(value=1.45, unit="kg CO2e/kg product"),
            evidence=None,
            reason="Value found.",
        ),
        gwp100_biogenic=PcfValueRequirementCheck(
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
        secondary_databases=SecondaryDatabasesRequirementCheck(
            fulfilled=False,
            result=[],
            evidence=None,
            reason="",
        ),
    )


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_assess_record_refreshes_minimum_requirements() -> None:
    client = TestClient(app)
    payload = {
        "biogenic_carbon_content": "0%",
        "minimum_requirements": _minimum_requirements().model_dump(mode="json"),
    }

    response = client.post("/api/records/assess", json=payload)

    assert response.status_code == 200
    assert response.json()["minimum_requirements"]["gwp100_biogenic"]["fulfilled"] is True
