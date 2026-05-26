from pathlib import Path

from pcf_pdf_extractor.domain import PCFRecord, assess_minimum_requirements
from pcf_pdf_extractor.extraction import HeuristicPcfExtractor, PcfExtractor
from pcf_pdf_extractor.infrastructure.pdf import PdfTextReader


class ExtractPcfFromPdf:
    """Application use case: PDF file in, structured PCF record out."""

    def __init__(
        self,
        pdf_reader: PdfTextReader | None = None,
        extractor: PcfExtractor | None = None,
    ) -> None:
        self._pdf_reader = pdf_reader or PdfTextReader()
        self._extractor = extractor or HeuristicPcfExtractor()

    def run(self, pdf_path: Path) -> PCFRecord:
        document = self._pdf_reader.read(pdf_path)
        record = self._extractor.extract(document.text)
        record.source_file = str(document.path)
        record.raw_text_sha256 = document.text_sha256
        record.minimum_requirements = assess_minimum_requirements(record)
        return record
