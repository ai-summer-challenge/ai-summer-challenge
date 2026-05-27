from typing import Any

import httpx


class BackendApiError(RuntimeError):
    pass


class PcfBackendClient:
    def __init__(self, base_url: str, timeout_seconds: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def extract_pdf(self, *, file_name: str, file_bytes: bytes, extractor: str) -> list[dict[str, Any]]:
        files = {"file": (file_name, file_bytes, "application/pdf")}
        data = {"extractor": extractor}
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.post(f"{self._base_url}/api/extract", files=files, data=data)
        payload = self._raise_for_status(response)
        records = payload.get("records")
        if not isinstance(records, list):
            raise BackendApiError("Backend response did not include a records list.")
        return records

    def assess_record(self, record: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.post(f"{self._base_url}/api/records/assess", json=record)
        payload = self._raise_for_status(response)
        if not isinstance(payload, dict):
            raise BackendApiError("Backend response did not include a record object.")
        return payload

    def _raise_for_status(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.is_success:
            if isinstance(payload, dict):
                return payload
            raise BackendApiError("Backend returned an invalid JSON response.")

        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, str):
            raise BackendApiError(detail)
        raise BackendApiError(f"Backend request failed with HTTP {response.status_code}.")

