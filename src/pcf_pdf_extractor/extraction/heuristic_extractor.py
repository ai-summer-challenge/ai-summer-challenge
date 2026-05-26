import re

from pcf_pdf_extractor.domain import (
    Gwp100Values,
    PCFRecord,
    SecondaryDatabase,
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

    def extract(self, text: str) -> PCFRecord:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        standards = self._find_terms(text, self._STANDARDS)
        secondary_databases = self._find_databases(lines)

        record = PCFRecord(
            company_name=self._find_labeled_value(lines, ["company", "supplier", "manufacturer"]),
            product_name=self._find_labeled_value(lines, ["product name", "product"]),
            biogenic_carbon_content=self._find_labeled_value(
                lines,
                ["biogenic carbon content", "bio carbon content", "biobased carbon content"],
            ),
            is_fossil_or_non_biobased_product=self._find_fossil_or_non_biobased(text),
            gwp100=Gwp100Values(
                with_biogenic_carbon=self._find_gwp_value(
                    lines,
                    ["with biogenic", "including biogenic", "incl. biogenic"],
                ),
                without_biogenic_carbon=self._find_gwp_value(
                    lines,
                    ["without biogenic", "excluding biogenic", "excl. biogenic"],
                ),
                unit=self._find_unit(lines),
            ),
            system_boundary=self._find_first_term(text, self._SYSTEM_BOUNDARIES, normalize=True),
            standards=standards,
            product_location=self._find_labeled_value(
                lines,
                ["product location", "production location", "country/region", "country"],
            ),
            reference_year=self._find_reference_year(lines),
            impact_assessment_method=self._find_first_term(text, self._IMPACT_METHODS),
            secondary_databases=secondary_databases,
            extraction_notes=[
                "Extracted with heuristic rules. Review missing or surprising fields before shipping."
            ],
        )
        record.minimum_requirements = assess_minimum_requirements(record)
        return record

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

    def _find_fossil_or_non_biobased(self, text: str) -> bool | None:
        text_lower = text.lower()
        positive_terms = [
            "fossil product",
            "fossil-based",
            "fossil based",
            "not biobased",
            "not bio-based",
            "non-biobased",
            "non bio-based",
            "biogenic carbon content: 0",
            "biogenic carbon content 0",
        ]
        negative_terms = ["biobased product", "bio-based product", "renewable carbon"]
        if any(term in text_lower for term in positive_terms):
            return True
        if any(term in text_lower for term in negative_terms):
            return False
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
                canonical_name = database
                found[canonical_name.lower()] = SecondaryDatabase(name=canonical_name, version=version)
        return list(found.values())

    def _find_version_near_database(self, line: str, database: str) -> str | None:
        pattern = re.compile(
            rf"{re.escape(database)}(?:\s*(?:database)?\s*)?(?:v|version)?\s*([0-9]+(?:\.[0-9]+)*)",
            re.IGNORECASE,
        )
        match = pattern.search(line)
        return match.group(1) if match else None

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
