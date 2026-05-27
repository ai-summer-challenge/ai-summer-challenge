import re

from pcf_pdf_extractor.domain.pcf import (
    BooleanRequirementCheck,
    MinimumRequirements,
    PCFRecord,
    PcfValueRequirementCheck,
    PcfValueResult,
    SecondaryDatabasesRequirementCheck,
    StandardsRequirementCheck,
    TextRequirementCheck,
    YearRequirementCheck,
)


def assess_minimum_requirements(record: PCFRecord) -> MinimumRequirements:
    """Normalize and assess minimum requirements from their extracted results."""

    existing = record.minimum_requirements
    has_exception_evidence = (
        record.is_fossil_or_non_biobased_product is True
        or _is_zero_biogenic_carbon_content(record.biogenic_carbon_content)
    )

    return MinimumRequirements(
        gwp100=_gwp100_check(existing.gwp100),
        gwp100_biogenic=_gwp100_biogenic_check(
            existing.gwp100_biogenic,
            has_exception_evidence,
            record.biogenic_carbon_content,
            record.is_fossil_or_non_biobased_product,
        ),
        system_boundary=_text_presence_check(
            existing.system_boundary,
            fulfilled_reason="System boundary found.",
            missing_reason="No system boundary was extracted.",
        ),
        accepted_standard=_accepted_standard_check(existing.accepted_standard),
        production_location=_text_presence_check(
            existing.production_location,
            fulfilled_reason="Production location found.",
            missing_reason="No production location was extracted.",
        ),
        reference_year=_reference_year_check(existing.reference_year),
        impact_assessment_method=_text_presence_check(
            existing.impact_assessment_method,
            fulfilled_reason="Impact assessment method found.",
            missing_reason="No impact assessment method was extracted.",
        ),
        secondary_databases=_secondary_databases_check(existing.secondary_databases),
        oil_and_gas_update=_oil_and_gas_update_check(existing.oil_and_gas_update),
        approved_secondary_database=_approved_secondary_database_check(
            existing.approved_secondary_database,
            existing.secondary_databases,
        ),
    )


def _gwp100_check(check: PcfValueRequirementCheck) -> PcfValueRequirementCheck:
    fulfilled = check.result is not None
    return PcfValueRequirementCheck(
        fulfilled=fulfilled,
        result=check.result,
        evidence=check.evidence or _pcf_value_evidence(check.result),
        reason=(
            "GWP 100 excluding biogenic carbon was extracted as a numeric value."
            if fulfilled
            else "No GWP 100 excluding biogenic carbon value was extracted."
        ),
    )


def _gwp100_biogenic_check(
    check: PcfValueRequirementCheck,
    has_exception_evidence: bool,
    biogenic_carbon_content: str | None,
    is_fossil_or_non_biobased_product: bool | None,
) -> PcfValueRequirementCheck:
    if check.result is not None:
        return PcfValueRequirementCheck(
            fulfilled=True,
            result=check.result,
            evidence=check.evidence or _pcf_value_evidence(check.result),
            reason="GWP 100 including biogenic carbon was extracted as a numeric value.",
        )

    if has_exception_evidence:
        return PcfValueRequirementCheck(
            fulfilled=True,
            result=None,
            evidence=check.evidence
            or _join_evidence(
                [
                    _format_optional("biogenic carbon content", biogenic_carbon_content),
                    _format_optional(
                        "fossil or non-biobased product",
                        is_fossil_or_non_biobased_product,
                    ),
                ]
            ),
            reason=(
                "GWP 100 including biogenic carbon is absent, but the fossil/non-biobased "
                "exception is supported."
            ),
        )

    return PcfValueRequirementCheck(
        fulfilled=False,
        result=None,
        evidence=check.evidence,
        reason=(
            "No GWP 100 including biogenic carbon was extracted and no fossil/non-biobased "
            "exception evidence was found."
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
            "Reference year of data collection found."
            if fulfilled
            else "No reference year of data collection was extracted."
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
    fulfilled = has_databases and not unapproved_databases

    if fulfilled:
        reason = (
            "Only approved secondary databases were extracted: ecoinvent 3.10 or "
            "Sphera Managed Content 2024."
        )
    elif has_databases:
        reason = (
            "At least one secondary emission factor database is not allowed. Only "
            "ecoinvent 3.10 or Sphera Managed Content 2024 are accepted. Found: "
            f"{_format_databases(unapproved_databases)}."
        )
    else:
        reason = (
            "No approved secondary emission factor database was extracted. Only ecoinvent "
            "3.10 or Sphera Managed Content 2024 are accepted."
        )

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


def _approved_secondary_database_check(
    check: SecondaryDatabasesRequirementCheck,
    secondary_databases_check: SecondaryDatabasesRequirementCheck,
) -> SecondaryDatabasesRequirementCheck:
    candidates = check.result or secondary_databases_check.result
    approved_databases = [
        database for database in candidates if _is_approved_secondary_database(database)
    ]
    fulfilled = bool(approved_databases)

    evidence = check.evidence
    if not evidence and approved_databases:
        evidence = ", ".join(
            f"{database.name} {database.version}".strip() for database in approved_databases
        )

    return SecondaryDatabasesRequirementCheck(
        fulfilled=fulfilled,
        result=approved_databases,
        evidence=evidence,
        reason=(
            "An approved secondary database/version was found: ecoinvent 3.10 or "
            "Sphera Managed Content 2024."
            if fulfilled
            else (
                "Neither ecoinvent 3.10 nor Sphera Managed Content 2024 was found among "
                "the secondary databases."
            )
        ),
    )


def _has_accepted_standard(standards: list[str]) -> bool:
    normalized = " ".join(standards).lower().replace("/", " ")
    has_tfs = "tfs" in normalized or "together for sustainability" in normalized
    has_iso_14067 = _contains_iso(normalized, "14067")
    has_iso_14040_and_14044 = _contains_iso(normalized, "14040") and _contains_iso(
        normalized,
        "14044",
    )
    return has_tfs or has_iso_14067 or has_iso_14040_and_14044


def _is_approved_secondary_database(database) -> bool:
    name = _normalize_text(database.name)
    version = _normalize_text(database.version or "")
    is_ecoinvent_310 = "ecoinvent" in name and version == "3 10"
    is_sphera_2024 = (
        "sphera" in name
        and ("managed content" in name or "managedcontent" in name)
        and version == "2024"
    )
    return is_ecoinvent_310 or is_sphera_2024


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _contains_iso(normalized_text: str, number: str) -> bool:
    return bool(re.search(rf"\biso\s*{number}\b|\b{number}\b", normalized_text))


def _is_zero_biogenic_carbon_content(value: str | None) -> bool:
    if not value:
        return False
    for raw_number in re.findall(r"[-+]?\d+(?:[.,]\d+)?", value):
        try:
            if float(raw_number.replace(",", ".")) == 0:
                return True
        except ValueError:
            continue
    return False


def _pcf_value_evidence(result: PcfValueResult | None) -> str | None:
    if result is None:
        return None
    if result.unit:
        return f"{result.value} {result.unit}"
    return str(result.value)


def _format_databases(databases) -> str:
    return ", ".join(f"{database.name} {database.version}".strip() for database in databases)


def _join_evidence(values: list[str | None]) -> str | None:
    present_values = [value for value in values if value]
    return "; ".join(present_values) if present_values else None


def _format_optional(label: str, value: object) -> str | None:
    if value is None or value == "":
        return None
    return f"{label}: {value}"
