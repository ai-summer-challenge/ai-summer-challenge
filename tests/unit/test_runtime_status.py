from fastapi.testclient import TestClient

from pcf_pdf_extractor.api.app import app


def test_runtime_status_reports_missing_llm_settings() -> None:
    client = TestClient(app)

    response = client.get("/api/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_available"] is True
    assert payload["llm_message"] is None
