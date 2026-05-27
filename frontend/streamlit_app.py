import json
import os
from typing import Any

import streamlit as st

from frontend.api_client import BackendApiError, PcfBackendClient
from frontend.review import RecordReviewEdits, apply_record_review_edits

DEFAULT_BACKEND_API_URL = "http://127.0.0.1:8000"


def main() -> None:
    st.set_page_config(page_title="PCF Review Cockpit", layout="wide")
    _ensure_session_state()

    st.title("PCF Review Cockpit")

    backend_client = PcfBackendClient(_backend_api_url())
    extractor_kind, uploaded_pdf = _render_sidebar()
    if uploaded_pdf is None and not st.session_state.records:
        st.info("Upload a supplier PDF in the sidebar to extract and review PCF records.")
        return

    if st.session_state.error_message:
        st.error(st.session_state.error_message)

    records: list[dict[str, Any]] = st.session_state.records
    if not records:
        return

    selected_index = _render_record_selector(records)
    selected_record = records[selected_index]
    reviewed_record = _render_record_review(selected_record, selected_index)
    reviewed_record = _assess_reviewed_record(backend_client, reviewed_record)
    st.session_state.records[selected_index] = reviewed_record

    _render_requirements(reviewed_record)
    _render_json_export(reviewed_record, selected_index)


def _ensure_session_state() -> None:
    st.session_state.setdefault("records", [])
    st.session_state.setdefault("source_file_name", None)
    st.session_state.setdefault("error_message", None)


def _backend_api_url() -> str:
    return os.environ.get("BACKEND_API_URL", DEFAULT_BACKEND_API_URL)


def _render_sidebar() -> tuple[str, Any]:
    with st.sidebar:
        st.header("Extraction")
        st.caption(f"Backend: {_backend_api_url()}")
        extractor_kind = st.selectbox(
            "Extractor",
            options=["llm", "heuristic"],
            index=0,
            help="Use heuristic when LLM settings are not configured.",
        )
        uploaded_pdf = st.file_uploader("Supplier PDF", type=["pdf"])

        if st.button("Extract", type="primary", disabled=uploaded_pdf is None):
            if uploaded_pdf is not None:
                _extract_uploaded_pdf(uploaded_pdf, extractor_kind)

        if st.session_state.source_file_name:
            st.caption(f"Current file: {st.session_state.source_file_name}")
        if st.session_state.records:
            st.caption(f"Records extracted: {len(st.session_state.records)}")

    return extractor_kind, uploaded_pdf


def _extract_uploaded_pdf(uploaded_pdf: Any, extractor_kind: str) -> None:
    st.session_state.error_message = None
    backend_client = PcfBackendClient(_backend_api_url())
    try:
        records = backend_client.extract_pdf(
            file_name=uploaded_pdf.name,
            file_bytes=uploaded_pdf.getvalue(),
            extractor=extractor_kind,
        )
    except BackendApiError as exc:
        st.session_state.records = []
        st.session_state.error_message = (
            f"{exc}. If LLM extraction is not configured yet, switch to heuristic."
        )
        return
    except Exception as exc:
        st.session_state.records = []
        st.session_state.error_message = f"Extraction failed: {exc}"
        return

    if not records:
        st.session_state.records = []
        st.session_state.error_message = "No PCF records were extracted from this PDF."
        return

    st.session_state.records = records
    st.session_state.source_file_name = uploaded_pdf.name


def _render_record_selector(records: list[dict[str, Any]]) -> int:
    labels = [
        f"{index + 1:02d} - {record.get('product_name') or record.get('company_name') or 'Unnamed record'}"
        for index, record in enumerate(records)
    ]
    selected_label = st.selectbox("Extracted record", options=labels)
    return labels.index(selected_label)


def _render_record_review(record: dict[str, Any], record_index: int) -> dict[str, Any]:
    st.subheader("Review")
    left, right = st.columns(2)
    with left:
        company_name = st.text_input(
            "Company name",
            value=record.get("company_name") or "",
            key=f"company-name-{record_index}",
        )
        product_name = st.text_input(
            "Product name",
            value=record.get("product_name") or "",
            key=f"product-name-{record_index}",
        )
    with right:
        biogenic_carbon_content = st.text_input(
            "Biogenic carbon content",
            value=record.get("biogenic_carbon_content") or "",
            key=f"biogenic-carbon-{record_index}",
        )
        fossil_label = _fossil_label(record.get("is_fossil_or_non_biobased_product"))
        fossil_selection = st.selectbox(
            "Fossil or non-biobased product",
            options=["Unknown", "Yes", "No"],
            index=["Unknown", "Yes", "No"].index(fossil_label),
            key=f"fossil-product-{record_index}",
        )

    extraction_notes = record.get("extraction_notes") or []
    extraction_notes_text = st.text_area(
        "Extraction notes",
        value="\n".join(str(note) for note in extraction_notes),
        key=f"extraction-notes-{record_index}",
    )

    return apply_record_review_edits(
        record,
        RecordReviewEdits(
            company_name=company_name,
            product_name=product_name,
            biogenic_carbon_content=biogenic_carbon_content,
            is_fossil_or_non_biobased_product=_fossil_value(fossil_selection),
            extraction_notes_text=extraction_notes_text,
        ),
    )


def _assess_reviewed_record(
    backend_client: PcfBackendClient,
    reviewed_record: dict[str, Any],
) -> dict[str, Any]:
    try:
        return backend_client.assess_record(reviewed_record)
    except BackendApiError as exc:
        st.warning(f"Could not refresh minimum requirement checks: {exc}")
        return reviewed_record


def _render_requirements(record: dict[str, Any]) -> None:
    st.subheader("Minimum requirements")
    minimum_requirements = record.get("minimum_requirements") or {}
    requirement_rows = []
    for name, check in minimum_requirements.items():
        if not isinstance(check, dict):
            continue
        requirement_rows.append(
            {
                "requirement": name,
                "fulfilled": check.get("fulfilled"),
                "result": _format_result(check.get("result")),
                "evidence": check.get("evidence") or "",
                "reason": check.get("reason") or "",
            }
        )
    st.dataframe(requirement_rows, hide_index=True, use_container_width=True)


def _render_json_export(record: dict[str, Any], record_index: int) -> None:
    st.subheader("Reviewed JSON")
    payload = _without_none_values(record)
    formatted_json = json.dumps(payload, indent=2, ensure_ascii=False)
    st.code(formatted_json, language="json")
    st.download_button(
        "Download JSON",
        data=formatted_json + "\n",
        file_name=f"{record_index + 1:02d}-{_record_slug(record)}.json",
        mime="application/json",
    )


def _without_none_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_none_values(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_without_none_values(item) for item in value]
    return value


def _format_result(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _record_slug(record: dict[str, Any]) -> str:
    raw_name = record.get("product_name") or record.get("company_name") or "pcf-record"
    return "".join(character.lower() if character.isalnum() else "-" for character in raw_name).strip(
        "-"
    ) or "pcf-record"


def _fossil_label(value: Any) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Unknown"


def _fossil_value(label: str) -> bool | None:
    if label == "Yes":
        return True
    if label == "No":
        return False
    return None


if __name__ == "__main__":
    main()
