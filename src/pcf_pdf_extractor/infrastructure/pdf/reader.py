from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class PdfDocument:
    path: Path
    text: str
    text_sha256: str


class PdfTextReader:
    """Extract text from a PDF while preserving coarse page boundaries."""

    def read(self, pdf_path: Path) -> PdfDocument:
        path = pdf_path.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, got: {path}")

        reader = PdfReader(str(path))
        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append(f"\n\n--- page {index} ---\n{page_text.strip()}")

        text = "\n".join(pages).strip()
        return PdfDocument(path=path, text=text, text_sha256=sha256(text.encode()).hexdigest())
