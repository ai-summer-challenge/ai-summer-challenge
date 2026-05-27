from pathlib import Path
from typing import Protocol

from pcf_pdf_extractor.infrastructure.source.document import SourceDocument


class SourceTextReader(Protocol):
    """Common interface for file-format readers."""

    def read(self, source_path: Path) -> SourceDocument:
        """Read a source file and return normalized text."""
