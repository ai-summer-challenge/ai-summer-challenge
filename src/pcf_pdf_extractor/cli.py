import json
from pathlib import Path
from typing import Annotated

import typer

from pcf_pdf_extractor.application import ExtractPcfFromPdf
from pcf_pdf_extractor.config import get_settings
from pcf_pdf_extractor.domain import PCFRecord
from pcf_pdf_extractor.extraction import ExtractorKind, build_extractor
from pcf_pdf_extractor.infrastructure.api import CompanyApiClient

app = typer.Typer(no_args_is_help=True, help="Extract and ship Product Carbon Footprint data.")


@app.command()
def extract(
    pdf_path: Annotated[Path, typer.Argument(help="Supplier PDF containing PCF information.")],
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
        typer.Option("--output", "-o", help="Optional JSON file to write the extracted record to."),
    ] = None,
) -> None:
    """Read a PDF and emit a structured PCF JSON record."""

    settings = get_settings()
    pcf_extractor = build_extractor(extractor, settings)
    record = ExtractPcfFromPdf(extractor=pcf_extractor).run(pdf_path)
    payload = record.model_dump(mode="json", exclude_none=True)
    formatted = json.dumps(payload, indent=2, ensure_ascii=False)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(formatted + "\n", encoding="utf-8")
        typer.echo(f"Wrote extracted PCF record to {output}")
        return

    typer.echo(formatted)


@app.command()
def ship(
    json_path: Annotated[Path, typer.Argument(help="Extracted PCF JSON file to submit.")],
) -> None:
    """Submit a structured PCF JSON record to the configured company API."""

    record = PCFRecord.model_validate_json(json_path.read_text(encoding="utf-8"))
    client = CompanyApiClient.from_settings(get_settings())
    response_payload = client.submit_pcf_record(record)
    typer.echo(json.dumps(response_payload, indent=2, ensure_ascii=False))
