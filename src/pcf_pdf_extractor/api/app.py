import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from pcf_pdf_extractor.application import ExtractPcfFromPdf
from pcf_pdf_extractor.config import Settings, get_settings
from pcf_pdf_extractor.domain import PCFExtractionResult, PCFRecord, assess_minimum_requirements
from pcf_pdf_extractor.extraction import ExtractorKind, build_extractor

app = FastAPI(title="PCF PDF Extractor API")


class ErrorResponse(BaseModel):
    detail: str


class RuntimeStatusResponse(BaseModel):
    llm_available: bool
    llm_message: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/runtime", response_model=RuntimeStatusResponse)
def runtime_status() -> RuntimeStatusResponse:
    settings = get_settings()
    llm_available, llm_message = _llm_runtime_status(settings)
    return RuntimeStatusResponse(llm_available=llm_available, llm_message=llm_message)


@app.post(
    "/api/extract",
    response_model=PCFExtractionResult,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def extract_pdf(
    file: Annotated[UploadFile, File(description="Supplier PDF containing PCF information.")],
    extractor: Annotated[ExtractorKind, Form()] = ExtractorKind.LLM,
) -> PCFExtractionResult:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Expected a PDF upload.")

    temporary_path = _write_upload_to_temporary_pdf(file)
    try:
        pcf_extractor = build_extractor(extractor, get_settings())
        records = ExtractPcfFromPdf(extractor=pcf_extractor).run(temporary_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        temporary_path.unlink(missing_ok=True)

    if not records:
        raise HTTPException(status_code=400, detail="No PCF records were extracted from this PDF.")
    return PCFExtractionResult(records=records)


@app.post("/api/records/assess", response_model=PCFRecord)
def assess_record(record: PCFRecord) -> PCFRecord:
    reviewed_record = record.model_copy(deep=True)
    reviewed_record.minimum_requirements = assess_minimum_requirements(reviewed_record)
    return reviewed_record


def _write_upload_to_temporary_pdf(file: UploadFile) -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporary_pdf:
        temporary_pdf.write(file.file.read())
        return Path(temporary_pdf.name)


def _llm_runtime_status(settings: Settings) -> tuple[bool, str | None]:
    missing_fields = []
    if settings.llm_api_base_url is None:
        missing_fields.append("LLM_API_BASE_URL")
    if settings.llm_api_key is None:
        missing_fields.append("LLM_API_KEY")
    if settings.llm_model is None:
        missing_fields.append("LLM_MODEL")

    if missing_fields:
        return False, f"Missing: {', '.join(missing_fields)}"
    return True, None
