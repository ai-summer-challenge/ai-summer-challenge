from email.message import EmailMessage
from pathlib import Path

import pytest

from pcf_pdf_extractor.infrastructure.source import EmailSourceReader, SourceTextReaderSelector


def test_source_selector_chooses_readers_by_extension() -> None:
    selector = SourceTextReaderSelector()

    assert selector.reader_for(Path("document.pdf")).__class__.__name__ == "PdfSourceReader"
    assert selector.reader_for(Path("table.xlsx")).__class__.__name__ == (
        "ExcelSourceReader"
    )
    assert selector.reader_for(Path("message.eml")).__class__.__name__ == (
        "EmailSourceReader"
    )


def test_source_selector_rejects_unsupported_extensions() -> None:
    selector = SourceTextReaderSelector()

    with pytest.raises(ValueError):
        selector.reader_for(Path("image.png"))


def test_email_reader_extracts_headers_and_body_without_attachment(tmp_path) -> None:
    message = EmailMessage()
    message["Subject"] = "PCF data"
    message["From"] = "supplier@example.com"
    message["To"] = "buyer@example.com"
    message.set_content("The body contains PCF information.")
    message.add_attachment(
        b"attachment content",
        maintype="application",
        subtype="octet-stream",
        filename="ignored.txt",
    )

    path = tmp_path / "supplier.eml"
    path.write_bytes(message.as_bytes())

    document = EmailSourceReader().read(path)

    assert "Subject: PCF data" in document.text
    assert "From: supplier@example.com" in document.text
    assert "The body contains PCF information." in document.text
    assert "attachment content" not in document.text
