#!/usr/bin/env python
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pcf_pdf_extractor.application import ExtractPcfFromSource  # noqa: E402
from pcf_pdf_extractor.cli import _ensure_enrichment_fields, _write_records  # noqa: E402
from pcf_pdf_extractor.config import get_settings  # noqa: E402
from pcf_pdf_extractor.enrichment import build_reference_data_enricher  # noqa: E402
from pcf_pdf_extractor.extraction import ExtractorKind, build_extractor  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract PCF JSON records from a PDF, Excel workbook, or email body file."
    )
    parser.add_argument("source_path", type=Path)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument(
        "--extractor",
        "-x",
        choices=[kind.value for kind in ExtractorKind],
        default=ExtractorKind.LLM.value,
    )
    parser.add_argument(
        "--enrich-reference-data",
        action="store_true",
        help="Map extracted records to BAFU/Eclasses reference data before writing JSON.",
    )
    args = parser.parse_args()

    settings = get_settings()
    extractor = build_extractor(ExtractorKind(args.extractor), settings)
    records = ExtractPcfFromSource(extractor=extractor).run(args.source_path)
    if args.enrich_reference_data:
        reference_enricher = build_reference_data_enricher(settings)
        for record in records:
            reference_enricher.enrich(record)
            _ensure_enrichment_fields(record)
    written_paths = _write_records(records, args.output)
    for path in written_paths:
        print(path)


if __name__ == "__main__":
    main()
