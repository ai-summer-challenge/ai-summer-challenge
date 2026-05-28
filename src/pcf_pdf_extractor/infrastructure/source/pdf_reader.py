from pathlib import Path

from pypdf import PdfReader

from pcf_pdf_extractor.infrastructure.source.document import SourceDocument


class PdfSourceReader:
    """Extract text from a PDF while preserving coarse page boundaries."""

    def read(self, source_path: Path) -> SourceDocument:
        path = source_path.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, got: {path}")

        reader = PdfReader(str(path))
        pages: list[str] = [f"--- source type: pdf ---\n--- file: {path.name} ---"]
        for index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append(f"\n\n--- page {index} ---\n{page_text.strip()}")

        text = "\n".join(pages).strip()
        return SourceDocument.from_text(path=path, text=text, source_type="pdf")
