import json
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

# Ensure UTF-8 stdout if needed
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# CONFIGURATION & PATHS
# ============================================================

RAW_FOLDER = Path("data/raw/tender_001")
PROCESSED_FOLDER = Path("data/processed/tender_001")

TENDER_FOLDER = RAW_FOLDER / "tender"
TENDER_FOLDER.mkdir(parents=True, exist_ok=True)
PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Tender & Multi-Bidder Analysis System",
    page_icon="📑",
    layout="wide"
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def save_uploaded_file(uploaded_file, destination_folder):
    """Save an uploaded Streamlit file buffer to disk."""
    if uploaded_file is None:
        return None
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination = destination_folder / uploaded_file.name
    with open(destination, "wb") as file:
        file.write(uploaded_file.getbuffer())
    return destination


def load_json(path):
    """Safely load a JSON file from disk."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return None


def get_field_value(fields, field_name, default="Not available"):
    """Extract field value string from fields dictionary."""
    if not isinstance(fields, dict):
        return default
    information = fields.get(field_name)
    if isinstance(information, dict):
        val = information.get("value")
        return str(val) if val is not None else default
    if information is None:
        return default
    return str(information)


def get_field_page(fields, field_name):
    """Extract page number from fields dictionary."""
    if not isinstance(fields, dict):
        return ""
    information = fields.get(field_name)
    if isinstance(information, dict):
        page = information.get("page")
        return str(page) if page is not None else ""
    return ""


def get_field_evidence(fields, field_name):
    """Extract verbatim evidence excerpt from fields dictionary."""
    if not isinstance(fields, dict):
        return ""
    information = fields.get(field_name)
    if isinstance(information, dict):
        return str(information.get("evidence", ""))
    return ""


def sanitize_df_for_display(rows):
    """
    Ensure all values in row dictionaries are converted to strings/clean formats
    to prevent PyArrow mixed-type crashes.
    """
    if not rows:
        return []
    clean_rows = []
    for row in rows:
        clean_row = {}
        for key, val in row.items():
            if val is None:
                clean_row[key] = "-"
            elif isinstance(val, (list, dict)):
                clean_row[key] = json.dumps(val) if val else "-"
            else:
                clean_row[key] = str(val)
        clean_rows.append(clean_row)
    return clean_rows



def render_table(data, use_container_width=True):
    """
    Renders table using st.dataframe if pyarrow is functional,
    or falls back to clean, responsive markdown table if pyarrow is unavailable.
    """
    if data is None:
        st.info("No data available.")
        return
    sanitized = sanitize_df_for_display(data)
    try:
        st.dataframe(sanitized, use_container_width=use_container_width)
    except Exception:
        rows = sanitized
        if hasattr(rows, "to_dict"):
            rows = rows.to_dict(orient="records")
        if not isinstance(rows, list) or len(rows) == 0:
            st.info("No data rows available.")
            return
        headers = list(rows[0].keys())
        lines = []
        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for r in rows:
            lines.append("| " + " | ".join(str(r.get(h, "-")).replace("\n", " ").replace("|", "/") for h in headers) + " |")
        st.markdown("\n".join(lines))



def display_field_table(fields):
    """Render a structured table for extracted fields with page and evidence."""
    if not fields or not isinstance(fields, dict):
        st.info("No extracted fields available.")
        return

    rows = []
    for field_key, information in fields.items():
        if isinstance(information, dict):
            value = information.get("value", "")
            page = information.get("page", "")
            evidence = information.get("evidence", "")
        else:
            value = information
            page = ""
            evidence = ""

        label = str(field_key).replace("_", " ").title()
        evidence_snippet = str(evidence).strip().replace("\n", " ")
        if len(evidence_snippet) > 120:
            evidence_snippet = evidence_snippet[:120] + "..."

        rows.append({
            "Field": label,
            "Extracted Value": str(value) if value is not None else "-",
            "Source Page": f"Page {page}" if page else "-",
            "Evidence Excerpt": evidence_snippet if evidence_snippet else "-"
        })

    if rows:
        render_table(rows, use_container_width=True)
    else:
        st.info("No extracted fields available.")


def count_boq_issues(boq_items):
    """Count BOQ line items with arithmetic or missing data issues."""
    if not boq_items or not isinstance(boq_items, list):
        return 0
    count = 0
    for item in boq_items:
        status = str(item.get("status", "")).upper()
        issues = item.get("issues", [])
        if status == "ISSUE" or issues:
            count += 1
    return count


def find_total_quote(bidder_data):
    """Safely extract the total quoted bid price from bidder dictionary."""
    if not bidder_data:
        return "Not available"
    fields = bidder_data.get("bidder_fields", {})
    for key in [
        "total_quoted_amount",
        "quoted_amount",
        "total_bid_amount",
        "bid_amount"
    ]:
        if key in fields:
            value = fields[key]
            if isinstance(value, dict):
                return str(value.get("value", "Not available"))
            return str(value)
    return "Not available"


# ============================================================
# LOAD PERSISTED ARTIFACTS
# ============================================================

tender_file = PROCESSED_FOLDER / "tender.json"
comparison_file = PROCESSED_FOLDER / "bid_comparison.json"
tender_boq_file = PROCESSED_FOLDER / "tender_boq.json"
ranking_file = PROCESSED_FOLDER / "bidder_ranking.json"
names_file = RAW_FOLDER / "bidder_names.json"

tender_data = load_json(tender_file)
comparison_data = load_json(comparison_file)
tender_boq_data = load_json(tender_boq_file)
ranking_data = load_json(ranking_file)
names_data = load_json(names_file) or {}

# Dynamically load all processed bidder JSON files (bidder_A.json, bidder_B.json, bidder_C.json...)
all_bidders_data = {}
if PROCESSED_FOLDER.exists():
    for b_file in sorted(PROCESSED_FOLDER.glob("bidder_*.json"), key=lambda p: p.name):
        if b_file.name == "bidder_ranking.json":
            continue
        b_content = load_json(b_file)
        if b_content:
            all_bidders_data[b_file.stem] = b_content

# Fallback backwards-compatibility variables
bidder_a_data = all_bidders_data.get("bidder_A")
bidder_b_data = all_bidders_data.get("bidder_B")



# ============================================================
# SIDEBAR — DYNAMIC MULTI-BIDDER UPLOAD
# ============================================================

st.sidebar.title("📂 Document Upload")

with st.sidebar.expander("1. Common Tender", expanded=True):
    tender_pdf = st.file_uploader("Tender Document (PDF)", type=["pdf"], key="tender_pdf")
    tender_boq = st.file_uploader("Tender BOQ (Excel)", type=["xlsx", "xls"], key="tender_boq")

# Dynamic Bidder Count Selector
num_bidders = st.sidebar.number_input("Number of Bidders", min_value=2, max_value=8, value=2, step=1)

uploaded_bidders = []
for i in range(num_bidders):
    letter = chr(65 + i)
    bidder_id = f"bidder_{letter}"

    with st.sidebar.expander(f"Bidder {letter} Submission", expanded=(i < 2)):
        input_name = st.text_input(
            "Company Name",
            value="",
            placeholder=f"Enter name for Bidder {letter} (or leave blank)",
            key=f"name_{bidder_id}"
        )
        b_name = input_name.strip() if input_name.strip() else f"Bidder {letter}"
        b_tech = st.file_uploader("Technical Bid (PDF)", type=["pdf"], key=f"tech_{bidder_id}")
        b_fin = st.file_uploader("Financial Bid (PDF)", type=["pdf"], key=f"fin_{bidder_id}")
        b_boq = st.file_uploader("BOQ (Excel)", type=["xlsx", "xls"], key=f"boq_{bidder_id}")

        uploaded_bidders.append({
            "bidder_id": bidder_id,
            "letter": letter,
            "name": b_name,
            "tech_pdf": b_tech,
            "fin_pdf": b_fin,
            "boq_excel": b_boq
        })

analyze_button = st.sidebar.button("🔍 Analyze Documents", use_container_width=True, type="primary")

if analyze_button:
    missing_files = []
    if tender_pdf is None:
        missing_files.append("Common Tender Document (PDF)")
    if tender_boq is None:
        missing_files.append("Common Tender BOQ (Excel)")

    for b in uploaded_bidders:
        if b["tech_pdf"] is None:
            missing_files.append(f"{b['name']} ({b['bidder_id']}) — Technical Bid PDF")
        if b["fin_pdf"] is None:
            missing_files.append(f"{b['name']} ({b['bidder_id']}) — Financial Bid PDF")
        if b["boq_excel"] is None:
            missing_files.append(f"{b['name']} ({b['bidder_id']}) — BOQ Excel")

    if missing_files:
        st.sidebar.error("Please upload all required files:")
        for item in missing_files:
            st.sidebar.caption(f"• {item}")
    else:
        # Clear previous raw folders for active bidders & tender
        for folder in [TENDER_FOLDER] + [RAW_FOLDER / b["bidder_id"] for b in uploaded_bidders]:
            if folder.exists():
                for old_file in folder.iterdir():
                    if old_file.is_file():
                        try:
                            old_file.unlink()
                        except Exception:
                            pass

        # Save Common Tender
        save_uploaded_file(tender_pdf, TENDER_FOLDER)
        save_uploaded_file(tender_boq, TENDER_FOLDER)

        # Save each bidder's documents
        updated_names = {}
        for b in uploaded_bidders:
            b_folder = RAW_FOLDER / b["bidder_id"]
            save_uploaded_file(b["tech_pdf"], b_folder)
            save_uploaded_file(b["fin_pdf"], b_folder)
            save_uploaded_file(b["boq_excel"], b_folder)
            updated_names[b["bidder_id"]] = b["name"]

        # Persist bidder names map
        with open(names_file, "w", encoding="utf-8") as file:
            json.dump(updated_names, file, indent=4)

        with st.spinner("Executing multi-bidder pipeline (OCR, Extraction, BOQ Audit, RAG Indexing, Comparison)..."):
            sub_env = os.environ.copy()
            extra_paths = [
                r"D:\document-intelligence\.venv\Lib\site-packages",
                r"D:\Python\Lib\site-packages"
            ]
            current_pp = sub_env.get("PYTHONPATH", "")
            sub_env["PYTHONPATH"] = ";".join(extra_paths + ([current_pp] if current_pp else []))

            result = subprocess.run(
                [sys.executable, "main.py"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=sub_env
            )

        if result.returncode == 0:
            st.sidebar.success(f"Successfully processed Tender and {len(uploaded_bidders)} Bidders.")
            st.session_state["processing_output"] = result.stdout
            st.rerun()
        else:
            st.sidebar.error("Document processing failed.")
            st.sidebar.code(result.stderr)

# Display last execution log expander if available
if "processing_output" in st.session_state:
    with st.sidebar.expander("Terminal Execution Log", expanded=False):
        st.text(st.session_state["processing_output"])

st.sidebar.divider()
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Module",
    [
        "Dashboard",
        "Tender Overview",
        "BOQ Analysis",
        "Bid Comparison",
        "Bidder Ranking",
        "Risk Analysis",
        "RAG Assistant"
    ]
)

# ============================================================
# MODULE 1: DASHBOARD
# ============================================================
if page == "Dashboard":
    st.header("📊 Executive Tender & Multi-Bidder Evaluation Dashboard")
    st.caption("AI-assisted, evidence-grounded decision support for procurement and tender evaluation committees.")

    if tender_data is None:
        st.info("No processed tender data found. Please upload documents in the sidebar and click **Analyze Documents**.")
    else:
        tender_fields = tender_data.get("tender_fields", {})
        tender_no = get_field_value(tender_fields, "tender_number", "SIDA/WORKS/001/2026")
        org_name = get_field_value(tender_fields, "organisation", "Infrastructure Development Authority")
        project_name = get_field_value(tender_fields, "project_name", "Building Construction")
        completion_period = get_field_value(tender_fields, "completion_period", "12 months")
        emd_req = get_field_value(tender_fields, "emd", "INR 5,00,000")
        perf_sec = get_field_value(tender_fields, "performance_security", "10%")

        # Row 1: Executive KPI Metrics
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Tender Identifier", tender_no)
        bidders_count = len(all_bidders_data)
        kpi2.metric("Bidders Evaluated", str(bidders_count))

        # Dynamic qualification counts
        summary_bidders = comparison_data.get("summary", {}).get("bidders", {}) if comparison_data else {}
        qual_count = sum(1 for b in summary_bidders.values() if b.get("non_compliant", 0) == 0)
        disqual_count = sum(1 for b in summary_bidders.values() if b.get("non_compliant", 0) > 0)
        kpi3.metric("Qualified / Non-Compliant", f"{qual_count} / {disqual_count}")

        recommended = comparison_data.get("recommended_bidder", "Pending") if comparison_data else "Pending"
        kpi4.metric("Recommended Bidder", recommended)

        st.divider()

        # Row 2: Tender Baseline Highlights
        st.subheader("📌 Key Tender Parameters")
        pcol1, pcol2, pcol3 = st.columns(3)
        with pcol1:
            st.markdown(f"**Organisation:** {org_name}")
            st.markdown(f"**Project:** {project_name}")
        with pcol2:
            st.markdown(f"**Earnest Money Deposit (EMD):** {emd_req}")
            st.markdown(f"**Completion Schedule:** {completion_period}")
        with pcol3:
            st.markdown(f"**Performance Security:** {perf_sec}")
            validity = get_field_value(tender_fields, "proposal_validity", "180 days")
            st.markdown(f"**Proposal Validity:** {validity}")

        st.divider()

        # Row 3: Bidder Evaluation Snapshot
        st.subheader("🏆 Evaluation Summary & Provisional Recommendation")
        rcol1, rcol2 = st.columns([3, 2])

        with rcol1:
            if comparison_data and recommended != "Pending":
                st.success(f"### Rank 1 — Recommended: {recommended}")
                reason_text = comparison_data.get("recommendation", "Satisfies all evaluated baseline criteria.")
                st.write(reason_text)

                next_bidder = comparison_data.get("next_eligible_bidder")
                if next_bidder and next_bidder != recommended:
                    st.info(f"**Next Eligible / Reserve Alternative:** {next_bidder}")
                    st.caption("Condition: Activated only if Rank 1 fails verification, withdraws, or is disqualified prior to contract award.")
            else:
                st.info("Evaluation results will appear here after document analysis.")

        with rcol2:
            st.markdown("#### Decision-Support Protocol")
            st.warning(
                "⚠️ **Disclaimer**: This system provides AI-assisted, evidence-grounded recommendations for evaluation committees. "
                "The software does not automatically award contracts; final procurement authority rests with the official tender committee."
            )

        # Row 4: Multi-Bidder Audit Highlights
        st.divider()
        st.subheader("🔍 Audit & BOQ Overview Across Bidders")
        scol1, scol2, scol3 = st.columns(3)

        tender_boq_count = len(tender_boq_data) if (tender_boq_data and isinstance(tender_boq_data, list)) else 0
        scol1.metric("Tender BOQ Line Items", tender_boq_count)

        # Summarize BOQ issues across all bidders
        b_issues_summary = []
        for b_id, b_data in all_bidders_data.items():
            name = b_data.get("bidder_name", b_id)
            issues = count_boq_issues(b_data.get("boq_validation", []))
            b_issues_summary.append(f"{name}: {issues}")

        scol2.metric("Total Bidders Analyzed", len(all_bidders_data))
        try:
            from src.risk.risk_analyzer import analyze_risks
            risks_detected = len(analyze_risks(tender_fields)) if tender_fields else 0
        except Exception:
            risks_detected = 0
        scol3.metric("Tender Clause Risks Detected", risks_detected)


# ============================================================
# MODULE 2: TENDER OVERVIEW
# ============================================================
elif page == "Tender Overview":
    st.header("📑 Common Tender Specification & Requirements")
    st.caption("Extracted contractual and technical requirements from the baseline tender document.")

    if tender_data is None:
        st.info("Upload the Tender document and click **Analyze Documents**.")
    else:
        fields = tender_data.get("tender_fields", {})

        col1, col2, col3 = st.columns(3)
        col1.metric("Tender Number", get_field_value(fields, "tender_number"))
        col2.metric("EMD Requirement", get_field_value(fields, "emd"))
        col3.metric("Performance Security", get_field_value(fields, "performance_security"))

        col4, col5, col6 = st.columns(3)
        col4.metric("Completion Period", get_field_value(fields, "completion_period"))
        col5.metric("Proposal Validity", get_field_value(fields, "proposal_validity"))
        ld_val = fields.get("liquidated_damages", {})
        ld_display = f"{ld_val.get('rate', '0.5%')}/wk (Max {ld_val.get('maximum', '10%')})" if isinstance(ld_val, dict) else str(ld_val)
        col6.metric("Liquidated Damages", ld_display)

        st.divider()
        st.subheader("1. Extracted Structured Tender Fields")
        st.caption("All extracted requirements link directly to their source page and verbatim evidence.")
        display_field_table(fields)

        st.divider()
        st.subheader("2. Detected Document Sections")
        sections = tender_data.get("sections", [])
        if sections:
            sec_rows = []
            for s in sections:
                sec_rows.append({
                    "Section Number": str(s.get("section_number", "")),
                    "Section Title": str(s.get("section_title", "")),
                    "Start Page": f"Page {s.get('start_page', '-')}",
                    "Character Count": str(len(s.get("text", "")))
                })
            render_table(sec_rows, use_container_width=True)
        else:
            st.info("No numbered sections detected.")

        st.divider()
        st.subheader("3. Document Page Inspection")
        pages = tender_data.get("pages", [])
        if pages:
            page_numbers = [p.get("page_number") for p in pages]
            selected_page_num = st.selectbox("Select Page to Inspect:", page_numbers)
            selected_page = next((p for p in pages if p.get("page_number") == selected_page_num), None)
            if selected_page:
                pinfo1, pinfo2, pinfo3 = st.columns(3)
                pinfo1.caption(f"Extraction Method: **{selected_page.get('extraction_method', 'direct').upper()}**")
                pinfo2.caption(f"OCR Used: **{selected_page.get('ocr_used', False)}**")
                pinfo3.caption(f"Characters: **{selected_page.get('character_count', 0)}**")
                with st.expander("Cleaned Page Text", expanded=True):
                    st.text(selected_page.get("cleaned_text", ""))


# ============================================================
# MODULE 3: BOQ ANALYSIS
# ============================================================
elif page == "BOQ Analysis":
    st.header("📊 Bill of Quantities (BOQ) Validation & Audit")
    st.caption("Deterministic arithmetic auditing (Quantity × Rate = Amount), missing values, and duplicate line-item detection.")

    tab1, tab2, tab3 = st.tabs(["Tender Baseline BOQ", "Bidder BOQs", "BOQ Summary & Audit"])

    with tab1:
        st.subheader("Tender Bill of Quantities")
        if tender_boq_data:
            render_table(tender_boq_data, use_container_width=True)
        else:
            st.info("Tender BOQ data not available. Upload tender BOQ and run analysis.")

    with tab2:
        st.subheader("Bidder BOQ Submissions")
        if not all_bidders_data:
            st.info("No bidder submissions loaded.")
        else:
            bidder_options = list(all_bidders_data.keys())
            selected_bidder_id = st.selectbox(
                "Select Bidder:",
                bidder_options,
                format_func=lambda b_id: all_bidders_data[b_id].get("bidder_name", b_id)
            )

            active_bidder_data = all_bidders_data.get(selected_bidder_id, {})
            active_label = active_bidder_data.get("bidder_name", selected_bidder_id)

            b_boq = active_bidder_data.get("boq_validation", [])
            b_issue_count = count_boq_issues(b_boq)

            bcol1, bcol2 = st.columns(2)
            bcol1.metric("Total Items Extracted", len(b_boq))
            bcol2.metric("Items With Validation Issues", b_issue_count)

            if b_issue_count > 0:
                st.warning(f"⚠️ {b_issue_count} item(s) contain calculation mismatches or missing values in {active_label}'s BOQ.")

            if b_boq:
                render_table(b_boq, use_container_width=True)
            else:
                st.info("No BOQ items extracted for this bidder.")

    with tab3:
        st.subheader("BOQ Financial Summary & Anomaly Classification")
        if not all_bidders_data:
            st.info("No bidder BOQ submissions available.")
        else:
            for b_id, b_data in all_bidders_data.items():
                name = b_data.get("bidder_name", b_id)
                with st.expander(f"📦 {name} BOQ Breakdown", expanded=True):
                    st.write(f"**Quoted Total:** {find_total_quote(b_data)}")

                    items = b_data.get("boq_validation", [])
                    issues_found = []
                    for itm in items:
                        if itm.get("issues"):
                            issues_found.append({
                                "Item No": itm.get("item_no", "-"),
                                "Description": itm.get("description", "-"),
                                "Issue": ", ".join(itm.get("issues", [])),
                                "Quoted Amount": str(itm.get("quoted_amount", "-")),
                                "Expected Amount": str(itm.get("expected_amount", "-"))
                            })

                    if issues_found:
                        st.markdown("**Detected BOQ Anomalies:**")
                        render_table(issues_found, use_container_width=True)
                    else:
                        st.success(f"All BOQ items for {name} passed arithmetic and missing-value checks.")


# ============================================================
# MODULE 4: BID COMPARISON
# ============================================================
elif page == "Bid Comparison":
    st.header("⚖️ Bidder Compliance & Comparison")
    st.caption("Side-by-side comparison of all bidder submissions against the common tender baseline.")

    if comparison_data is None:
        st.info("Upload tender and bidder documents and execute analysis to view comparison.")
    else:
        summary = comparison_data.get("summary", {})
        summary_bidders = summary.get("bidders", {})

        # Dynamic metrics across all bidders
        cols = st.columns(max(1, min(len(summary_bidders) + 1, 5)))
        cols[0].metric("Requirements Evaluated", summary.get("fields_compared", 0))

        for idx, (b_id, b_info) in enumerate(summary_bidders.items()):
            col_idx = (idx % (len(cols) - 1)) + 1
            cols[col_idx].metric(f"{b_info['name']} Compliant", f"{b_info['compliant']} / {b_info['total']}")

        st.divider()
        st.subheader("1. Detailed Requirement Compliance Matrix")

        field_comparisons = comparison_data.get("field_comparisons", [])
        if field_comparisons:
            comp_rows = []
            for item in field_comparisons:
                field_label = str(item.get("field", "")).replace("_", " ").title()
                row = {
                    "Requirement": field_label,
                    "Tender Baseline": str(item.get("tender_requirement", "-"))
                }

                # Populate columns for all evaluated bidders
                bidders_dict = item.get("bidders", {})
                if bidders_dict:
                    for b_id, b_resp in bidders_dict.items():
                        b_name = summary_bidders.get(b_id, {}).get("name", b_id)
                        row[f"{b_name} Value"] = str(b_resp.get("value", "-"))
                        row[f"{b_name} Status"] = str(b_resp.get("status", "-"))
                else:
                    # Fallback for legacy 2-bidder keys
                    row["Bidder A Value"] = str(item.get("bidder_a_value", "-"))
                    row["Bidder A Status"] = str(item.get("bidder_a_status", "-"))
                    row["Bidder B Value"] = str(item.get("bidder_b_value", "-"))
                    row["Bidder B Status"] = str(item.get("bidder_b_status", "-"))

                comp_rows.append(row)

            render_table(comp_rows, use_container_width=True)

        st.divider()
        st.subheader("2. Technical, Financial & BOQ Snapshot Across Bidders")

        criteria_list = [
            ("Technical Score", "technical_score"),
            ("Completion Period", "completion_period"),
            ("EMD Submitted", "emd_submitted"),
            ("Performance Security", "performance_security")
        ]

        snapshot_rows = []
        for crit_label, crit_key in criteria_list:
            row = {"Criterion": crit_label}
            for b_id, b_data in all_bidders_data.items():
                name = b_data.get("bidder_name", b_id)
                fields = b_data.get("bidder_fields", {})
                row[name] = get_field_value(fields, crit_key)
            snapshot_rows.append(row)

        # Add Quoted Amount row
        quote_row = {"Criterion": "Total Quoted Bid Amount"}
        for b_id, b_data in all_bidders_data.items():
            name = b_data.get("bidder_name", b_id)
            quote_row[name] = find_total_quote(b_data)
        snapshot_rows.append(quote_row)

        # Add BOQ Issues row
        boq_row = {"Criterion": "BOQ Line Items With Issues"}
        for b_id, b_data in all_bidders_data.items():
            name = b_data.get("bidder_name", b_id)
            boq_row[name] = str(count_boq_issues(b_data.get("boq_validation", [])))
        snapshot_rows.append(boq_row)

        render_table(snapshot_rows, use_container_width=True)

        st.divider()
        st.subheader("3. Substantive Differences & Operational Impact")
        differences = comparison_data.get("differences", [])
        if differences:
            for diff in differences:
                field_title = str(diff.get("field", "Difference")).replace("_", " ").title()
                with st.expander(f"📌 Difference in {field_title}"):
                    st.markdown(f"**Impact Category:** `{diff.get('impact', 'General')}`")
                    st.write(diff.get("message", ""))
        else:
            st.success("No critical differences detected among bidder commitments.")


# ============================================================
# MODULE 5: BIDDER RANKING & RECOMMENDATION
# ============================================================
elif page == "Bidder Ranking":
    st.header("🏅 Dynamic Multi-Bidder Ranking & Recommendation")
    st.caption("Multi-bidder ranking based on mandatory qualification, technical scoring, financial quotation, and risk.")

    st.info(
        "💡 **Evaluation Principle**: Mandatory qualification rules are checked before active ranking. "
        "Disqualified bidders are retained for transparent audit reporting but are excluded from active rank positions."
    )

    if comparison_data is None and ranking_data is None:
        st.info("Run the document analysis pipeline first to calculate rankings.")
    else:
        # Check if structured ranking_data from BidderRanker is available
        if ranking_data and "ranking_table" in ranking_data:
            eval_params = ranking_data.get("evaluation_parameters", {})
            tech_pct = eval_params.get("technical_weight_percent", "80%")
            fin_pct = eval_params.get("financial_weight_percent", "20%")
            min_score = eval_params.get("min_technical_score", 70.0)
            l1_val = eval_params.get("lowest_qualified_bid_l1")

            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
            mcol1.metric("Technical Weight", tech_pct)
            mcol2.metric("Financial Weight", fin_pct)
            mcol3.metric("Min Technical Cutoff", f"{min_score} marks")
            mcol4.metric("Benchmark L1 Quote", f"INR {l1_val:,.0f}" if l1_val else "N/A")

            st.divider()

            # Active Tabbed Display
            rtab1, rtab2, rtab3 = st.tabs(["📋 Evaluation & Ranking Table", "🔄 Fallback Recalculation", "📜 Recommendation Audit Trail"])

            with rtab1:
                st.subheader("1. Comprehensive Bidder Ranking Table")
                st.caption("Qualified bidders ranked descending by Overall Score. Disqualified bidders listed separately below.")

                ranking_table = ranking_data.get("ranking_table", [])
                render_table(ranking_table, use_container_width=True)

                st.divider()
                st.subheader("2. Formal Decision-Support Recommendation")

                recom_card, fallback_card = st.columns(2)
                with recom_card:
                    rec_bidder = ranking_data.get("recommended_bidder", "Pending")
                    st.success(f"### 🏆 Recommended: {rec_bidder}")
                    st.markdown("**Status:** `Rank 1 — RECOMMENDED`")
                    st.write(ranking_data.get("recommendation_statement", "Recommended based on tender compliance and highest overall score."))
                    st.caption("Basis: Qualified on all mandatory clauses; highest combined technical and financial score.")

                with fallback_card:
                    next_eligible = ranking_data.get("next_eligible_bidder", "None")
                    st.info(f"### 🥈 Next Eligible (Reserve): {next_eligible}")
                    st.markdown("**Status:** `Rank 2 — RESERVE / FALLBACK`")
                    st.write(ranking_data.get("next_eligible_statement", "Designated as backup candidate."))
                    st.caption("Protocol: Automatically promoted if Rank 1 fails due diligence or withdraws.")

            with rtab2:
                st.subheader("Interactive Fallback Simulator")
                st.caption("Simulate post-qualification disqualification or voluntary withdrawal of any active bidder.")

                qualified_names = {b["bidder_id"]: b["bidder_name"] for b in ranking_data.get("qualified_bidders", [])}
                if not qualified_names:
                    st.warning("No qualified bidders available for fallback simulation.")
                else:
                    selected_sim_id = st.selectbox(
                        "Select Bidder to Disqualify / Withdraw:",
                        list(qualified_names.keys()),
                        format_func=lambda x: qualified_names.get(x, x)
                    )
                    sim_reason = st.text_input(
                        "Disqualification / Withdrawal Reason:",
                        value="Failed post-qualification verification / voluntary withdrawal"
                    )

                    if st.button("⚡ Recalculate Ranking with Fallback", type="primary"):
                        from src.comparison.bidder_ranker import BidderRanker
                        sim_ranker = BidderRanker()
                        updated_ranking = sim_ranker.simulate_fallback(
                            ranking_result=ranking_data,
                            disqualified_bidder_id=selected_sim_id,
                            disqualification_reason=sim_reason
                        )
                        st.session_state["simulated_ranking"] = updated_ranking
                        st.success(f"Recalculation complete! {updated_ranking.get('recommended_bidder')} is now Recommended Rank 1.")

                    if "simulated_ranking" in st.session_state:
                        sim_res = st.session_state["simulated_ranking"]
                        st.markdown("#### Updated Recalculated Ranking Table:")
                        render_table(sim_res.get("ranking_table", []), use_container_width=True)
                        st.info(f"**Updated Recommendation:** {sim_res.get('recommendation_statement')}")

            with rtab3:
                st.subheader("Immutable Recommendation Audit Trail")
                st.caption("Chronological event log tracking all ranking calculations, baseline parameters, and fallback triggers.")
                active_trail = st.session_state.get("simulated_ranking", {}).get("audit_trail") or ranking_data.get("audit_trail", [])
                render_table(active_trail, use_container_width=True)

        else:
            # Fallback legacy view if ranking_data not yet populated
            rec_details = comparison_data.get("recommendation_details", {}) if comparison_data else {}
            summary_bidders = comparison_data.get("summary", {}).get("bidders", {}) if comparison_data else {}

            rankings = []
            excluded = []

            bidders_dict = rec_details.get("bidders", {})
            if not bidders_dict and summary_bidders:
                bidders_dict = summary_bidders

            qualified_list = []
            non_compliant_list = []

            for b_id, b_info in bidders_dict.items():
                name = b_info.get("name", b_id)
                b_data = all_bidders_data.get(b_id, {})
                fields = b_data.get("bidder_fields", {})

                tech_score = float(get_field_value(fields, "technical_score", "75.0"))
                quoted_amt = find_total_quote(b_data)
                boq_issues = count_boq_issues(b_data.get("boq_validation", []))

                non_comp = b_info.get("non_compliant_requirements", b_info.get("non_compliant", 0))

                entry = {
                    "bidder_id": b_id,
                    "name": name,
                    "technical_score": tech_score,
                    "quoted_amount": quoted_amt,
                    "boq_issues": boq_issues,
                    "non_compliant_count": non_comp,
                    "failures": b_info.get("non_compliance_details", [])
                }

                if non_comp == 0:
                    qualified_list.append(entry)
                else:
                    non_compliant_list.append(entry)

            qualified_list.sort(key=lambda x: x["technical_score"], reverse=True)

            for idx, q_b in enumerate(qualified_list, start=1):
                status_label = "RECOMMENDED" if idx == 1 else ("NEXT ELIGIBLE / RESERVE" if idx == 2 else "ELIGIBLE")
                rankings.append({
                    "Rank": str(idx),
                    "Bidder Name": q_b["name"],
                    "Qualification": "QUALIFIED",
                    "Technical Score": f"{q_b['technical_score']:.1f}",
                    "Financial Quote": q_b["quoted_amount"],
                    "Compliance": "Compliant",
                    "BOQ Issues": str(q_b["boq_issues"]),
                    "Risk Level": "LOW" if q_b["boq_issues"] == 0 else "MEDIUM",
                    "Overall Score": f"{q_b['technical_score']:.2f}",
                    "Status": status_label
                })

            for nc_b in non_compliant_list:
                failure_msgs = [f"{f.get('field')}: {f.get('bidder_value')} (Tender requires: {f.get('requirement')})" for f in nc_b["failures"]]
                reason_str = "; ".join(failure_msgs) if failure_msgs else "Failed mandatory tender compliance requirements."
                excluded.append({
                    "Bidder Name": nc_b["name"],
                    "Status": "NON-COMPLIANT / DISQUALIFIED",
                    "Reason": reason_str,
                    "Technical Score": f"{nc_b['technical_score']:.1f}",
                    "Quoted Amount": nc_b["quoted_amount"]
                })

            st.subheader("1. Active Eligible Bidder Rankings")
            if rankings:
                render_table(rankings, use_container_width=True)
            else:
                st.warning("No bidders currently satisfy all mandatory eligibility criteria.")

            if excluded:
                st.divider()
                st.subheader("2. Disqualified / Excluded Bidders (Audit Trail)")
                render_table(excluded, use_container_width=True)

            st.divider()
            st.subheader("3. Formal Recommendation & Fallback Reserve Protocol")

            recom_card, fallback_card = st.columns(2)
            with recom_card:
                rec_bidder = comparison_data.get("recommended_bidder", "Pending") if comparison_data else "Pending"
                st.success(f"### 🏆 Recommended Bidder: {rec_bidder}")
                st.markdown(f"**Current Status:** `Rank 1 — RECOMMENDED`")
                st.write(comparison_data.get("recommendation", "Highest-ranked qualified bidder based on tender compliance evaluation.") if comparison_data else "")
                st.caption("Basis: Fully satisfies tender technical, schedule, and security requirements.")

            with fallback_card:
                next_eligible = comparison_data.get("next_eligible_bidder", "None") if comparison_data else "None"
                st.info(f"### 🥈 Next Eligible Alternative: {next_eligible}")
                st.markdown(f"**Current Status:** `RESERVE / FALLBACK`")
                st.write(
                    "In the event Rank 1 is disqualified during final document verification, withdraws, or fails to execute "
                    "the performance security within 21 days, the committee may automatically recalculate active ranking "
                    "to evaluate the next eligible bidder."
                )

        st.caption("Note: All recommendations are provisional decision-support outputs. Human procurement authorities retain final contract award authority.")


# ============================================================
# MODULE 6: RISK ANALYSIS
# ============================================================
elif page == "Risk Analysis":
    st.header("⚠️ Tender & Bid Risk Analysis")
    st.caption("Evidence-grounded risk detection covering contractual clauses, BOQ calculations, and bidder deviations.")

    if tender_data is None:
        st.info("Upload tender documents and run analysis first.")
    else:
        st.subheader("1. Tender Contractual & Financial Risks")
        try:
            from src.risk.risk_analyzer import analyze_risks
            tender_fields = tender_data.get("tender_fields", {})
            try:
                tender_risks = analyze_risks(tender_fields)
            except TypeError:
                tender_risks = analyze_risks(tender_data)
            tender_risks = tender_risks or []

            high = sum(str(r.get("severity", "")).upper() == "HIGH" for r in tender_risks)
            medium = sum(str(r.get("severity", "")).upper() == "MEDIUM" for r in tender_risks)
            low = sum(str(r.get("severity", "")).upper() == "LOW" for r in tender_risks)

            r1, r2, r3 = st.columns(3)
            r1.metric("🔴 High Severity Risks", high)
            r2.metric("🟠 Medium Severity Risks", medium)
            r3.metric("🟢 Low Severity Risks", low)

            if not tender_risks:
                st.success("No high-risk tender clauses detected.")
            else:
                for r in tender_risks:
                    sev = str(r.get("severity", "MEDIUM")).upper()
                    icon = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟢"}.get(sev, "⚪")
                    risk_type = r.get("risk_type", r.get("category", "Tender Risk"))
                    desc = r.get("description", "Potential risk detected.")
                    page_ref = r.get("page")

                    with st.expander(f"{icon} {sev} — {risk_type}"):
                        st.write(desc)
                        if page_ref:
                            st.caption(f"Tender Clause Evidence: Page {page_ref}")
        except Exception as e:
            st.warning("Tender risk analyzer module encountered an issue.")
            st.caption(str(e))

        st.divider()
        st.subheader("2. Bidder BOQ Arithmetic & Data Risks")
        if not all_bidders_data:
            st.info("No bidder submissions loaded.")
        else:
            for b_id, b_data in all_bidders_data.items():
                name = b_data.get("bidder_name", b_id)
                items = b_data.get("boq_validation", [])
                issue_cnt = count_boq_issues(items)

                with st.expander(f"📦 {name} — BOQ Issues ({issue_cnt})", expanded=(issue_cnt > 0)):
                    if issue_cnt == 0:
                        st.success("No arithmetic errors or missing values detected.")
                    else:
                        for itm in items:
                            if itm.get("issues"):
                                st.warning(f"Item {itm.get('item_no')}: {itm.get('description')}")
                                st.write("Issues:", ", ".join(itm.get("issues", [])))

        st.divider()
        st.subheader("3. Bidder Compliance & Deviation Risks")
        if comparison_data:
            noncomp_found = False
            field_comparisons = comparison_data.get("field_comparisons", [])
            for item in field_comparisons:
                field_name = str(item.get("field", "Requirement")).replace("_", " ").title()
                req = item.get("tender_requirement", "")
                bidders_dict = item.get("bidders", {})

                for b_id, b_resp in bidders_dict.items():
                    name = all_bidders_data.get(b_id, {}).get("bidder_name", b_id)
                    st_val = str(b_resp.get("status", "")).upper()
                    if "NON" in st_val:
                        noncomp_found = True
                        st.error(f"**{name} Deviation** on `{field_name}`: Proposes '{b_resp.get('value')}'; Tender requires '{req}'.")

            if not noncomp_found:
                st.success("No bidder compliance deviations found in currently evaluated fields.")
        else:
            st.info("Run comparison to review compliance deviation risks.")


# ============================================================
# MODULE 7: RAG ASSISTANT
# ============================================================
elif page == "RAG Assistant":
    st.header("🤖 Evidence-Grounded Tender RAG Assistant")
    st.caption("Ask questions about tender clauses. The assistant retrieves relevant clauses from ChromaDB before generating answers with Ollama.")

    if tender_data is None:
        st.info("Upload tender documents and run analysis before querying the RAG Assistant.")
    else:
        st.subheader("Suggested Questions")
        example_queries = [
            "What is the proposal validity period?",
            "What is the Earnest Money Deposit (EMD) amount?",
            "What performance security must the successful bidder provide?",
            "What is the project completion period?",
            "What are the liquidated damages for delayed work?",
            "What are the minimum eligibility criteria?"
        ]

        preset_cols = st.columns(2)
        for i, query in enumerate(example_queries):
            target_col = preset_cols[i % 2]
            if target_col.button(f"👉 {query}", key=f"ex_{i}", use_container_width=True):
                st.session_state["active_rag_q"] = query

        default_query = st.session_state.get("active_rag_q", "")
        question = st.text_area(
            "Enter your question regarding the tender:",
            value=default_query,
            placeholder="Example: What is the proposal validity period?",
            height=90,
            key="rag_input"
        )

        if st.button("🔎 Ask Assistant", type="primary", key="rag_search_btn"):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                try:
                    from src.rag.rag_pipeline import answer_question

                    with st.spinner("Retrieving tender evidence and generating grounded response..."):
                        result = answer_question(question=question, tender_id="tender_001", top_k=3)

                    st.divider()
                    st.subheader("💬 Evidence-Grounded Answer")

                    if isinstance(result, dict):
                        answer_text = result.get("answer", "No answer generated.")
                        st.success(answer_text)

                        sources = result.get("sources", [])
                        if sources:
                            st.subheader("📚 Retrieved Tender Evidence")
                            for s in sources:
                                rank = s.get("rank", 1)
                                sec_num = s.get("section_number", "INTRO")
                                sec_title = s.get("section_title", "Tender Information")
                                pg_num = s.get("page_number", "-")
                                dist = s.get("distance")

                                dist_str = f" | Vector Distance: {float(dist):.4f}" if dist is not None else ""
                                exp_title = f"Source {rank} — Section {sec_num}: {sec_title} (Page {pg_num}){dist_str}"

                                with st.expander(exp_title):
                                    st.markdown(f"**Section:** {sec_num} — {sec_title}")
                                    st.markdown(f"**Source Document Page:** {pg_num}")
                                    st.markdown("**Verbatim Clause Context:**")
                                    st.write(s.get("text", ""))
                        else:
                            st.info("No source chunks were retrieved.")
                    else:
                        st.write(result)

                except Exception as e:
                    st.error("RAG Assistant retrieval failed.")
                    st.exception(e)
