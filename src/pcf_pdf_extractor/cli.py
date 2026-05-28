import json
import re
from pathlib import Path
from typing import Annotated

import typer

from pcf_pdf_extractor.application import ExtractPcfFromSource
from pcf_pdf_extractor.config import get_settings
from pcf_pdf_extractor.domain import BooleanRequirementCheck, PCFRecord, PcfValueRequirementCheck
from pcf_pdf_extractor.enrichment import build_reference_data_enricher
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
    enrich_reference_data: Annotated[
        bool,
        typer.Option(
            "--enrich-reference-data/--no-enrich-reference-data",
            help="Map each extracted product to BAFU/Eclasses reference data after extraction.",
        ),
    ] = False,
) -> None:
    """Read a supported source file and emit one PCF JSON record per chemical/product."""

    settings = get_settings()
    pcf_extractor = build_extractor(extractor, settings)
    records = ExtractPcfFromSource(extractor=pcf_extractor).run(source_path)
    if not records:
        raise typer.BadParameter("No chemical/product PCF records were extracted from this source.")
    if enrich_reference_data:
        reference_enricher = build_reference_data_enricher(settings)
        for record in records:
            reference_enricher.enrich(record)
            _ensure_enrichment_fields(record)

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
def enrich(
    json_path: Annotated[
        Path,
        typer.Argument(help="Extracted PCF JSON file to enrich with BAFU/Eclasses data."),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional JSON file or directory for the enriched record(s).",
        ),
    ] = None,
) -> None:
    """Add expected BAFU GWP 100 and Eclasses Oil & Gas relevance to PCF JSON."""

    settings = get_settings()
    records = _read_records(json_path)
    reference_enricher = build_reference_data_enricher(settings)
    for record in records:
        reference_enricher.enrich(record)
        _ensure_enrichment_fields(record)

    if output is not None:
        written_paths = _write_records(records, output)
        for path in written_paths:
            typer.echo(f"Wrote enriched PCF record to {path}")
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


def _read_records(json_path: Path) -> list[PCFRecord]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [PCFRecord.model_validate(_normalize_legacy_record_payload(record)) for record in payload["records"]]
    if isinstance(payload, list):
        return [PCFRecord.model_validate(_normalize_legacy_record_payload(record)) for record in payload]
    return [PCFRecord.model_validate(_normalize_legacy_record_payload(payload))]


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
    _ensure_enrichment_fields(record)
    return record.model_dump(mode="json")


def _ensure_enrichment_fields(record: PCFRecord) -> None:
    if record.expected_gwp100_value is None:
        record.expected_gwp100_value = PcfValueRequirementCheck(
            fulfilled=False,
            reason="Enrichment did not provide a BAFU mapping result.",
            evidence=None,
            result=None,
        )
    if record.oil_gas_relevant is None:
        record.oil_gas_relevant = BooleanRequirementCheck(
            fulfilled=False,
            reason="Enrichment did not provide an Eclasses relevance result.",
            evidence=None,
            result=False,
        )
    if record.is_benchmarch_ok is None:
        record.is_benchmarch_ok = False
    if record.oil_and_gas_check_ok is None:
        record.oil_and_gas_check_ok = False


def _normalize_legacy_record_payload(payload: dict) -> dict:
    normalized = dict(payload)
    minimum_requirements = normalized.get("minimum_requirements")
    if isinstance(minimum_requirements, dict):
        secondary_databases = minimum_requirements.get("secondary_databases")
        if isinstance(secondary_databases, dict):
            secondary_result = secondary_databases.get("result")
            if isinstance(secondary_result, list):
                fulfilled = secondary_databases.get("fulfilled")
                secondary_databases["result"] = bool(fulfilled) if isinstance(fulfilled, bool) else bool(secondary_result)
        elif isinstance(secondary_databases, list):
            minimum_requirements["secondary_databases"] = {
                "fulfilled": bool(secondary_databases),
                "result": bool(secondary_databases),
                "evidence": None,
                "reason": "Migrated from legacy secondary_databases list field.",
            }

    expected = normalized.get("expected_gwp100_value")
    if isinstance(expected, dict) and "fulfilled" not in expected and "result" not in expected:
        normalized["expected_gwp100_value"] = {
            "fulfilled": True,
            "result": expected,
            "evidence": None,
            "reason": "Migrated from legacy expected_gwp100_value structure.",
        }
    elif expected is None:
        normalized["expected_gwp100_value"] = {
            "fulfilled": False,
            "result": None,
            "evidence": None,
            "reason": "No expected_gwp100_value was available.",
        }

    oil_gas = normalized.get("oil_gas_relevant")
    if isinstance(oil_gas, bool):
        normalized["oil_gas_relevant"] = {
            "fulfilled": True,
            "result": oil_gas,
            "evidence": None,
            "reason": "Migrated from legacy oil_gas_relevant boolean field.",
        }
    elif oil_gas is None:
        normalized["oil_gas_relevant"] = {
            "fulfilled": False,
            "result": False,
            "evidence": None,
            "reason": "No oil_gas_relevant value was available.",
        }

    if normalized.get("is_benchmarch_ok") is None:
        normalized["is_benchmarch_ok"] = False
    if normalized.get("oil_and_gas_check_ok") is None:
        normalized["oil_and_gas_check_ok"] = False

    return normalized
