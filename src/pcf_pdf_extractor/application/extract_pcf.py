from pathlib import Path

from pcf_pdf_extractor.domain import PCFRecord, assess_minimum_requirements
from pcf_pdf_extractor.enrichment.reference_data import ReferenceDataEnricher
from pcf_pdf_extractor.extraction import HeuristicPcfExtractor, PcfExtractor
from pcf_pdf_extractor.infrastructure.source import SourceTextReaderSelector


class ExtractPcfFromSource:
    """Application use case: supported source file in, structured PCF records out."""

    def __init__(
        self,
        source_reader: SourceTextReaderSelector | None = None,
        extractor: PcfExtractor | None = None,
        enricher: ReferenceDataEnricher | None = None,
    ) -> None:
        self._source_reader = source_reader or SourceTextReaderSelector()
        self._extractor = extractor or HeuristicPcfExtractor()
        self._enricher = enricher

    def run(self, source_path: Path) -> list[PCFRecord]:
        document = self._source_reader.read(source_path)
        records = self._extractor.extract(document.text)
        for record in records:
            record.source_file = str(document.path)
            record.raw_text_sha256 = document.text_sha256
            record.minimum_requirements = assess_minimum_requirements(record)
            if self._enricher is not None:
                self._enricher.enrich(record)
        return records


ExtractPcfFromPdf = ExtractPcfFromSource
