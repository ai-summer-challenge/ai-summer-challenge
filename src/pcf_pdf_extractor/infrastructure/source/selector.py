from pathlib import Path

from pcf_pdf_extractor.infrastructure.source.base import SourceTextReader
from pcf_pdf_extractor.infrastructure.source.email_reader import EmailSourceReader
from pcf_pdf_extractor.infrastructure.source.excel_reader import ExcelSourceReader
from pcf_pdf_extractor.infrastructure.source.pdf_reader import PdfSourceReader


class SourceTextReaderSelector:
    """Select the source reader from the input file extension."""

    _EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"}
    _EMAIL_SUFFIXES = {".eml", ".msg", ".mail"}

    def __init__(
        self,
        pdf_reader: SourceTextReader | None = None,
        excel_reader: SourceTextReader | None = None,
        email_reader: SourceTextReader | None = None,
    ) -> None:
        self._pdf_reader = pdf_reader or PdfSourceReader()
        self._excel_reader = excel_reader or ExcelSourceReader()
        self._email_reader = email_reader or EmailSourceReader()

    def reader_for(self, source_path: Path) -> SourceTextReader:
        suffix = source_path.suffix.lower()
        if suffix == ".pdf":
            return self._pdf_reader
        if suffix in self._EXCEL_SUFFIXES:
            return self._excel_reader
        if suffix in self._EMAIL_SUFFIXES:
            return self._email_reader

        supported = sorted({".pdf", *self._EXCEL_SUFFIXES, *self._EMAIL_SUFFIXES})
        raise ValueError(
            f"Unsupported source file extension '{suffix}'. Supported extensions: "
            f"{', '.join(supported)}"
        )

    def read(self, source_path: Path):
        return self.reader_for(source_path).read(source_path)
