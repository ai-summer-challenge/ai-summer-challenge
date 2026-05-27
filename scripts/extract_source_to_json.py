#!/usr/bin/env python
import argparse
from pathlib import Path

from pcf_pdf_extractor.application import ExtractPcfFromSource
from pcf_pdf_extractor.cli import _write_records
from pcf_pdf_extractor.config import get_settings
from pcf_pdf_extractor.extraction import ExtractorKind, build_extractor


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
    args = parser.parse_args()

    settings = get_settings()
    extractor = build_extractor(ExtractorKind(args.extractor), settings)
    records = ExtractPcfFromSource(extractor=extractor).run(args.source_path)
    written_paths = _write_records(records, args.output)
    for path in written_paths:
        print(path)


if __name__ == "__main__":
    main()
