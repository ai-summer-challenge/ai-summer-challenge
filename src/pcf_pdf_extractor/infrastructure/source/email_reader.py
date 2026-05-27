import re
from email import policy
from email.parser import BytesParser
from pathlib import Path

from pcf_pdf_extractor.infrastructure.source.document import SourceDocument


class EmailSourceReader:
    """Extract email headers and body text.

    Attachments are intentionally ignored. Supplier files attached to an email should be
    processed as their own input files.
    """

    def read(self, source_path: Path) -> SourceDocument:
        path = source_path.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)

        suffix = path.suffix.lower()
        if suffix == ".msg":
            text = self._read_msg(path)
        else:
            text = self._read_eml_like(path)

        return SourceDocument.from_text(path=path, text=text, source_type="email")

    def _read_eml_like(self, path: Path) -> str:
        with path.open("rb") as file:
            message = BytesParser(policy=policy.default).parse(file)

        headers = self._format_headers(
            subject=message.get("subject"),
            sender=message.get("from"),
            recipients=message.get("to"),
            cc=message.get("cc"),
            date=message.get("date"),
        )
        body = self._extract_message_body(message)
        return f"--- source type: email ---\n--- file: {path.name} ---\n{headers}\n\n--- body ---\n{body}".strip()

    def _read_msg(self, path: Path) -> str:
        try:
            import extract_msg
        except ImportError as exc:
            raise RuntimeError(
                "Reading .msg files requires extract-msg. Install project dependencies with "
                'pip install -e ".[dev]".'
            ) from exc

        message = extract_msg.Message(str(path))
        try:
            headers = self._format_headers(
                subject=message.subject,
                sender=message.sender,
                recipients=message.to,
                cc=message.cc,
                date=str(message.date) if message.date else None,
            )
            body = message.body or ""
        finally:
            message.close()

        return f"--- source type: email ---\n--- file: {path.name} ---\n{headers}\n\n--- body ---\n{body.strip()}".strip()

    def _format_headers(
        self,
        *,
        subject: str | None,
        sender: str | None,
        recipients: str | None,
        cc: str | None,
        date: str | None,
    ) -> str:
        lines = ["--- email headers ---"]
        for label, value in [
            ("Subject", subject),
            ("From", sender),
            ("To", recipients),
            ("Cc", cc),
            ("Date", date),
        ]:
            if value:
                lines.append(f"{label}: {value}")
        return "\n".join(lines)

    def _extract_message_body(self, message) -> str:
        plain_parts: list[str] = []
        html_parts: list[str] = []

        for part in message.walk():
            if part.is_multipart():
                continue
            if part.get_content_disposition() == "attachment":
                continue

            content_type = part.get_content_type()
            try:
                content = part.get_content()
            except LookupError:
                payload = part.get_payload(decode=True)
                content = payload.decode(errors="replace") if payload else ""

            if not content:
                continue
            if content_type == "text/plain":
                plain_parts.append(str(content).strip())
            elif content_type == "text/html":
                html_parts.append(_html_to_text(str(content)))

        if plain_parts:
            return "\n\n".join(part for part in plain_parts if part).strip()
        return "\n\n".join(part for part in html_parts if part).strip()


def _html_to_text(html: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", without_tags).strip()
