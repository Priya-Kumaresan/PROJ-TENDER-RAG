import json

import subprocess

import sys

from pathlib import Path



import streamlit as st





# ============================================================

# CONFIGURATION

# ============================================================



RAW_FOLDER = Path("data/raw/tender_001")

PROCESSED_FOLDER = Path("data/processed/tender_001")



TENDER_FOLDER = RAW_FOLDER / "tender"

BIDDER_A_FOLDER = RAW_FOLDER / "bidder_A"

BIDDER_B_FOLDER = RAW_FOLDER / "bidder_B"



TENDER_FOLDER.mkdir(parents=True, exist_ok=True)

BIDDER_A_FOLDER.mkdir(parents=True, exist_ok=True)

BIDDER_B_FOLDER.mkdir(parents=True, exist_ok=True)





# ============================================================

# PAGE CONFIGURATION

# ============================================================



st.set_page_config(

    page_title="Tender & Bid Analysis",

    page_icon="📑",

    layout="wide"

)



st.title("📑 LLM-Based Tender & Bid Analysis")



st.write(

    "AI-assisted analysis of tender requirements, BOQ data, "

    "bidder submissions, risks, RAG-based question answering, "

    "and bid comparison."

)





# ============================================================

# HELPER FUNCTIONS

# ============================================================



def save_uploaded_file(uploaded_file, destination_folder):



    if uploaded_file is None:

        return None



    destination_folder.mkdir(

        parents=True,

        exist_ok=True

    )



    destination = (

        destination_folder

        / uploaded_file.name

    )



    with open(destination, "wb") as file:

        file.write(uploaded_file.getbuffer())



    return destination





def load_json(path):



    if not path.exists():

        return None



    try:



        with open(

            path,

            "r",

            encoding="utf-8"

        ) as file:



            return json.load(file)



    except Exception:

        return None





def get_field_value(fields, field_name):



    information = fields.get(field_name)



    if isinstance(information, dict):

        return information.get(

            "value",

            "Not available"

        )



    if information is None:

        return "Not available"



    return information





def get_field_page(fields, field_name):



    information = fields.get(field_name)



    if isinstance(information, dict):

        return information.get("page", "")



    return ""





def display_field_table(fields):



    rows = []



    for field, information in fields.items():



        if isinstance(information, dict):



            value = information.get(

                "value",

                ""

            )



            page = information.get(

                "page",

                ""

            )



        else:



            value = information

            page = ""



        rows.append({

            "Field": field,

            "Value": value,

            "Page": page

        })



    if rows:



        st.dataframe(

            rows,

            width="stretch"

        )



    else:



        st.info(

            "No extracted fields available."

        )





def count_boq_issues(boq_items):



    count = 0



    for item in boq_items:



        status = str(

            item.get("status", "")

        ).upper()



        issues = item.get(

            "issues",

            []

        )



        if status == "ISSUE" or issues:

            count += 1



    return count





def find_total_quote(bidder_data):



    if not bidder_data:

        return "Not available"



    fields = bidder_data.get(

        "bidder_fields",

        {}

    )



    for key in [

        "total_quoted_amount",

        "quoted_amount",

        "total_bid_amount",

        "bid_amount"

    ]:



        if key in fields:



            value = fields[key]



            if isinstance(value, dict):

                return value.get(

                    "value",

                    "Not available"

                )



            return value



    return "Not available"





# ============================================================

# SIDEBAR — DOCUMENT UPLOAD

# ============================================================



st.sidebar.title("📂 Document Upload")





# ------------------------------------------------------------

# TENDER

# ------------------------------------------------------------



st.sidebar.subheader("1. Common Tender")



tender_pdf = st.sidebar.file_uploader(

    "Tender Document PDF",

    type=["pdf"],

    key="tender_pdf"

)



tender_boq = st.sidebar.file_uploader(

    "Tender BOQ / Price Schedule",

    type=["xlsx", "xls"],

    key="tender_boq"

)





# ------------------------------------------------------------

# BIDDER A

# ------------------------------------------------------------



st.sidebar.subheader("2. Bidder A")



bidder_a_name = st.sidebar.text_input(

    "Bidder A Name",

    value="Bidder A"

)



bidder_a_technical = st.sidebar.file_uploader(

    "Bidder A Technical Bid",

    type=["pdf"],

    key="bidder_a_technical"

)



bidder_a_financial = st.sidebar.file_uploader(

    "Bidder A Financial Bid",

    type=["pdf"],

    key="bidder_a_financial"

)



bidder_a_boq = st.sidebar.file_uploader(

    "Bidder A BOQ",

    type=["xlsx", "xls"],

    key="bidder_a_boq"

)





# ------------------------------------------------------------

# BIDDER B

# ------------------------------------------------------------



st.sidebar.subheader("3. Bidder B")



bidder_b_name = st.sidebar.text_input(

    "Bidder B Name",

    value="Bidder B"

)



bidder_b_technical = st.sidebar.file_uploader(

    "Bidder B Technical Bid",

    type=["pdf"],

    key="bidder_b_technical"

)



bidder_b_financial = st.sidebar.file_uploader(

    "Bidder B Financial Bid",

    type=["pdf"],

    key="bidder_b_financial"

)



bidder_b_boq = st.sidebar.file_uploader(

    "Bidder B BOQ",

    type=["xlsx", "xls"],

    key="bidder_b_boq"

)





# ============================================================

# ANALYZE BUTTON

# ============================================================



analyze_button = st.sidebar.button(

    "🔍 Analyze Documents",

    width="stretch"

)





# ============================================================

# PROCESS UPLOADS

# ============================================================



if analyze_button:



    missing_files = []



    if tender_pdf is None:

        missing_files.append(

            "Tender Document PDF"

        )



    if tender_boq is None:

        missing_files.append(

            "Tender BOQ"

        )



    if bidder_a_technical is None:

        missing_files.append(

            "Bidder A Technical Bid"

        )



    if bidder_a_financial is None:

        missing_files.append(

            "Bidder A Financial Bid"

        )



    if bidder_a_boq is None:

        missing_files.append(

            "Bidder A BOQ"

        )



    if bidder_b_technical is None:

        missing_files.append(

            "Bidder B Technical Bid"

        )



    if bidder_b_financial is None:

        missing_files.append(

            "Bidder B Financial Bid"

        )



    if bidder_b_boq is None:

        missing_files.append(

            "Bidder B BOQ"

        )



    if missing_files:



        st.sidebar.error(

            "Please upload all required documents."

        )



        for item in missing_files:

            st.sidebar.write(

                f"- {item}"

            )



    else:



        # ----------------------------------------------------

        # Remove old uploaded files

        # ----------------------------------------------------



        for folder in [

            TENDER_FOLDER,

            BIDDER_A_FOLDER,

            BIDDER_B_FOLDER

        ]:



            for old_file in folder.iterdir():



                if old_file.is_file():

                    old_file.unlink()



        # ----------------------------------------------------

        # Save Tender

        # ----------------------------------------------------



        save_uploaded_file(

            tender_pdf,

            TENDER_FOLDER

        )



        save_uploaded_file(

            tender_boq,

            TENDER_FOLDER

        )



        # ----------------------------------------------------

        # Save Bidder A

        # ----------------------------------------------------



        save_uploaded_file(

            bidder_a_technical,

            BIDDER_A_FOLDER

        )



        save_uploaded_file(

            bidder_a_financial,

            BIDDER_A_FOLDER

        )



        save_uploaded_file(

            bidder_a_boq,

            BIDDER_A_FOLDER

        )



        # ----------------------------------------------------

        # Save Bidder B

        # ----------------------------------------------------



        save_uploaded_file(

            bidder_b_technical,

            BIDDER_B_FOLDER

        )



        save_uploaded_file(

            bidder_b_financial,

            BIDDER_B_FOLDER

        )



        save_uploaded_file(

            bidder_b_boq,

            BIDDER_B_FOLDER

        )



        # ----------------------------------------------------

        # Save bidder names

        # ----------------------------------------------------



        names_file = (

            RAW_FOLDER

            / "bidder_names.json"

        )



        with open(

            names_file,

            "w",

            encoding="utf-8"

        ) as file:



            json.dump(

                {

                    "bidder_A": bidder_a_name,

                    "bidder_B": bidder_b_name

                },

                file,

                indent=4

            )



        # ----------------------------------------------------

        # Run backend

        # ----------------------------------------------------



        with st.spinner(

            "Analyzing tender and bidder documents..."

        ):



            result = subprocess.run(

                [

                    sys.executable,

                    "main.py"

                ],

                capture_output=True,

                text=True,

                encoding="utf-8",

                errors="replace"

            )



        if result.returncode == 0:



            st.success(

                "Tender and bidder analysis completed successfully."

            )



            st.session_state[

                "processing_output"

            ] = result.stdout



            st.rerun()



        else:



            st.error(

                "Document processing failed."

            )



            st.subheader(

                "Backend Error"

            )



            st.code(

                result.stderr

            )





# ============================================================

# NAVIGATION

# ============================================================



st.sidebar.divider()



st.sidebar.title("Navigation")



page = st.sidebar.radio(

    "Select Module",

    [

        "Tender Overview",

        "Bidder A Analysis",

        "Bidder B Analysis",

        "BOQ Analysis",

        "Bid Comparison",

        "RAG Assistant",

        "Risk Analysis"

    ]

)

# ============================================================

# LOAD PROCESSED FILES

# ============================================================



tender_file = (

    PROCESSED_FOLDER

    / "tender.json"

)



bidder_a_file = (

    PROCESSED_FOLDER

    / "bidder_A.json"

)



bidder_b_file = (

    PROCESSED_FOLDER

    / "bidder_B.json"

)



comparison_file = (

    PROCESSED_FOLDER

    / "bid_comparison.json"

)



tender_boq_file = (

    PROCESSED_FOLDER

    / "tender_boq.json"

)





tender_data = load_json(

    tender_file

)



bidder_a_data = load_json(

    bidder_a_file

)



bidder_b_data = load_json(

    bidder_b_file

)



comparison_data = load_json(

    comparison_file

)



tender_boq_data = load_json(

    tender_boq_file

)





# ============================================================

# TENDER OVERVIEW

# ============================================================



if page == "Tender Overview":



    st.header(

        "📑 Tender Overview"

    )



    if tender_data is None:



        st.info(

            "Upload the Tender, Bidder A and Bidder B "

            "documents and click 'Analyze Documents'."

        )



    else:



        fields = tender_data.get(

            "tender_fields",

            {}

        )



        col1, col2 = st.columns(2)



        with col1:



            st.metric(

                "Tender Number",

                get_field_value(

                    fields,

                    "tender_number"

                )

            )



            st.write(

                "**Organisation:**",

                get_field_value(

                    fields,

                    "organisation"

                )

            )



            st.write(

                "**Project:**",

                get_field_value(

                    fields,

                    "project_name"

                )

            )



        with col2:



            st.metric(

                "EMD",

                get_field_value(

                    fields,

                    "emd"

                )

            )



            st.write(

                "**Completion Period:**",

                get_field_value(

                    fields,

                    "completion_period"

                )

            )



            st.write(

                "**Performance Security:**",

                get_field_value(

                    fields,

                    "performance_security"

                )

            )



        st.divider()



        st.subheader(

            "Extracted Tender Fields"

        )



        display_field_table(fields)



        st.subheader(

            "Document Summary"

        )



        col1, col2 = st.columns(2)



        with col1:



            st.metric(

                "Total Pages",

                tender_data.get(

                    "total_pages",

                    "N/A"

                )

            )



        with col2:



            st.metric(

                "Sections Detected",

                len(

                    tender_data.get(

                        "sections",

                        []

                    )

                )

            )





# ============================================================

# BIDDER A ANALYSIS

# ============================================================



elif page == "Bidder A Analysis":



    st.header(

        "👤 Bidder A Analysis"

    )



    if bidder_a_data is None:



        st.info(

            "Upload Bidder A documents and "

            "analyze the documents first."

        )



    else:



        name = bidder_a_data.get(

            "bidder_name",

            "Bidder A"

        )



        st.subheader(name)



        fields = bidder_a_data.get(

            "bidder_fields",

            {}

        )



        col1, col2, col3 = st.columns(3)



        col1.metric(

            "Completion Period",

            get_field_value(

                fields,

                "completion_period"

            )

        )



        col2.metric(

            "Technical Score",

            get_field_value(

                fields,

                "technical_score"

            )

        )



        col3.metric(

            "Quoted Amount",

            find_total_quote(

                bidder_a_data

            )

        )



        st.subheader(

            "Extracted Bidder Fields"

        )



        display_field_table(fields)



        st.subheader(

            "Bidder A BOQ Validation"

        )



        boq_items = bidder_a_data.get(

            "boq_validation",

            []

        )



        if boq_items:



            issue_count = count_boq_issues(

                boq_items

            )



            st.metric(

                "BOQ Items With Issues",

                issue_count

            )



            st.dataframe(

                boq_items,

                width="stretch"

            )



        else:



            st.info(

                "No bidder BOQ validation data available."

            )





# ============================================================

# BIDDER B ANALYSIS

# ============================================================



elif page == "Bidder B Analysis":



    st.header(

        "👤 Bidder B Analysis"

    )



    if bidder_b_data is None:



        st.info(

            "Upload Bidder B documents and "

            "analyze the documents first."

        )



    else:



        name = bidder_b_data.get(

            "bidder_name",

            "Bidder B"

        )



        st.subheader(name)



        fields = bidder_b_data.get(

            "bidder_fields",

            {}

        )



        col1, col2, col3 = st.columns(3)



        col1.metric(

            "Completion Period",

            get_field_value(

                fields,

                "completion_period"

            )

        )



        col2.metric(

            "Technical Score",

            get_field_value(

                fields,

                "technical_score"

            )

        )



        col3.metric(

            "Quoted Amount",

            find_total_quote(

                bidder_b_data

            )

        )



        st.subheader(

            "Extracted Bidder Fields"

        )



        display_field_table(fields)



        st.subheader(

            "Bidder B BOQ Validation"

        )



        boq_items = bidder_b_data.get(

            "boq_validation",

            []

        )



        if boq_items:



            issue_count = count_boq_issues(

                boq_items

            )



            st.metric(

                "BOQ Items With Issues",

                issue_count

            )



            st.dataframe(

                boq_items,

                width="stretch"

            )



        else:



            st.info(

                "No bidder BOQ validation data available."

            )





# ============================================================

# BOQ ANALYSIS

# ============================================================



elif page == "BOQ Analysis":



    st.header(

        "📊 BOQ Analysis"

    )



    if tender_boq_data is None:



        st.info(

            "Upload and analyze the tender BOQ first."

        )



    else:



        st.subheader(

            "Tender BOQ"

        )



        st.dataframe(

            tender_boq_data,

            width="stretch"

        )



        st.divider()



        col1, col2 = st.columns(2)



        with col1:



            st.subheader(

                "Bidder A BOQ"

            )



            if bidder_a_data:



                bidder_a_boq_items = (

                    bidder_a_data.get(

                        "boq_validation",

                        []

                    )

                )



                st.metric(

                    "Items With Issues",

                    count_boq_issues(

                        bidder_a_boq_items

                    )

                )



                st.dataframe(

                    bidder_a_boq_items,

                    width="stretch"

                )



            else:



                st.info(

                    "No Bidder A BOQ data."

                )



        with col2:



            st.subheader(

                "Bidder B BOQ"

            )



            if bidder_b_data:



                bidder_b_boq_items = (

                    bidder_b_data.get(

                        "boq_validation",

                        []

                    )

                )



                st.metric(

                    "Items With Issues",

                    count_boq_issues(

                        bidder_b_boq_items

                    )

                )



                st.dataframe(

                    bidder_b_boq_items,

                    width="stretch"

                )



            else:



                st.info(

                    "No Bidder B BOQ data."

                )





# ============================================================

# BID COMPARISON

# ============================================================



elif page == "Bid Comparison":



    st.header(

        "⚖️ Bidder Comparison"

    )



    if comparison_data is None:



        st.info(

            "Upload Tender, Bidder A and Bidder B "

            "documents and run analysis first."

        )



    else:



        summary = comparison_data.get(

            "summary",

            {}

        )



        bidder_a_display_name = (

            comparison_data.get(

                "bidder_a_name",

                "Bidder A"

            )

        )



        bidder_b_display_name = (

            comparison_data.get(

                "bidder_b_name",

                "Bidder B"

            )

        )



        # ----------------------------------------------------

        # Comparison Summary

        # ----------------------------------------------------



        st.subheader(

            "Comparison Summary"

        )



        col1, col2, col3 = st.columns(3)



        col1.metric(

            "Fields Compared",

            summary.get(

                "fields_compared",

                0

            )

        )



        col2.metric(

            f"{bidder_a_display_name} Compliant",

            summary.get(

                "bidder_a_compliant",

                0

            )

        )



        col3.metric(

            f"{bidder_b_display_name} Compliant",

            summary.get(

                "bidder_b_compliant",

                0

            )

        )



        # ----------------------------------------------------

        # Tender Requirement Comparison

        # ----------------------------------------------------



        st.subheader(

            "Tender Requirement vs Bidder Responses"

        )



        comparison_rows = []



        for item in comparison_data.get(

            "field_comparisons",

            []

        ):



            comparison_rows.append({



                "Requirement":

                    item.get(

                        "field",

                        ""

                    ),



                "Tender Requirement":

                    item.get(

                        "tender_requirement",

                        ""

                    ),



                bidder_a_display_name:

                    item.get(

                        "bidder_a_value",

                        ""

                    ),



                f"{bidder_a_display_name} Status":

                    item.get(

                        "bidder_a_status",

                        ""

                    ),



                bidder_b_display_name:

                    item.get(

                        "bidder_b_value",

                        ""

                    ),



                f"{bidder_b_display_name} Status":

                    item.get(

                        "bidder_b_status",

                        ""

                    )

            })



        if comparison_rows:



            st.dataframe(

                comparison_rows,

                width="stretch"

            )



        # ----------------------------------------------------

        # Additional bidder information

        # ----------------------------------------------------



        st.subheader(

            "Technical, Financial & BOQ Snapshot"

        )



        bidder_a_fields = (

            bidder_a_data.get(

                "bidder_fields",

                {}

            )

            if bidder_a_data

            else {}

        )



        bidder_b_fields = (

            bidder_b_data.get(

                "bidder_fields",

                {}

            )

            if bidder_b_data

            else {}

        )



        bidder_a_boq = (

            bidder_a_data.get(

                "boq_validation",

                []

            )

            if bidder_a_data

            else []

        )



        bidder_b_boq = (

            bidder_b_data.get(

                "boq_validation",

                []

            )

            if bidder_b_data

            else []

        )



        snapshot = [

            {

                "Criterion": "Technical Score",

                bidder_a_display_name:

                    get_field_value(

                        bidder_a_fields,

                        "technical_score"

                    ),

                bidder_b_display_name:

                    get_field_value(

                        bidder_b_fields,

                        "technical_score"

                    )

            },

            {

                "Criterion": "Quoted Amount",

                bidder_a_display_name:

                    find_total_quote(

                        bidder_a_data

                    ),

                bidder_b_display_name:

                    find_total_quote(

                        bidder_b_data

                    )

            },

            {

                "Criterion": "Completion Period",

                bidder_a_display_name:

                    get_field_value(

                        bidder_a_fields,

                        "completion_period"

                    ),

                bidder_b_display_name:

                    get_field_value(

                        bidder_b_fields,

                        "completion_period"

                    )

            },

            {

                "Criterion": "BOQ Items With Issues",

                bidder_a_display_name:

                    count_boq_issues(

                        bidder_a_boq

                    ),

                bidder_b_display_name:

                    count_boq_issues(

                        bidder_b_boq

                    )

            }

        ]



        # Convert mixed values to strings for PyArrow compatibility.
        for row in snapshot:
            for key, value in row.items():
                if value is None:
                    row[key] = "Not available"
                else:
                    row[key] = str(value)

        st.dataframe(
            snapshot,
            width="stretch"
        )

                # ----------------------------------------------------

        # BIDDER RECOMMENDATION

        # ----------------------------------------------------



        st.subheader(

            "🏆 Bidder Recommendation"

        )



        recommended_bidder = comparison_data.get(

            "recommended_bidder"

        )



        recommendation = comparison_data.get(

            "recommendation"

        )



        recommendation_details = comparison_data.get(

            "recommendation_details",

            {}

        )



        if recommended_bidder:



            # ------------------------------------------------

            # Recommended bidder

            # ------------------------------------------------



            st.success(

                f"Recommended Bidder: {recommended_bidder}"

            )



            # ------------------------------------------------

            # Recommendation explanation

            # ------------------------------------------------



            if recommendation:



                st.write(

                    recommendation

                )



            # ------------------------------------------------

            # Recommendation basis

            # ------------------------------------------------



            recommendation_basis = (

                recommendation_details.get(

                    "recommendation_basis"

                )

            )



            if recommendation_basis:



                st.markdown(

                    f"**Recommendation Basis:** "

                    f"{recommendation_basis}"

                )



            # ------------------------------------------------

            # Compliance summary

            # ------------------------------------------------



            bidder_a_result = (

                recommendation_details.get(

                    "bidder_a",

                    {}

                )

            )



            bidder_b_result = (

                recommendation_details.get(

                    "bidder_b",

                    {}

                )

            )



            if bidder_a_result or bidder_b_result:



                st.markdown(

                    "#### Compliance Summary"

                )



                col1, col2 = st.columns(2)



                with col1:



                    bidder_a_rec_name = (

                        bidder_a_result.get(

                            "name",

                            bidder_a_display_name

                        )

                    )



                    st.markdown(

                        f"**{bidder_a_rec_name}**"

                    )



                    st.metric(

                        "Compliant Requirements",

                        bidder_a_result.get(

                            "compliant_requirements",

                            0

                        )

                    )



                    st.metric(

                        "Non-Compliant Requirements",

                        bidder_a_result.get(

                            "non_compliant_requirements",

                            0

                        )

                    )



                with col2:



                    bidder_b_rec_name = (

                        bidder_b_result.get(

                            "name",

                            bidder_b_display_name

                        )

                    )



                    st.markdown(

                        f"**{bidder_b_rec_name}**"

                    )



                    st.metric(

                        "Compliant Requirements",

                        bidder_b_result.get(

                            "compliant_requirements",

                            0

                        )

                    )



                    st.metric(

                        "Non-Compliant Requirements",

                        bidder_b_result.get(

                            "non_compliant_requirements",

                            0

                        )

                    )



            # ------------------------------------------------

            # Non-compliance details

            # ------------------------------------------------



            bidder_a_failures = (

                bidder_a_result.get(

                    "non_compliance_details",

                    []

                )

            )



            bidder_b_failures = (

                bidder_b_result.get(

                    "non_compliance_details",

                    []

                )

            )



            if bidder_a_failures or bidder_b_failures:



                st.markdown(

                    "#### Non-Compliance Details"

                )



            for failure in bidder_a_failures:



                st.error(

                    f"{bidder_a_result.get('name', 'Bidder A')} — "

                    f"{failure.get('field', 'Requirement')}: "

                    f"Bidder value "

                    f"{failure.get('bidder_value', 'Not available')} "

                    f"does not satisfy tender requirement "

                    f"{failure.get('requirement', 'Not available')}."

                )



            for failure in bidder_b_failures:



                st.error(

                    f"{bidder_b_result.get('name', 'Bidder B')} — "

                    f"{failure.get('field', 'Requirement')}: "

                    f"Bidder value "

                    f"{failure.get('bidder_value', 'Not available')} "

                    f"does not satisfy tender requirement "

                    f"{failure.get('requirement', 'Not available')}."

                )



            # ------------------------------------------------

            # Provisional recommendation warning

            # ------------------------------------------------



            if recommendation_details.get(

                "provisional",

                False

            ):



                st.warning(

                    "This is a provisional recommendation "

                    "based on the currently implemented tender "

                    "compliance checks. BOQ and final financial "

                    "evaluation should be completed before the "

                    "final contract award."

                )



        else:



            st.info(

                "No bidder recommendation is currently "

                "available from the backend."

            )



        # ----------------------------------------------------

        # Important differences

        # ----------------------------------------------------



        differences = comparison_data.get(

            "differences",

            []

        )



        if differences:



            st.subheader(

                "Important Differences"

            )



            for item in differences:



                with st.expander(

                    item.get(

                        "field",

                        "Difference"

                    )

                ):



                    st.write(

                        "**Impact:**",

                        item.get(

                            "impact",

                            ""

                        )

                    )



                    st.write(

                        "**Analysis:**",

                        item.get(

                            "message",

                            ""

                        )

                    )





# ============================================================
# RAG ASSISTANT
# ============================================================

elif page == "RAG Assistant":
    st.header("🤖 RAG Tender Assistant")

    st.write(
        "Ask questions about the uploaded tender. "
        "The assistant retrieves relevant tender sections "
        "before generating an evidence-grounded answer."
    )

    if tender_data is None:
        st.info("Upload and analyze the tender documents first.")
    else:
        st.subheader("Example Questions")
        st.markdown(
            """
- What is the EMD requirement?
- What is the performance security requirement?
- What is the completion period?
- What are the liquidated damages?
- What are the eligibility requirements?
- What is the proposal validity period?
            """
        )

        question = st.text_area(
            "Ask a question",
            placeholder="Example: What is the proposal validity period?",
            height=100,
            key="rag_question"
        )

        if st.button(
            "🔎 Ask RAG Assistant",
            type="primary",
            key="rag_ask_button"
        ):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                try:
                    from src.rag.rag_pipeline import answer_question

                    with st.spinner(
                        "Searching tender evidence and generating answer..."
                    ):
                        result = answer_question(
                            question=question,
                            tender_id="tender_001",
                            top_k=3
                        )

                    st.divider()
                    st.subheader("💬 Answer")

                    if isinstance(result, dict):
                        answer = result.get(
                            "answer",
                            "No answer generated."
                        )
                        st.success(answer)

                        sources = result.get("sources", [])
                        if sources:
                            st.subheader("📚 Retrieved Evidence")

                            for index, source in enumerate(sources, start=1):
                                rank = source.get("rank", index)
                                section_number = source.get(
                                    "section_number", ""
                                )
                                section_title = source.get(
                                    "section_title", "Unknown Section"
                                )
                                page_number = source.get(
                                    "page_number", "Unknown"
                                )
                                evidence = source.get("text", "")
                                distance = source.get("distance")

                                title = (
                                    f"Source {rank} — Section "
                                    f"{section_number}: {section_title} — "
                                    f"Page {page_number}"
                                )

                                with st.expander(title):
                                    st.markdown(
                                        f"**Section:** {section_number} - "
                                        f"{section_title}"
                                    )
                                    st.markdown(f"**Page:** {page_number}")

                                    if distance is not None:
                                        try:
                                            st.markdown(
                                                f"**Vector Distance:** "
                                                f"{float(distance):.4f}"
                                            )
                                        except (TypeError, ValueError):
                                            st.markdown(
                                                f"**Vector Distance:** {distance}"
                                            )

                                    st.markdown("**Evidence:**")
                                    st.write(evidence)
                        else:
                            st.info("No retrieved evidence was returned.")
                    else:
                        st.success(str(result))

                except Exception as e:
                    st.error("RAG Assistant failed.")
                    st.write("Error type:", type(e).__name__)
                    st.write("Error message:", str(e))
                    st.exception(e)

# ============================================================
# RISK ANALYSIS
# ============================================================

elif page == "Risk Analysis":
    st.header("⚠️ Tender & Bid Risk Analysis")
    st.write("Review tender, BOQ, and bidder compliance risks.")

    if tender_data is None:
        st.info("Upload and analyze the tender documents first.")
    else:
        st.subheader("1. Tender Risks")
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
            c1, c2, c3 = st.columns(3)
            c1.metric("🔴 High Risks", high)
            c2.metric("🟠 Medium Risks", medium)
            c3.metric("🟢 Low Risks", low)
            if not tender_risks:
                st.success("No rule-based tender risks detected.")
            else:
                for risk_item in tender_risks:
                    severity = str(risk_item.get("severity", "UNKNOWN")).upper()
                    risk_type = risk_item.get("risk_type", risk_item.get("type", risk_item.get("category", "Tender Risk")))
                    description = risk_item.get("description", risk_item.get("message", risk_item.get("reason", "Risk detected.")))
                    icon = {"HIGH":"🔴", "MEDIUM":"🟠", "LOW":"🟢"}.get(severity, "⚪")
                    with st.expander(f"{icon} {severity} — {risk_type}"):
                        st.write(description)
                        if risk_item.get("page"):
                            st.caption(f"Tender evidence: Page {risk_item.get('page')}")
        except ImportError:
            st.warning("Could not import analyze_risks from src/risk/risk_analyzer.py.")
        except Exception as e:
            st.error("Tender risk analysis could not be completed.")
            st.exception(e)

        st.divider()
        st.subheader("2. Bidder BOQ Risks")
        c1, c2 = st.columns(2)
        for column, label, data in [(c1, "Bidder A", bidder_a_data), (c2, "Bidder B", bidder_b_data)]:
            with column:
                st.markdown(f"### {label}")
                if data:
                    items = data.get("boq_validation", [])
                    issue_count = count_boq_issues(items)
                    st.metric("BOQ Items With Issues", issue_count)
                    if issue_count == 0:
                        st.success("No BOQ validation issues detected.")
                    else:
                        for item in items:
                            issues = item.get("issues", [])
                            if str(item.get("status", "")).upper() == "ISSUE" or issues:
                                st.warning(f"Item {item.get('item_no', '')}: {item.get('description', '')}")
                                if issues:
                                    st.write(", ".join(map(str, issues)))
                else:
                    st.info(f"No {label} data available.")

        st.divider()
        st.subheader("3. Bidder Compliance Risks")
        if comparison_data:
            found = False
            for item in comparison_data.get("field_comparisons", []):
                field = item.get("field", "Requirement")
                requirement = item.get("tender_requirement", "")
                a_status = str(item.get("bidder_a_status", "")).upper()
                b_status = str(item.get("bidder_b_status", "")).upper()
                if "NON" in a_status or "FAIL" in a_status:
                    found = True
                    st.error(f"Bidder A — {field}: {a_status}. Tender requirement: {requirement}")
                if "NON" in b_status or "FAIL" in b_status:
                    found = True
                    st.error(f"Bidder B — {field}: {b_status}. Tender requirement: {requirement}")
            if not found:
                st.success("No bidder non-compliance was identified in the currently compared fields.")
        else:
            st.info("Bid comparison data is not available.")

        st.caption("Risk indicators are decision-support outputs and should be reviewed against the original tender and bidder documents before procurement decisions are made.")
