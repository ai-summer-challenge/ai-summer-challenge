import json
import os
from typing import Any

import pandas as pd
import streamlit as st

from frontend.api_client import BackendApiError, PcfBackendClient
from frontend.review import RecordReviewEdits, apply_record_review_edits

DEFAULT_BACKEND_API_URL = "http://127.0.0.1:8000"
EVONIK_PRIMARY = "#981d85"
EVONIK_LIGHT = "#efd9ea"


def main() -> None:
    st.set_page_config(page_title="PCF Review Cockpit", layout="wide")
    _ensure_session_state()
    _apply_theme()

    if _show_start_screen():
        _render_start_screen()
        return

    backend_client = PcfBackendClient(_backend_api_url())
    _render_sidebar()

    if st.session_state.error_message:
        st.error(st.session_state.error_message)

    records: list[dict[str, Any]] = st.session_state.records
    _render_batch_results()

    if not records:
        return

    _render_records_overview(backend_client, records)


def _ensure_session_state() -> None:
    st.session_state.setdefault("records", [])
    st.session_state.setdefault("source_file_name", None)
    st.session_state.setdefault("error_message", None)
    st.session_state.setdefault("batch_results", [])


def _backend_api_url() -> str:
    return os.environ.get("BACKEND_API_URL", DEFAULT_BACKEND_API_URL)


def _render_sidebar() -> list[Any]:
    with st.sidebar:
        st.header("Extraction")
        st.caption(f"Backend: {_backend_api_url()}")
        uploaded_files = st.file_uploader(
            "Supplier files",
            accept_multiple_files=True,
            help="You can upload and run multiple source files in one batch.",
        )

        if st.button("Extract files", type="primary", disabled=not uploaded_files):
            _reset_extraction_state()
            _extract_uploaded_pdfs(uploaded_files)

        if st.session_state.source_file_name:
            st.caption(f"Last batch: {st.session_state.source_file_name}")
        if st.session_state.records:
            st.caption(f"Records extracted: {len(st.session_state.records)}")

    return uploaded_files


def _show_start_screen() -> bool:
    return not st.session_state.records and not st.session_state.batch_results


def _render_start_screen() -> None:
    left, center, right = st.columns([1, 1, 1], gap="small")
    with center:
        st.markdown(
            """
            <div class="start-shell">
              <div class="start-title">PCF Extractor</div>
              <div class="start-subtitle">Upload one or more supplier files.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div class='start-card compact'>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Supplier files",
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="start-upload-files",
        )
        if st.button("Extract", type="primary", disabled=not uploaded_files, key="start-extract"):
            _reset_extraction_state()
            _extract_uploaded_pdfs(uploaded_files)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def _extract_uploaded_pdfs(uploaded_pdfs: list[Any]) -> None:
    st.session_state.error_message = None
    backend_client = PcfBackendClient(_backend_api_url())
    all_records: list[dict[str, Any]] = []
    batch_results: list[dict[str, Any]] = []
    errors: list[str] = []
    total_steps = max(len(uploaded_pdfs) * 3, 1)
    completed_steps = 0

    status = st.status("Running extraction batch...", expanded=True)
    progress = st.progress(0, text="Initializing batch run...")

    for uploaded_pdf in uploaded_pdfs:
        status.write(f"Extracting data from `{uploaded_pdf.name}`")
        try:
            records = backend_client.extract_pdf(
                file_name=uploaded_pdf.name,
                file_bytes=uploaded_pdf.getvalue(),
                extractor="llm",
            )
        except BackendApiError as exc:
            batch_results.append(
                {
                    "file": uploaded_pdf.name,
                    "status": "error",
                    "records": 0,
                    "message": str(exc),
                }
            )
            errors.append(f"{uploaded_pdf.name}: {exc}")
            completed_steps += 3
            progress.progress(
                min(int((completed_steps / total_steps) * 100), 100),
                text=f"Failed: {uploaded_pdf.name}",
            )
            continue
        except Exception as exc:
            batch_results.append(
                {
                    "file": uploaded_pdf.name,
                    "status": "error",
                    "records": 0,
                    "message": str(exc),
                }
            )
            errors.append(f"{uploaded_pdf.name}: {exc}")
            completed_steps += 3
            progress.progress(
                min(int((completed_steps / total_steps) * 100), 100),
                text=f"Failed: {uploaded_pdf.name}",
            )
            continue

        completed_steps += 1
        progress.progress(
            min(int((completed_steps / total_steps) * 100), 100),
            text=f"Extracted: {uploaded_pdf.name}",
        )

        if not records:
            batch_results.append(
                {
                    "file": uploaded_pdf.name,
                    "status": "empty",
                    "records": 0,
                    "message": "No PCF records extracted.",
                }
            )
            completed_steps += 2
            progress.progress(
                min(int((completed_steps / total_steps) * 100), 100),
                text=f"No records: {uploaded_pdf.name}",
            )
            continue

        status.write(f"Validating minimum requirements for `{uploaded_pdf.name}`")
        refreshed_records: list[dict[str, Any]] = []
        for record in records:
            source_file_name = uploaded_pdf.name
            record["_source_file_name"] = uploaded_pdf.name
            try:
                refreshed_record = backend_client.assess_record(_without_ui_metadata(record))
                refreshed_record["_source_file_name"] = source_file_name
                refreshed_records.append(refreshed_record)
            except BackendApiError:
                refreshed_records.append(record)

        completed_steps += 1
        progress.progress(
            min(int((completed_steps / total_steps) * 100), 100),
            text=f"Validated: {uploaded_pdf.name}",
        )

        for refreshed_record in refreshed_records:
            all_records.append(refreshed_record)

        batch_results.append(
            {
                "file": uploaded_pdf.name,
                "status": "ok",
                "records": len(refreshed_records),
                "message": "",
            }
        )
        completed_steps += 1
        progress.progress(
            min(int((completed_steps / total_steps) * 100), 100),
            text=f"Finished: {uploaded_pdf.name}",
        )

    if not all_records:
        st.session_state.records = []
        st.session_state.batch_results = batch_results
        status.update(label="Batch finished with errors", state="error", expanded=True)
        progress.progress(100, text="Batch finished")
        if errors:
            st.session_state.error_message = "Batch extraction failed for all files."
        else:
            st.session_state.error_message = "No PCF records were extracted from the selected files."
        return

    st.session_state.records = all_records
    st.session_state.batch_results = batch_results
    st.session_state.source_file_name = f"{len(uploaded_pdfs)} file(s)"
    if errors:
        status.update(label="Batch finished with partial errors", state="error", expanded=False)
    else:
        status.update(label="Batch finished successfully", state="complete", expanded=False)
    progress.progress(100, text="Batch finished")
    if errors:
        st.session_state.error_message = "Some files failed. Check Batch results below."


def _reset_extraction_state() -> None:
    st.session_state.records = []
    st.session_state.batch_results = []
    st.session_state.source_file_name = None
    st.session_state.error_message = None
    _clear_review_widget_state()


def _clear_review_widget_state() -> None:
    dynamic_prefixes = (
        "company-name-",
        "product-name-",
        "extraction-notes-",
    )
    for key in list(st.session_state.keys()):
        if key.startswith(dynamic_prefixes):
            del st.session_state[key]


def _render_batch_results() -> None:
    results: list[dict[str, Any]] = st.session_state.batch_results
    if not results:
        return
    st.subheader("Batch results")
    total_files = len(results)
    ok_files = sum(1 for item in results if item.get("status") == "ok")
    empty_files = sum(1 for item in results if item.get("status") == "empty")
    error_files = sum(1 for item in results if item.get("status") == "error")
    total_records = sum(int(item.get("records") or 0) for item in results)

    metric_a, metric_b, metric_c, metric_d = st.columns(4)
    metric_a.metric("Files", total_files)
    metric_b.metric("Records", total_records)
    metric_c.metric("Successful", ok_files)
    metric_d.metric("With issues", empty_files + error_files)

    for item in results:
        file_name = str(item.get("file") or "unknown.pdf")
        status = str(item.get("status") or "unknown")
        records = int(item.get("records") or 0)
        message = str(item.get("message") or "")

        if status == "ok":
            badge = "<span class='batch-badge ok'>OK</span>"
            subtitle = f"{records} record(s) extracted"
        elif status == "empty":
            badge = "<span class='batch-badge empty'>EMPTY</span>"
            subtitle = "No records extracted"
        else:
            badge = "<span class='batch-badge error'>ERROR</span>"
            subtitle = message or "Extraction failed"

        st.markdown(
            (
                "<div class='batch-row'>"
                f"<div class='batch-main'><div class='batch-file'>{file_name}</div>"
                f"<div class='batch-sub'>{subtitle}</div></div>"
                f"<div class='batch-side'>{badge}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _render_records_overview(backend_client: PcfBackendClient, records: list[dict[str, Any]]) -> None:
    st.subheader("Chemicals")
    st.session_state.setdefault("selected_record_index", 0)

    overview_rows = []
    labels = []
    for index, record in enumerate(records):
        minimum_requirements = record.get("minimum_requirements") or {}
        total = 0
        fulfilled = 0
        for check in minimum_requirements.values():
            if not isinstance(check, dict):
                continue
            total += 1
            if check.get("fulfilled") is True:
                fulfilled += 1
        open_count = max(total - fulfilled, 0)
        labels.append(
            f"{index + 1:02d} | {record.get('product_name') or 'Unnamed'}"
        )
        minimum_requirements = record.get("minimum_requirements") or {}
        r1_standard = _requirement_status(minimum_requirements.get("accepted_standard"))
        r2_country = _requirement_status(minimum_requirements.get("production_location"))
        r3_ref_year = _requirement_status(minimum_requirements.get("reference_year"))
        r4_method = _requirement_status(minimum_requirements.get("impact_assessment_method"))
        r6_secondary_db = _requirement_status(minimum_requirements.get("secondary_databases"))
        r7_oil_gas_update = _requirement_status(minimum_requirements.get("oil_and_gas_update"))
        pcf_two = "PASS" if _two_pcf_ok(record) else "FAIL"
        deviation = _deviation_status(record)
        verdict = _verdict_status(
            r1_standard,
            r2_country,
            r3_ref_year,
            r4_method,
            pcf_two,
            r6_secondary_db,
            r7_oil_gas_update,
            deviation,
            open_count,
        )
        overview_rows.append(
            {
                "#": f"{index + 1:02d}",
                "Supplier": record.get("company_name") or "n/a",
                "Product": record.get("product_name") or "Unnamed",
                "O&G": _oil_gas_label(record),
                "R1 2 PCFs": pcf_two,
                "R2 Standard": r1_standard,
                "R3 Country": r2_country,
                "R4 Ref Year": r3_ref_year,
                "R5 Method": r4_method,
                "R6 Secondary DB": r6_secondary_db,
                "R7 O&G Update": r7_oil_gas_update,
                "Deviation vs Reference": deviation,
                "Verdict": verdict,
                "Recommendation": _recommendation_text(verdict, open_count),
                "source": record.get("_source_file_name") or "unknown",
            }
        )

    overview_df = pd.DataFrame(overview_rows)
    styled_overview = overview_df.style.apply(
        lambda row: [
            (
                "background-color: #e7f6ef; color: #136f47; font-weight: 700;"
                if str(row[column]).upper() in {"PASS", "ACCEPT", "YES"}
                else (
                    "background-color: #fff3d6; color: #8f5a00; font-weight: 700;"
                    if str(row[column]).upper() in {"PARTIAL", "CONDITIONAL ACCEPT"}
                    else (
                        "background-color: #fde9ef; color: #a0233e; font-weight: 700;"
                        if str(row[column]).upper() in {"FAIL", "REJECT", "NO"}
                        else ""
                    )
                )
            )
            for column in overview_df.columns
        ],
        axis=1,
    )

    st.dataframe(
        styled_overview,
        hide_index=True,
        use_container_width=True,
    )
    selected_label = st.selectbox("Select chemical", options=labels)
    selected_index = labels.index(selected_label)
    st.session_state.selected_record_index = selected_index

    selected_record = records[selected_index]
    reviewed_record = _render_record_review(selected_record, selected_index)
    reviewed_record = _assess_reviewed_record(backend_client, reviewed_record)
    st.session_state.records[selected_index] = reviewed_record
    _render_requirements(reviewed_record)
    _render_json_export(reviewed_record, selected_index)
    return

def _render_record_review(record: dict[str, Any], record_index: int) -> dict[str, Any]:
    st.subheader("Review")
    names_left, names_right = st.columns(2)
    with names_left:
        product_name = st.text_input(
            "Product name",
            value=record.get("product_name") or "",
            key=f"product-name-{record_index}",
        )
    with names_right:
        company_name = st.text_input(
            "Company name",
            value=record.get("company_name") or "",
            key=f"company-name-{record_index}",
        )

    gwp_left, gwp_right = st.columns(2)
    with gwp_left:
        st.metric("GWP100 excl. biogenic", _gwp_display(record, "gwp100_excluding_biogenic"))
    with gwp_right:
        st.metric("GWP100 incl. biogenic", _gwp_display(record, "gwp100_including_biogenic"))
    expected_left, _ = st.columns(2)
    with expected_left:
        st.metric("Expected GWP100 (reference)", _expected_gwp_display(record))
    biogenic_carbon_content = record.get("biogenic_carbon_content")

    extraction_notes = record.get("extraction_notes") or []
    extraction_notes_text = "\n".join(str(note) for note in extraction_notes)

    return apply_record_review_edits(
        record,
        RecordReviewEdits(
            company_name=company_name,
            product_name=product_name,
            biogenic_carbon_content=biogenic_carbon_content,
            is_fossil_or_non_biobased_product=record.get("is_fossil_or_non_biobased_product"),
            extraction_notes_text=extraction_notes_text,
        ),
    )


def _assess_reviewed_record(
    backend_client: PcfBackendClient,
    reviewed_record: dict[str, Any],
) -> dict[str, Any]:
    assessment_payload = _without_ui_metadata(reviewed_record)
    try:
        refreshed = backend_client.assess_record(assessment_payload)
        # Keep UI metadata for navigation in the frontend.
        if "_source_file_name" in reviewed_record:
            refreshed["_source_file_name"] = reviewed_record["_source_file_name"]
        return refreshed
    except BackendApiError as exc:
        st.warning(f"Could not refresh minimum requirement checks: {exc}")
        return reviewed_record


def _render_requirements(record: dict[str, Any]) -> None:
    st.subheader("Minimum requirements")
    minimum_requirements = record.get("minimum_requirements") or {}
    requirement_rows = []
    fulfilled_count = 0
    total_count = 0
    required_keys = [
        "system_boundary",
        "accepted_standard",
        "production_location",
        "reference_year",
        "impact_assessment_method",
        "secondary_databases",
        "is_benchmarch_ok",
        "oil_and_gas_update",
    ]

    for name in required_keys:
        if name == "is_benchmarch_ok":
            total_count += 1
            bench_value = record.get("is_benchmarch_ok")
            fulfilled = bench_value is True
            if fulfilled:
                fulfilled_count += 1
            requirement_rows.append(
                {
                    "requirement": "is_benchmarch_ok",
                    "fulfilled": bench_value,
                    "result": _format_result(bench_value),
                    "evidence": "",
                    "reason": "",
                }
            )
            continue

        check = minimum_requirements.get(name)
        if not isinstance(check, dict):
            total_count += 1
            requirement_rows.append(
                {
                    "requirement": "product_location" if name == "production_location" else name,
                    "fulfilled": None,
                    "result": "",
                    "evidence": "",
                    "reason": "Missing in backend payload.",
                }
            )
            continue

        total_count += 1
        fulfilled = check.get("fulfilled") is True
        if fulfilled:
            fulfilled_count += 1
        requirement_rows.append(
            {
                "requirement": "product_location" if name == "production_location" else name,
                "fulfilled": check.get("fulfilled"),
                "result": _format_result(check.get("result")),
                "evidence": check.get("evidence") or "",
                "reason": check.get("reason") or "",
            }
        )

    missing_count = max(total_count - fulfilled_count, 0)
    all_passed = total_count > 0 and missing_count == 0
    if all_passed:
        st.success("All minimum requirements are fulfilled for this record.")
    else:
        st.warning(f"{missing_count} requirement(s) still open.")

    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Total", total_count)
    metric_b.metric("Fulfilled", fulfilled_count)
    metric_c.metric("Open", missing_count)

    st.dataframe(requirement_rows, hide_index=True, use_container_width=True)


def _render_json_export(record: dict[str, Any], record_index: int) -> None:
    st.subheader("Reviewed JSON")
    payload = _without_none_values(_without_ui_metadata(record))
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


def _without_ui_metadata(record: dict[str, Any]) -> dict[str, Any]:
    # Keep only fields accepted by the strict PCFRecord backend schema.
    allowed_top_level_keys = {
        "source_file",
        "raw_text_sha256",
        "company_name",
        "product_name",
        "expected_gwp100_value",
        "oil_gas_relevant",
        "is_benchmarch_ok",
        "oil_and_gas_check_ok",
        "minimum_requirements",
        "extraction_notes",
    }
    return {
        key: value
        for key, value in record.items()
        if key in allowed_top_level_keys and not key.startswith("_")
    }


def _format_result(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _gwp_display(record: dict[str, Any], requirement_key: str) -> str:
    minimum_requirements = record.get("minimum_requirements") or {}
    check = minimum_requirements.get(requirement_key)
    if not isinstance(check, dict):
        return "n/a"

    result = check.get("result")
    if not isinstance(result, dict):
        return "n/a"

    value = result.get("value")
    unit = result.get("unit")
    if value is None:
        return "n/a"
    if isinstance(unit, str) and unit.strip():
        return f"{value} {unit}"
    return str(value)


def _expected_gwp_display(record: dict[str, Any]) -> str:
    expected_payload = record.get("expected_gwp100_value")
    if not isinstance(expected_payload, dict):
        return "n/a"
    result = expected_payload.get("result")
    if not isinstance(result, dict):
        return "n/a"
    value = result.get("value")
    unit = result.get("unit")
    if value is None:
        return "n/a"
    if isinstance(unit, str) and unit.strip():
        return f"{value} {unit}"
    return str(value)


def _record_slug(record: dict[str, Any]) -> str:
    raw_name = record.get("product_name") or record.get("company_name") or "pcf-record"
    return "".join(character.lower() if character.isalnum() else "-" for character in raw_name).strip(
        "-"
    ) or "pcf-record"


def _overall_result_label(record: dict[str, Any], open_requirements: int | None = None) -> str:
    # Preferred backend field (planned): requirements_status
    backend_value = str(record.get("requirements_status") or "").strip().lower()
    if backend_value in {"fulfilled", "rejected", "missing"}:
        return backend_value

    if open_requirements is None:
        minimum_requirements = record.get("minimum_requirements") or {}
        total = 0
        fulfilled = 0
        for check in minimum_requirements.values():
            if not isinstance(check, dict):
                continue
            total += 1
            if check.get("fulfilled") is True:
                fulfilled += 1
        open_requirements = max(total - fulfilled, 0)

    return "fulfilled" if open_requirements == 0 else "missing"


def _two_pcf_ok(record: dict[str, Any]) -> bool:
    minimum_requirements = record.get("minimum_requirements") or {}
    gwp_excl = minimum_requirements.get("gwp100_excluding_biogenic") or {}
    gwp_incl = minimum_requirements.get("gwp100_including_biogenic") or {}

    excl_fulfilled = isinstance(gwp_excl, dict) and gwp_excl.get("fulfilled") is True
    incl_fulfilled = isinstance(gwp_incl, dict) and gwp_incl.get("fulfilled") is True

    oil_relevant_payload = record.get("oil_gas_relevant")
    oil_relevant: bool | None = None
    if isinstance(oil_relevant_payload, dict):
        oil_relevant = oil_relevant_payload.get("result")
    elif isinstance(oil_relevant_payload, bool):
        oil_relevant = oil_relevant_payload

    if oil_relevant is True and excl_fulfilled:
        return True
    if oil_relevant is False and excl_fulfilled and incl_fulfilled:
        return True
    return False


def _requirement_status(check: Any) -> str:
    if not isinstance(check, dict):
        return "MISSING"
    return "PASS" if check.get("fulfilled") is True else "FAIL"


def _oil_gas_label(record: dict[str, Any]) -> str:
    payload = record.get("oil_gas_relevant")
    value: bool | None = None
    if isinstance(payload, dict):
        value = payload.get("result")
    elif isinstance(payload, bool):
        value = payload
    if value is True:
        return "YES"
    if value is False:
        return "NO"
    return "N/A"


def _deviation_status(record: dict[str, Any]) -> str:
    value = record.get("is_benchmarch_ok")
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "N/A"


def _verdict_status(
    r1_standard: str,
    r2_country: str,
    r3_ref_year: str,
    r4_method: str,
    pcf_two: str,
    r6_secondary_db: str,
    r7_oil_gas_update: str,
    deviation: str,
    open_count: int,
) -> str:
    hard_fails = [r1_standard, r2_country, r3_ref_year, r4_method]
    if any(item == "FAIL" for item in hard_fails):
        return "REJECT"
    if pcf_two == "PASS" and r6_secondary_db == "PASS" and (deviation in {"PASS", "N/A"}) and open_count == 0:
        return "ACCEPT"
    if pcf_two == "FAIL" or r7_oil_gas_update == "FAIL":
        return "CONDITIONAL ACCEPT"
    return "CONDITIONAL ACCEPT"


def _recommendation_text(verdict: str, open_count: int) -> str:
    if verdict == "ACCEPT":
        return "ACCEPT"
    if verdict == "REJECT":
        return "REJECT - complete missing mandatory requirements."
    return f"CONDITIONAL - review {open_count} open requirement(s)."


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


def _apply_theme() -> None:
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] {{
            background: {EVONIK_LIGHT};
        }}
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(180deg, #ffffff 0%, #fbf5fa 100%);
        }}
        .stButton > button[kind="primary"] {{
            background-color: {EVONIK_PRIMARY};
            border-color: {EVONIK_PRIMARY};
            color: #ffffff !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: #7f176f;
            border-color: #7f176f;
            color: #ffffff !important;
        }}
        h1, h2, h3 {{
            color: {EVONIK_PRIMARY};
        }}
        .start-shell {{
            margin: 18vh auto 0 auto;
            width: min(33vw, 480px);
            min-width: 320px;
            text-align: center;
        }}
        .start-title {{
            font-size: 2rem;
            font-weight: 500;
            color: #1f1f1f;
            letter-spacing: 0;
        }}
        .start-subtitle {{
            margin-top: 4px;
            color: #6a6a6a;
            font-size: 0.98rem;
        }}
        .start-card {{
            margin: 18px auto 0 auto;
            max-width: 760px;
            border: 0;
            border-radius: 0;
            padding: 8px 0 0 0;
            background: transparent;
            box-shadow: none;
        }}
        .start-card.compact {{
            width: min(33vw, 480px);
            min-width: 320px;
            padding: 4px 0 0 0;
            text-align: center;
            margin-left: auto;
            margin-right: auto;
        }}
        .start-card.compact [data-testid="stFileUploader"] {{
            width: 100%;
            max-width: 100%;
            margin: 0 auto;
        }}
        .start-card.compact [data-testid="stFileUploader"] > div {{
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 auto !important;
        }}
        .start-card.compact [data-testid="stFileUploaderDropzone"] {{
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 auto !important;
        }}
        .start-card.compact .stButton > button {{
            width: 160px;
            border-radius: 999px;
            margin-top: 8px;
            margin-left: auto;
            margin-right: auto;
            display: block;
            color: #ffffff !important;
        }}
        .start-card.compact section[data-testid="stFileUploaderDropzone"] {{
            border-radius: 999px;
            border: 1px solid #ddd;
            min-height: 44px;
            background: #f3f3f3;
            padding-top: 4px;
            padding-bottom: 4px;
        }}
        .start-card.compact [data-testid="stFileUploaderDropzoneInstructions"] {{
            width: 100%;
            text-align: center;
        }}
        .start-card.compact [data-testid="stFileUploaderDropzoneInstructions"] > div {{
            font-size: 0.93rem;
            color: #646464;
        }}
        .start-card.compact small {{
            color: #7c7c7c;
        }}
        @media (max-width: 900px) {{
            .start-shell {{
                margin-top: 14vh;
                width: 92vw;
                min-width: unset;
            }}
            .start-title {{
                font-size: 1.6rem;
            }}
            .start-card.compact {{
                border-radius: 16px;
                width: 92vw;
                min-width: unset;
            }}
        }}
        .batch-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #e6e1e6;
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 8px;
            background: #ffffff;
        }}
        .batch-main {{
            min-width: 0;
        }}
        .batch-file {{
            font-weight: 600;
            color: #222;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 80vw;
        }}
        .batch-sub {{
            color: #666;
            font-size: 0.86rem;
            margin-top: 2px;
        }}
        .batch-badge {{
            border-radius: 999px;
            padding: 3px 10px;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0;
        }}
        .batch-badge.ok {{
            color: #136f47;
            background: #e7f6ef;
        }}
        .batch-badge.empty {{
            color: #8f5a00;
            background: #fff3d6;
        }}
        .batch-badge.error {{
            color: #a0233e;
            background: #fde9ef;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
