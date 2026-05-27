import re

from pcf_pdf_extractor.domain import (
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
    assess_minimum_requirements,
)


class HeuristicPcfExtractor:
    """First-pass extractor for text PDFs.

    This is intentionally conservative. It gives the app a working pipeline today and
    marks uncertain fields as missing so an LLM/OCR review step can be added later.
    """

    _SYSTEM_BOUNDARIES = [
        "cradle-to-gate",
        "cradle to gate",
        "cradle-to-grave",
        "cradle to grave",
        "gate-to-gate",
        "gate to gate",
        "cradle-to-cradle",
        "cradle to cradle",
    ]
    _STANDARDS = [
        "ISO 14040",
        "ISO 14044",
        "ISO 14067",
        "TfS",
        "Together for Sustainability",
        "GHG Protocol",
        "PEF",
    ]
    _IMPACT_METHODS = [
        "IPCC AR6",
        "IPCC 2021",
        "IPCC AR5",
        "CML2001",
        "ISO 14067",
        "EF 3.1",
        "Environmental Footprint",
    ]
    _DATABASES = [
        "ecoinvent",
        "GaBi",
        "Sphera",
        "ELCD",
        "Agribalyse",
        "WFLDB",
        "USLCI",
        "Carbon Minds",
    ]

    def extract(self, text: str) -> list[PCFRecord]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        standards = self._find_terms(text, self._STANDARDS)
        secondary_databases = self._find_databases(lines)
        gwp100 = self._find_primary_gwp_value(lines)
        gwp100_biogenic = self._find_gwp_value(
            lines,
            [
                "with biogenic",
                "including biogenic",
                "incl. biogenic",
                "including bio",
                "incl. bio",
            ],
        )
        gwp100_unit = self._find_unit(lines)

        record = PCFRecord(
            company_name=self._find_labeled_value(lines, ["company", "supplier", "manufacturer"]),
            product_name=self._find_labeled_value(lines, ["product name", "product"]),
            minimum_requirements=MinimumRequirements(
                gwp100_excluding_biogenic=PcfValueRequirementCheck(
                    fulfilled=True,
                    result=PcfValueResult(value=gwp100, unit=gwp100_unit),
                    evidence=None,
                    reason="",
                ),
                gwp100_including_biogenic=PcfValueRequirementCheck(
                    fulfilled=gwp100_biogenic is not None,
                    result=(
                        PcfValueResult(value=gwp100_biogenic, unit=gwp100_unit)
                        if gwp100_biogenic is not None
                        else None
                    ),
                    evidence=None,
                    reason="",
                ),
                system_boundary=TextRequirementCheck(
                    fulfilled=False,
                    result=self._find_first_term(text, self._SYSTEM_BOUNDARIES, normalize=True),
                    evidence=None,
                    reason="",
                ),
                accepted_standard=StandardsRequirementCheck(
                    fulfilled=False,
                    result=standards,
                    evidence=None,
                    reason="",
                ),
                production_location=TextRequirementCheck(
                    fulfilled=False,
                    result=self._find_labeled_value(
                        lines,
                        ["product location", "production location", "country/region", "country"],
                    ),
                    evidence=None,
                    reason="",
                ),
                reference_year=YearRequirementCheck(
                    fulfilled=False,
                    result=self._find_reference_year(lines),
                    evidence=None,
                    reason="",
                ),
                impact_assessment_method=TextRequirementCheck(
                    fulfilled=False,
                    result=self._find_first_term(text, self._IMPACT_METHODS),
                    evidence=None,
                    reason="",
                ),
                secondary_databases=SecondaryDatabasesRequirementCheck(
                    fulfilled=False,
                    result=secondary_databases,
                    evidence=None,
                    reason="",
                ),
                oil_and_gas_update=BooleanRequirementCheck(
                    fulfilled=False,
                    result=bool(re.search(r"\boil\s+and\s+gas\s+update\b", text, re.IGNORECASE)),
                    evidence=None,
                    reason="",
                ),
            ),
            extraction_notes=[
                "Extracted with heuristic rules. Review missing or surprising fields before shipping."
            ],
        )
        record.minimum_requirements = assess_minimum_requirements(record)
        return [record]

    def _find_labeled_value(self, lines: list[str], labels: list[str]) -> str | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        pattern = re.compile(rf"^(?:{label_pattern})\s*(?:name)?\s*[:\-]\s*(.+)$", re.IGNORECASE)
        for line in lines:
            match = pattern.search(line)
            if match:
                return self._clean_value(match.group(1))
        return None

    def _find_gwp_value(self, lines: list[str], context_terms: list[str]) -> float | None:
        for line in lines:
            line_lower = line.lower()
            if "gwp" not in line_lower and "global warming potential" not in line_lower:
                continue
            if not any(term in line_lower for term in context_terms):
                continue
            numbers = self._numbers_from_line(line)
            if numbers:
                return numbers[-1]
        return None

    def _find_primary_gwp_value(self, lines: list[str]) -> float:
        without_biogenic = self._find_gwp_value(
            lines,
            [
                "without biogenic",
                "excluding biogenic",
                "excl. biogenic",
                "without bio",
                "excluding bio",
                "excl. bio",
            ],
        )
        if without_biogenic is not None:
            return without_biogenic

        for line in lines:
            line_lower = line.lower()
            if "gwp" not in line_lower and "global warming potential" not in line_lower:
                continue
            if any(term in line_lower for term in ["with biogenic", "including biogenic"]):
                continue
            numbers = self._numbers_from_line(line)
            if numbers:
                return numbers[-1]

        raise ValueError("Could not extract mandatory GWP 100 value excluding biogenic carbon")

    def _find_unit(self, lines: list[str]) -> str | None:
        unit_pattern = re.compile(
            r"(kg\s*CO2e(?:q)?\s*/\s*(?:kg|t|ton|tonne|unit|piece|m2|m3)[\w\s]*)",
            re.IGNORECASE,
        )
        for line in lines:
            match = unit_pattern.search(line)
            if match:
                return self._clean_value(match.group(1))
        return None

    def _find_reference_year(self, lines: list[str]) -> int | None:
        for line in lines:
            line_lower = line.lower()
            if not any(token in line_lower for token in ["reference year", "data collection", "year"]):
                continue
            match = re.search(r"\b(20[0-9]{2}|19[9][0-9])\b", line)
            if match:
                return int(match.group(1))
        return None

    def _find_terms(self, text: str, terms: list[str]) -> list[str]:
        return [term for term in terms if re.search(re.escape(term), text, flags=re.IGNORECASE)]

    def _find_first_term(self, text: str, terms: list[str], normalize: bool = False) -> str | None:
        matches = self._find_terms(text, terms)
        if not matches:
            return None
        if normalize:
            return matches[0].replace(" to ", "-to-").lower()
        return matches[0]

    def _find_databases(self, lines: list[str]) -> list[SecondaryDatabase]:
        found: dict[str, SecondaryDatabase] = {}
        for line in lines:
            for database in self._DATABASES:
                if not re.search(re.escape(database), line, flags=re.IGNORECASE):
                    continue
                version = self._find_version_near_database(line, database)
                canonical_name = self._canonical_database_name(line, database)
                found[canonical_name.lower()] = SecondaryDatabase(name=canonical_name, version=version)
        return list(found.values())

    def _find_version_near_database(self, line: str, database: str) -> str | None:
        pattern = re.compile(
            rf"{re.escape(database)}[^\d\n]{{0,60}}(?:v|version)?\s*([0-9]+(?:\.[0-9]+)*)",
            re.IGNORECASE,
        )
        match = pattern.search(line)
        return match.group(1) if match else None

    def _canonical_database_name(self, line: str, database: str) -> str:
        if database.lower() == "sphera" and re.search(
            r"sphera\s+managed\s+content",
            line,
            flags=re.IGNORECASE,
        ):
            return "Sphera Managed Content"
        return database

    def _numbers_from_line(self, line: str) -> list[float]:
        values: list[float] = []
        for raw in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:[.,]\d+)?", line):
            normalized = raw.replace(",", ".")
            try:
                value = float(normalized)
            except ValueError:
                continue
            if value == 100 and "gwp" in line.lower():
                continue
            values.append(value)
        return values

    def _clean_value(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip(" .;")
