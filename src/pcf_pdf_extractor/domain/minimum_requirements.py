import re

from pcf_pdf_extractor.domain.pcf import (
    BooleanRequirementCheck,
    MinimumRequirements,
    PCFRecord,
    PcfValueRequirementCheck,
    PcfValueResult,
    SecondaryDatabase,
    SecondaryDatabasesRequirementCheck,
    StandardsRequirementCheck,
    TextRequirementCheck,
    YearRequirementCheck,
)


def assess_minimum_requirements(record: PCFRecord) -> MinimumRequirements:
    """Normalize and assess minimum requirements from their extracted results."""

    existing = record.minimum_requirements
    return MinimumRequirements(
        gwp100_excluding_biogenic=_gwp100_excluding_biogenic_check(
            existing.gwp100_excluding_biogenic
        ),
        gwp100_including_biogenic=_gwp100_including_biogenic_check(
            existing.gwp100_including_biogenic
        ),
        system_boundary=_text_presence_check(
            existing.system_boundary,
            fulfilled_reason="System boundary found.",
            missing_reason="No system boundary was extracted.",
        ),
        accepted_standard=_accepted_standard_check(existing.accepted_standard),
        production_location=_text_presence_check(
            existing.production_location,
            fulfilled_reason="Production location of the product/process found.",
            missing_reason="No product/process production location was extracted.",
        ),
        reference_year=_reference_year_check(existing.reference_year),
        impact_assessment_method=_text_presence_check(
            existing.impact_assessment_method,
            fulfilled_reason="Impact assessment method found.",
            missing_reason="No impact assessment method was extracted.",
        ),
        secondary_databases=_secondary_databases_check(existing.secondary_databases),
        oil_and_gas_update=_oil_and_gas_update_check(existing.oil_and_gas_update),
    )


def _gwp100_excluding_biogenic_check(
    check: PcfValueRequirementCheck,
) -> PcfValueRequirementCheck:
    fulfilled = check.result is not None and bool(check.result.unit)
    return PcfValueRequirementCheck(
        fulfilled=fulfilled,
        result=check.result,
        evidence=check.evidence or _pcf_value_evidence(check.result),
        reason=(
            "GWP 100 excluding biogenic carbon was extracted with value and unit."
            if fulfilled
            else "No GWP 100 excluding biogenic carbon value with unit was extracted."
        ),
    )


def _gwp100_including_biogenic_check(
    check: PcfValueRequirementCheck,
) -> PcfValueRequirementCheck:
    fulfilled = check.result is not None and bool(check.result.unit)
    return PcfValueRequirementCheck(
        fulfilled=fulfilled,
        result=check.result,
        evidence=check.evidence or _pcf_value_evidence(check.result),
        reason=(
            "GWP 100 including biogenic carbon was extracted with value and unit."
            if fulfilled
            else "No GWP 100 including biogenic carbon value with unit was extracted."
        ),
    )


def _text_presence_check(
    check: TextRequirementCheck,
    *,
    fulfilled_reason: str,
    missing_reason: str,
) -> TextRequirementCheck:
    fulfilled = bool(check.result)
    return TextRequirementCheck(
        fulfilled=fulfilled,
        result=check.result,
        evidence=check.evidence or check.result,
        reason=fulfilled_reason if fulfilled else missing_reason,
    )


def _reference_year_check(check: YearRequirementCheck) -> YearRequirementCheck:
    fulfilled = check.result is not None
    return YearRequirementCheck(
        fulfilled=fulfilled,
        result=check.result,
        evidence=check.evidence or _format_optional("reference year", check.result),
        reason=(
            "Reference year of the production data found."
            if fulfilled
            else "No reference year of the production data was extracted."
        ),
    )


def _accepted_standard_check(check: StandardsRequirementCheck) -> StandardsRequirementCheck:
    accepted = _has_accepted_standard(check.result)
    standards = ", ".join(check.result)
    return StandardsRequirementCheck(
        fulfilled=accepted,
        result=check.result,
        evidence=check.evidence or standards or None,
        reason=(
            "An accepted standard was extracted."
            if accepted
            else (
                "No accepted standard was extracted. Accepted standards are TfS, "
                "ISO 14040/14044 together, or ISO 14067."
            )
        ),
    )


def _secondary_databases_check(
    check: SecondaryDatabasesRequirementCheck,
) -> SecondaryDatabasesRequirementCheck:
    has_databases = bool(check.result)
    unapproved_databases = [
        database for database in check.result if not _is_approved_secondary_database(database)
    ]
    fulfilled = not unapproved_databases

    if fulfilled and has_databases:
        reason = (
            "Only approved secondary databases were extracted: ecoinvent 3.10 or newer "
            "and/or Sphera Managed Content 2024 or newer."
        )
    elif has_databases:
        reason = (
            "At least one secondary emission factor database is not allowed. Only "
            "ecoinvent 3.10 or newer and Sphera Managed Content 2024 or newer are "
            "accepted. Found: "
            f"{_format_databases(unapproved_databases)}."
        )
    else:
        reason = "No secondary emission factor database was extracted, which is acceptable."

    database_evidence = _format_databases(check.result)
    return SecondaryDatabasesRequirementCheck(
        fulfilled=fulfilled,
        result=check.result,
        evidence=check.evidence or database_evidence or None,
        reason=reason,
    )


def _oil_and_gas_update_check(check: BooleanRequirementCheck) -> BooleanRequirementCheck:
    mentioned = check.result is True
    return BooleanRequirementCheck(
        fulfilled=mentioned,
        result=mentioned,
        evidence=check.evidence,
        reason=(
            "'Oil and gas update' is mentioned in the supplier documentation."
            if mentioned
            else "'Oil and gas update' was not found in the supplier documentation."
        ),
    )


def _has_accepted_standard(standards: list[str]) -> bool:
    normalized = " ".join(standards).lower().replace("/", " ")
    has_tfs = "tfs" in normalized or "together for sustainability" in normalized
    has_iso_14067 = _contains_iso(normalized, "14067")
    has_iso_14040_and_14044 = (
        (_contains_iso(normalized, "14040") and _contains_iso(normalized, "14044"))
        or _contains_iso_14040_44_shorthand(" ".join(standards).lower())
    )
    return has_tfs or has_iso_14067 or has_iso_14040_and_14044


def _is_approved_secondary_database(database: SecondaryDatabase) -> bool:
    name = _normalize_text(database.name)
    is_ecoinvent_310_or_above = "ecoinvent" in name and _version_gte(database.version, 3.10)
    is_sphera_2024_or_above = (
        "sphera" in name
        and ("managed content" in name or "managedcontent" in name)
        and _year_gte(database.version, 2024)
    )
    return is_ecoinvent_310_or_above or is_sphera_2024_or_above


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _contains_iso(normalized_text: str, number: str) -> bool:
    return bool(re.search(rf"\biso\s*{number}\b|\b{number}\b", normalized_text))


def _contains_iso_14040_44_shorthand(text: str) -> bool:
    return bool(re.search(r"\biso\s*14040\s*(?:/|-|to|and)\s*44\b", text))


def _pcf_value_evidence(result: PcfValueResult | None) -> str | None:
    if result is None:
        return None
    return f"{result.value} {result.unit}"


def _format_databases(databases: list[SecondaryDatabase]) -> str:
    return ", ".join(f"{database.name} {database.version}".strip() for database in databases)


def _format_optional(label: str, value: object) -> str | None:
    if value is None or value == "":
        return None
    return f"{label}: {value}"


def _version_gte(version: str | None, threshold: float) -> bool:
    if not version:
        return False
    match = re.search(r"(\d+(?:[.,]\d+)?)", version)
    if not match:
        return False
    try:
        return float(match.group(1).replace(",", ".")) >= threshold
    except ValueError:
        return False


def _year_gte(version: str | None, threshold: int) -> bool:
    if not version:
        return False
    match = re.search(r"\b(19\d{2}|20\d{2})\b", version)
    if not match:
        return False
    try:
        return int(match.group(1)) >= threshold
    except ValueError:
        return False
