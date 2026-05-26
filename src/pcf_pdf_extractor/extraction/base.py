from typing import Protocol

from pcf_pdf_extractor.domain import PCFRecord


class PcfExtractor(Protocol):
    """Common interface for PCF extraction strategies."""

    def extract(self, text: str) -> PCFRecord:
        """Extract a structured PCF record from PDF text."""
