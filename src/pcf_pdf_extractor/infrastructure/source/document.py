from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class SourceDocument:
    """Normalized text extracted from a supported supplier-document source file."""

    path: Path
    text: str
    text_sha256: str
    source_type: str

    @classmethod
    def from_text(cls, *, path: Path, text: str, source_type: str) -> "SourceDocument":
        normalized_path = path.expanduser().resolve()
        return cls(
            path=normalized_path,
            text=text,
            text_sha256=sha256(text.encode("utf-8")).hexdigest(),
            source_type=source_type,
        )
