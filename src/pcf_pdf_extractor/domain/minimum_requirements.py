import re

from pcf_pdf_extractor.domain.pcf import MinimumRequirementCheck, PCFRecord


CRITERIA: dict[str, str] = {
    "pcf_gwp100_values": (
        "Two product PCF GWP 100 values are documented: one including and one excluding "
        "biogenic carbon. If the product is fossil or not biobased, one value excluding "
        "biogenic carbon is sufficient when supported by evidence such as biogenic carbon "
        "content of 0."
    ),
    "system_boundary": "The system boundary used for the PCF calculation is documented.",
    "accepted_standard": (
        "The PCF calculation standard is accepted: TfS guideline, ISO 14040/14044, "
        "or ISO 14067."
    ),
    "production_location": "The production location is documented as a country or region.",
    "reference_year": "The reference year of data collection is documented.",
    "impact_assessment_method": "The impact assessment method used for PCF calculation is documented.",
    "secondary_databases": (
        "The secondary emission factor databases used for the PCF calculation are documented "
        "with their versions."
    ),
}


def assess_minimum_requirements(record: PCFRecord) -> list[MinimumRequirementCheck]:
    """Assess extracted data against the minimum supplier-documentation requirements."""

    existing = {check.criterion_id: check for check in record.minimum_requirements}

    return [
        _pcf_values_check(record, existing),
        _simple_presence_check(
            "system_boundary",
            record.system_boundary,
            "System boundary found.",
            "No system boundary was extracted.",
            existing,
        ),
        _accepted_standard_check(record, existing),
        _simple_presence_check(
            "production_location",
            record.product_location,
            "Production location found.",
            "No production location was extracted.",
            existing,
        ),
        _reference_year_check(record, existing),
        _simple_presence_check(
            "impact_assessment_method",
            record.impact_assessment_method,
            "Impact assessment method found.",
            "No impact assessment method was extracted.",
            existing,
        ),
        _secondary_databases_check(record, existing),
    ]


def _pcf_values_check(
    record: PCFRecord,
    existing: dict[str, MinimumRequirementCheck],
) -> MinimumRequirementCheck:
    has_with_bio = record.gwp100.with_biogenic_carbon is not None
    has_without_bio = record.gwp100.without_biogenic_carbon is not None
    has_exception_evidence = (
        record.is_fossil_or_non_biobased_product is True
        or _is_zero_biogenic_carbon_content(record.biogenic_carbon_content)
    )

    fulfilled = (has_with_bio and has_without_bio) or (has_without_bio and has_exception_evidence)

    if has_with_bio and has_without_bio:
        reason = "Both GWP 100 values, including and excluding biogenic carbon, were extracted."
    elif has_without_bio and has_exception_evidence:
        reason = (
            "Only the value excluding biogenic carbon was extracted, but the fossil/non-biobased "
            "exception is supported by the extracted data."
        )
    elif has_without_bio:
        reason = (
            "Only the value excluding biogenic carbon was extracted and no fossil/non-biobased "
            "exception evidence was found."
        )
    else:
        reason = "The required GWP 100 values were not extracted."

    evidence = _existing_evidence("pcf_gwp100_values", existing) or _join_evidence(
        [
            _format_optional("with biogenic carbon", record.gwp100.with_biogenic_carbon),
            _format_optional("without biogenic carbon", record.gwp100.without_biogenic_carbon),
            _format_optional("biogenic carbon content", record.biogenic_carbon_content),
        ]
    )
    return _check("pcf_gwp100_values", fulfilled, reason, evidence)


def _accepted_standard_check(
    record: PCFRecord,
    existing: dict[str, MinimumRequirementCheck],
) -> MinimumRequirementCheck:
    accepted = _has_accepted_standard(record.standards)
    standards = ", ".join(record.standards)
    reason = (
        "An accepted standard was extracted."
        if accepted
        else "No accepted standard was extracted. Accepted standards are TfS, ISO 14040/14044, or ISO 14067."
    )
    evidence = _existing_evidence("accepted_standard", existing) or standards or None
    return _check("accepted_standard", accepted, reason, evidence)


def _reference_year_check(
    record: PCFRecord,
    existing: dict[str, MinimumRequirementCheck],
) -> MinimumRequirementCheck:
    fulfilled = record.reference_year is not None
    reason = (
        "Reference year of data collection found."
        if fulfilled
        else "No reference year of data collection was extracted."
    )
    evidence = _existing_evidence("reference_year", existing) or _format_optional(
        "reference year",
        record.reference_year,
    )
    return _check("reference_year", fulfilled, reason, evidence)


def _secondary_databases_check(
    record: PCFRecord,
    existing: dict[str, MinimumRequirementCheck],
) -> MinimumRequirementCheck:
    has_databases = bool(record.secondary_databases)
    databases_without_versions = [
        database.name for database in record.secondary_databases if not database.version
    ]
    fulfilled = has_databases and not databases_without_versions

    if fulfilled:
        reason = "Secondary emission factor databases and versions were extracted."
    elif has_databases:
        reason = (
            "At least one secondary emission factor database is missing a version: "
            f"{', '.join(databases_without_versions)}."
        )
    else:
        reason = "No secondary emission factor database with version was extracted."

    database_evidence = ", ".join(
        f"{database.name} {database.version}".strip() for database in record.secondary_databases
    )
    evidence = _existing_evidence("secondary_databases", existing) or database_evidence or None
    return _check("secondary_databases", fulfilled, reason, evidence)


def _simple_presence_check(
    criterion_id: str,
    value: object,
    fulfilled_reason: str,
    missing_reason: str,
    existing: dict[str, MinimumRequirementCheck],
) -> MinimumRequirementCheck:
    fulfilled = bool(value)
    reason = fulfilled_reason if fulfilled else missing_reason
    evidence = _existing_evidence(criterion_id, existing) or _format_optional(criterion_id, value)
    return _check(criterion_id, fulfilled, reason, evidence)


def _check(
    criterion_id: str,
    fulfilled: bool,
    reason: str,
    evidence: str | None,
) -> MinimumRequirementCheck:
    return MinimumRequirementCheck(
        criterion_id=criterion_id,
        criterion=CRITERIA[criterion_id],
        fulfilled=fulfilled,
        evidence=evidence,
        reason=reason,
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


def _existing_evidence(
    criterion_id: str,
    existing: dict[str, MinimumRequirementCheck],
) -> str | None:
    check = existing.get(criterion_id)
    if check is None:
        return None
    return check.evidence


def _join_evidence(values: list[str | None]) -> str | None:
    present_values = [value for value in values if value]
    return "; ".join(present_values) if present_values else None


def _format_optional(label: str, value: object) -> str | None:
    if value is None or value == "":
        return None
    return f"{label}: {value}"
