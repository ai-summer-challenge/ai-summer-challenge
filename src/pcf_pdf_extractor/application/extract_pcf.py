from pathlib import Path

from pcf_pdf_extractor.domain import PCFRecord, assess_minimum_requirements
from pcf_pdf_extractor.extraction import HeuristicPcfExtractor, PcfExtractor
from pcf_pdf_extractor.infrastructure.pdf import PdfTextReader


class ExtractPcfFromPdf:
    """Application use case: PDF file in, structured PCF records out."""

    def __init__(
        self,
        pdf_reader: PdfTextReader | None = None,
        extractor: PcfExtractor | None = None,
    ) -> None:
        self._pdf_reader = pdf_reader or PdfTextReader()
        self._extractor = extractor or HeuristicPcfExtractor()

    def run(self, pdf_path: Path) -> list[PCFRecord]:
        document = self._pdf_reader.read(pdf_path)
        records = self._extractor.extract(document.text)
        for record in records:
            record.source_file = str(document.path)
            record.raw_text_sha256 = document.text_sha256
            record.minimum_requirements = assess_minimum_requirements(record)
        return records
