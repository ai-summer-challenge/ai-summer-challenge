from typing import Protocol

from pcf_pdf_extractor.domain import PCFRecord


class PcfExtractor(Protocol):
    """Common interface for PCF extraction strategies."""

    def extract(self, text: str) -> list[PCFRecord]:
        """Extract one PCF record per distinct chemical/product from PDF text."""
