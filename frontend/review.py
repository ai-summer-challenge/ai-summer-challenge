from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RecordReviewEdits:
    company_name: str | None
    product_name: str | None
    biogenic_carbon_content: str | None
    is_fossil_or_non_biobased_product: bool | None
    extraction_notes_text: str


def apply_record_review_edits(record: dict[str, Any], edits: RecordReviewEdits) -> dict[str, Any]:
    updated_record = dict(record)
    updated_record["company_name"] = _blank_to_none(edits.company_name)
    updated_record["product_name"] = _blank_to_none(edits.product_name)
    updated_record["biogenic_carbon_content"] = _blank_to_none(edits.biogenic_carbon_content)
    updated_record["is_fossil_or_non_biobased_product"] = edits.is_fossil_or_non_biobased_product
    updated_record["extraction_notes"] = _notes_from_text(edits.extraction_notes_text)
    return updated_record


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _notes_from_text(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]

