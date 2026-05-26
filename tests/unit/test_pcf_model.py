import pytest
from pydantic import ValidationError

from pcf_pdf_extractor.domain import PCFRecord


def test_reference_year_accepts_recent_year() -> None:
    record = PCFRecord(reference_year=2024)

    assert record.reference_year == 2024


def test_reference_year_rejects_unreasonable_year() -> None:
    with pytest.raises(ValidationError):
        PCFRecord(reference_year=1800)
