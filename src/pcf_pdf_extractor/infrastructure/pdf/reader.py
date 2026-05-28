from pathlib import Path

from pcf_pdf_extractor.infrastructure.source import PdfSourceReader, SourceDocument


PdfDocument = SourceDocument


class PdfTextReader:
    """Backward-compatible wrapper around the generic PDF source reader."""

    def __init__(self) -> None:
        self._reader = PdfSourceReader()

    def read(self, pdf_path: Path) -> PdfDocument:
        return self._reader.read(pdf_path)
