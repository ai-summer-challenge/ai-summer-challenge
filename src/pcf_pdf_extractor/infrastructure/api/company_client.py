from typing import Any

import httpx

from pcf_pdf_extractor.config import Settings
from pcf_pdf_extractor.domain import PCFRecord


class CompanyApiClient:
    """HTTP adapter for shipping validated PCF records to a receiving company."""

    def __init__(self, base_url: str, token: str, timeout_seconds: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "CompanyApiClient":
        if settings.company_api_base_url is None:
            raise ValueError("COMPANY_API_BASE_URL is required to ship PCF records")
        if settings.company_api_token is None:
            raise ValueError("COMPANY_API_TOKEN is required to ship PCF records")

        return cls(
            base_url=str(settings.company_api_base_url),
            token=settings.company_api_token.get_secret_value(),
            timeout_seconds=settings.company_api_timeout_seconds,
        )

    def submit_pcf_record(self, record: PCFRecord) -> dict[str, Any]:
        payload = record.model_dump(mode="json", exclude_none=True)
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.post(f"{self._base_url}/pcf-records", json=payload, headers=headers)
            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()
