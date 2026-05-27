import json
import re
from pathlib import Path
from typing import Annotated

import typer

from pcf_pdf_extractor.application import ExtractPcfFromSource
from pcf_pdf_extractor.config import get_settings
from pcf_pdf_extractor.domain import PCFRecord
from pcf_pdf_extractor.extraction import ExtractorKind, build_extractor
from pcf_pdf_extractor.infrastructure.api import CompanyApiClient

app = typer.Typer(no_args_is_help=True, help="Extract and ship Product Carbon Footprint data.")


@app.command()
def extract(
    source_path: Annotated[
        Path,
        typer.Argument(help="Supplier source file containing PCF information."),
    ],
    extractor: Annotated[
        ExtractorKind,
        typer.Option(
            "--extractor",
            "-x",
            help="Extraction strategy to use.",
            case_sensitive=False,
        ),
    ] = ExtractorKind.LLM,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Optional JSON file or directory. Multi-chemical sources are written as one "
                "JSON file per chemical."
            ),
        ),
    ] = None,
) -> None:
    """Read a supported source file and emit one PCF JSON record per chemical/product."""

    settings = get_settings()
    pcf_extractor = build_extractor(extractor, settings)
    records = ExtractPcfFromSource(extractor=pcf_extractor).run(source_path)
    if not records:
        raise typer.BadParameter("No chemical/product PCF records were extracted from this source.")

    if output is not None:
        written_paths = _write_records(records, output)
        for path in written_paths:
            typer.echo(f"Wrote extracted PCF record to {path}")
        return

    payload: object
    if len(records) == 1:
        payload = _record_payload(records[0])
    else:
        payload = [_record_payload(record) for record in records]
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command()
def ship(
    json_path: Annotated[Path, typer.Argument(help="Extracted PCF JSON file to submit.")],
) -> None:
    """Submit a structured PCF JSON record to the configured company API."""

    record = PCFRecord.model_validate_json(json_path.read_text(encoding="utf-8"))
    client = CompanyApiClient.from_settings(get_settings())
    response_payload = client.submit_pcf_record(record)
    typer.echo(json.dumps(response_payload, indent=2, ensure_ascii=False))


def _write_records(records: list[PCFRecord], output: Path) -> list[Path]:
    if len(records) == 1 and output.suffix.lower() == ".json" and not output.is_dir():
        formatted = json.dumps(
            _record_payload(records[0]),
            indent=2,
            ensure_ascii=False,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(formatted + "\n", encoding="utf-8")
        return [output]

    output_dir = _record_output_dir(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []
    for index, record in enumerate(records, start=1):
        filename = f"{index:02d}-{_record_slug(record, index)}.json"
        path = output_dir / filename
        formatted = json.dumps(
            _record_payload(record),
            indent=2,
            ensure_ascii=False,
        )
        path.write_text(formatted + "\n", encoding="utf-8")
        written_paths.append(path)
    return written_paths


def _record_output_dir(output: Path) -> Path:
    if output.suffix.lower() == ".json" and not output.is_dir():
        return output.with_suffix("")
    return output


def _record_slug(record: PCFRecord, index: int) -> str:
    raw_name = record.product_name or record.company_name or f"chemical-{index:02d}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw_name).strip("-").lower()
    return slug or f"chemical-{index:02d}"


def _record_payload(record: PCFRecord) -> dict:
    return record.model_dump(mode="json")
