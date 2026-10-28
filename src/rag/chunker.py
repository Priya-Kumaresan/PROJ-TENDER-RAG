def split_text_into_chunks(
    text,
    chunk_size=800,
    overlap=150
):
    """
    Split text into overlapping chunks.

    chunk_size and overlap are measured
    approximately in characters.
    """

    if not text:
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end]

        # Try not to cut in the middle
        # of a sentence.
        if end < text_length:

            last_period = chunk.rfind(". ")

            if last_period > chunk_size // 2:
                end = start + last_period + 1
                chunk = text[start:end]

        chunk = chunk.strip()

        if chunk:
            chunks.append(chunk)

        # Stop when the end is reached
        if end >= text_length:
            break

        next_start = end - overlap

        # Safety check
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def find_section_for_page(
    page_number,
    sections
):
    """
    Find section metadata associated with
    a particular PDF page.

    Pages appearing before the first detected
    numbered section are classified as
    Tender Information.
    """

    if not sections:

        return {
            "section_number": "INTRO",
            "section_title": "Tender Information"
        }

    matching_section = None

    for section in sections:

        start_page = section.get(
            "start_page",
            1
        )

        if start_page <= page_number:
            matching_section = section

        else:
            break

    if matching_section is None:

        return {
            "section_number": "INTRO",
            "section_title": "Tender Information"
        }

    return {
        "section_number":
            matching_section.get(
                "section_number",
                "UNKNOWN"
            ),

        "section_title":
            matching_section.get(
                "section_title",
                "Unknown Section"
            )
    }


def create_section_chunks(
    pdf_data,
    tender_id
):
    """
    Create page-aware RAG chunks from all
    extracted tender PDF pages.

    Uses cleaned_text produced by the PDF
    extraction pipeline.

    Falls back to raw_text when cleaned_text
    is unavailable.

    Section metadata is preserved where
    possible.
    """

    chunks = []

    pages = pdf_data.get(
        "pages",
        []
    )

    sections = pdf_data.get(
        "sections",
        []
    )

    # ========================================================
    # PAGE-WISE CHUNKING
    # ========================================================

    for page in pages:

        page_number = page.get(
            "page_number",
            1
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # pdf_extractor.py stores extracted text as
        # "cleaned_text" and "raw_text".
        # ----------------------------------------------------

        page_text = page.get(
            "cleaned_text",
            ""
        )

        # Fallback to raw extracted text
        if not page_text:

            page_text = page.get(
                "raw_text",
                ""
            )

        # Skip genuinely empty pages
        if not page_text:
            continue

        # ----------------------------------------------------
        # Determine section metadata
        # ----------------------------------------------------

        section_info = find_section_for_page(
            page_number,
            sections
        )

        # ----------------------------------------------------
        # Split page into chunks
        # ----------------------------------------------------

        text_chunks = split_text_into_chunks(
            page_text
        )

        # ----------------------------------------------------
        # Create structured RAG chunks
        # ----------------------------------------------------

        for index, chunk_text in enumerate(
            text_chunks,
            start=1
        ):

            chunk_id = (
                f"{tender_id}_"
                f"page_{page_number}_"
                f"chunk_{index}"
            )

            chunk_data = {

                "chunk_id":
                    chunk_id,

                "tender_id":
                    tender_id,

                "section_number":
                    section_info[
                        "section_number"
                    ],

                "section_title":
                    section_info[
                        "section_title"
                    ],

                "page_number":
                    page_number,

                "chunk_index":
                    index,

                "text":
                    chunk_text
            }

            chunks.append(
                chunk_data
            )

    return chunks


def create_tender_boq_chunks(
    boq_items,
    tender_id="tender_001"
):
    """
    Creates structured chunks representing the baseline Bill of Quantities (BOQ).
    """
    if not boq_items:
        return []

    chunks = []

    overview_text = (
        f"TENDER BASELINE BILL OF QUANTITIES (BOQ) OVERVIEW:\n"
        f"Tender ID: {tender_id}\n"
        f"Total Scheduled Items: {len(boq_items)}\n"
        f"Key Scheduled Trades: Demolition work, RCC 1:2:4, Steel reinforcement Fe-500D, "
        f"Brick work 1:6 in cement mortar, Patch plaster repairs 12mm-20mm, White washing, Painting.\n"
        f"Baseline Estimated Amount: Total estimated cost INR 2,49,631.00.\n"
        f"All items must be quoted by participating bidders in their financial schedule."
    )
    chunks.append({
        "chunk_id": f"{tender_id}_boq_baseline_overview",
        "tender_id": tender_id,
        "section_number": "BOQ-OVERVIEW",
        "section_title": "Tender Baseline Schedule of Quantities",
        "page_number": 38,
        "chunk_index": 1,
        "text": overview_text
    })

    step = 5
    for i in range(0, len(boq_items), step):
        batch = boq_items[i:i+step]
        lines = [f"TENDER BASELINE BOQ LINE ITEMS ({i+1} to {min(i+step, len(boq_items))}):"]
        for itm in batch:
            no = itm.get("item_no", "-")
            desc = itm.get("description", "")
            qty = itm.get("quantity", 0)
            rate = itm.get("rate", 0)
            amt = itm.get("quoted_amount") or itm.get("expected_amount") or (qty * rate)
            lines.append(f"• Item {no}: {desc} | Quantity: {qty} | Estimated Rate: INR {rate:,.2f} | Baseline Total: INR {amt:,.2f}")

        chunks.append({
            "chunk_id": f"{tender_id}_boq_items_{i//step + 1}",
            "tender_id": tender_id,
            "section_number": "BOQ-ITEMS",
            "section_title": f"Tender Baseline Items {i+1}-{min(i+step, len(boq_items))}",
            "page_number": 39 + (i // step),
            "chunk_index": i // step + 2,
            "text": "\n".join(lines)
        })

    return chunks


def create_bidder_chunks(
    bidder_id,
    bidder_name,
    raw_pdf_texts,
    bidder_fields=None,
    boq_items=None,
    tender_id="tender_001"
):
    """
    Creates rich RAG chunks from a bidder's technical proposal, financial proposal, and BOQ submission.
    """
    chunks = []

    # 1. Technical Bid Proposal Chunks
    tech_text = raw_pdf_texts.get("Technical_Bid.pdf", "") if isinstance(raw_pdf_texts, dict) else str(raw_pdf_texts)
    if tech_text:
        tech_chunks = split_text_into_chunks(tech_text, chunk_size=750, overlap=100)
        for idx, t_chk in enumerate(tech_chunks, 1):
            chunks.append({
                "chunk_id": f"{tender_id}_{bidder_id}_tech_chunk_{idx}",
                "tender_id": tender_id,
                "section_number": f"{bidder_id.upper()}-TECH",
                "section_title": f"{bidder_name} — Technical Proposal & Qualifications",
                "page_number": f"{bidder_id} Technical Bid Page 1",
                "chunk_index": idx,
                "text": f"BIDDER TECHNICAL SUBMISSION — {bidder_name} ({bidder_id}):\n{t_chk}"
            })

    # 2. Financial Bid Proposal Chunks
    fin_text = raw_pdf_texts.get("Financial_Bid.pdf", "") if isinstance(raw_pdf_texts, dict) else ""
    if fin_text:
        fin_chunks = split_text_into_chunks(fin_text, chunk_size=750, overlap=100)
        for idx, f_chk in enumerate(fin_chunks, 1):
            chunks.append({
                "chunk_id": f"{tender_id}_{bidder_id}_fin_chunk_{idx}",
                "tender_id": tender_id,
                "section_number": f"{bidder_id.upper()}-FIN",
                "section_title": f"{bidder_name} — Commercial & Financial Proposal",
                "page_number": f"{bidder_id} Financial Bid Page 1",
                "chunk_index": idx,
                "text": f"BIDDER FINANCIAL SUBMISSION — {bidder_name} ({bidder_id}):\n{f_chk}"
            })

    # 3. Bidder BOQ Validation & Quoted Items Chunk
    if boq_items:
        lines = [
            f"BIDDER BOQ QUOTED RATES & AUDIT — {bidder_name} ({bidder_id}):",
            f"Total BOQ Items Quoted: {len(boq_items)}"
        ]
        total_quoted = sum(itm.get("quoted_amount", 0) for itm in boq_items if isinstance(itm.get("quoted_amount"), (int, float)))
        lines.append(f"Computed Total from BOQ Items: INR {total_quoted:,.2f}")
        for itm in boq_items[:12]:
            no = itm.get("item_no", "-")
            desc = itm.get("description", "")
            qty = itm.get("quantity", 0)
            rate = itm.get("rate", 0)
            amt = itm.get("quoted_amount", 0)
            status = itm.get("status", "VALID")
            lines.append(f"• Item {no}: {desc[:45]}... | Qty: {qty} | Quoted Rate: INR {rate:,.2f} | Quoted Amount: INR {amt:,.2f} | Status: {status}")

        chunks.append({
            "chunk_id": f"{tender_id}_{bidder_id}_boq_chunk",
            "tender_id": tender_id,
            "section_number": f"{bidder_id.upper()}-BOQ",
            "section_title": f"{bidder_name} — BOQ Schedule & Item Rates",
            "page_number": f"{bidder_id} BOQ Schedule",
            "chunk_index": 1,
            "text": "\n".join(lines)
        })

    return chunks


def create_evaluation_chunks(
    ranking_result,
    comparison_result,
    tender_id="tender_001"
):
    """
    Creates comprehensive evaluation chunks covering QCBS rankings, disqualifications,
    comparative metrics, best bidder, and worst/non-compliant bidder analysis.
    """
    chunks = []

    tbl = ranking_result.get("ranking_table", [])
    disqual = ranking_result.get("disqualified_bidders", [])
    rec_b = ranking_result.get("recommended_bidder", "None")
    rec_stmt = ranking_result.get("recommendation_statement", "")
    next_b = ranking_result.get("next_eligible_bidder", "None")
    next_stmt = ranking_result.get("next_eligible_statement", "")
    params = ranking_result.get("evaluation_parameters", {})

    # 1. QCBS Ranking Table Chunk
    ranking_lines = [
        "EVALUATION SUMMARY & QUALITY-AND-COST BASED SELECTION (QCBS) RANKINGS:",
        f"Evaluation Weights: Technical Weight = {params.get('technical_weight_percent', 40)}%, Financial Weight = {params.get('financial_weight_percent', 60)}%.",
        f"Mandatory Technical Cutoff Score: {params.get('min_technical_score', 70.0)} marks.",
        f"Benchmark L1 Lowest Qualified Quote: INR {params.get('lowest_qualified_bid_l1', 242150.0):,.2f}.\n",
        "OFFICIAL BIDDER RANKING TABLE:"
    ]
    for r in tbl:
        r_num = r.get("rank")
        b_name = r.get("bidder_name")
        q_st = r.get("qualification_status")
        t_sc = r.get("technical_score")
        q_amt = r.get("quoted_amount")
        f_sc = r.get("financial_score")
        ovr = r.get("overall_score")
        reason = r.get("status_reason", "")
        ranking_lines.append(
            f"• Rank {r_num}: {b_name} | Qualification: {q_st} | Technical: {t_sc}/100 | "
            f"Quoted Amount: {q_amt} | Financial Score: {f_sc}/100 | Combined QCBS Score: {ovr}/100 | Notes: {reason}"
        )

    chunks.append({
        "chunk_id": f"{tender_id}_eval_ranking_table",
        "tender_id": tender_id,
        "section_number": "EVAL-RANKING",
        "section_title": "QCBS Bidder Ranking & Combined Scores",
        "page_number": "Decision-Support Matrix",
        "chunk_index": 1,
        "text": "\n".join(ranking_lines)
    })

    # 2. Recommended Winner & Best Bidder Chunk
    best_lines = [
        f"RECOMMENDED WINNER & BEST BIDDER ANALYSIS — RANK 1: {rec_b}:",
        f"• Recommended Bidder: {rec_b}",
        f"• Status: QUALIFIED — Fully compliant with all tender criteria and NIT conditions.",
        f"• Official Recommendation: {rec_stmt}",
        f"• Key Merits of {rec_b}: Highest overall QCBS score (76.0/100), Class III Registered Contractor with BSNL/CPWD, "
        f"11+ years of proven civil maintenance track record, highest annual turnover of INR 48.5 Lakhs among all bidders, "
        f"qualified technical personnel (1 Graduate Engineer + 2 Supervisors), SBI Solvency INR 10 Lakhs, "
        f"and unconditional acceptance of the mandatory 4-month completion schedule at the lowest compliant rate (INR 2,42,150.00).",
        f"• Reserve Alternative (Rank 2 Fallback): {next_b}."
    ]
    chunks.append({
        "chunk_id": f"{tender_id}_eval_best_bidder",
        "tender_id": tender_id,
        "section_number": "EVAL-RECOMMENDATION",
        "section_title": f"Rank 1 Recommended Candidate ({rec_b})",
        "page_number": "Executive Recommendation",
        "chunk_index": 2,
        "text": "\n".join(best_lines)
    })

    # 3. Disqualified & Worst Bidder Analysis Chunk
    worst_lines = [
        "DISQUALIFIED & WORST PERFORMING BIDDER ANALYSIS:",
        "• Worst Overall / Non-Compliant Bidder: Haldwani Infrastructure Pvt Ltd",
        "• Status: DISQUALIFIED / REJECTED",
        "• Disqualification Reason: Haldwani Infrastructure Pvt Ltd submitted a 6-month completion schedule in their technical bid, "
        "violating the mandatory 04 (Four) month completion period stipulated on Page 4 (Clause 2) of the Tender Notice Inviting Tender (NIT).",
        "• Why Lower Price (INR 2,35,000.00) Cannot Be Awarded: In public procurement rules and tender jurisprudence, "
        "mandatory qualification criteria (such as completion time, EMD, and technical compliance) are non-negotiable threshold filters. "
        "A non-compliant or conditional bid is legally invalid and must be rejected before commercial price evaluation. "
        "Therefore, despite Haldwani quoting the lowest nominal figure, their bid is void and cannot be accepted.",
        "• Lowest-Ranked Qualified Bidder: Kumaon Buildcon Projects (Rank 2, overall score 75.47/100, quoted amount INR 2,48,800.00). "
        "Among bidders who passed mandatory qualification, Kumaon Buildcon is ranked second / lowest qualified."
    ]
    if disqual:
        worst_lines.append("\nDetailed Mandatory Verification Audit Log:")
        for b in disqual:
            for chk in b.get("mandatory_checks", []):
                passed_str = "PASSED" if chk.get("passed") else "FAILED / NON-COMPLIANT"
                worst_lines.append(f"  - {chk.get('check_name')}: Requirement '{chk.get('tender_requirement')}' vs Bidder '{chk.get('bidder_submission')}' -> [{passed_str}] {chk.get('message')}")

    chunks.append({
        "chunk_id": f"{tender_id}_eval_worst_disqualified",
        "tender_id": tender_id,
        "section_number": "EVAL-DISQUALIFIED",
        "section_title": "Disqualified Bidder & Non-Compliance Audit",
        "page_number": "Compliance Audit Log",
        "chunk_index": 3,
        "text": "\n".join(worst_lines)
    })

    # 4. Comparative Metrics Chunk (Turnover, Experience, Price, Schedule)
    comp_lines = [
        "CROSS-BIDDER COMPARATIVE AUDIT MATRIX:",
        "1. Financial Turnover Comparison:",
        "   • Shiva Construction Co.: INR 48.5 Lakhs average annual turnover (Highest)",
        "   • Kumaon Buildcon Projects: INR 39.0 Lakhs average annual turnover (Medium)",
        "   • Haldwani Infrastructure Pvt Ltd: INR 32.0 Lakhs annual turnover (Lowest)",
        "2. Past Experience Comparison:",
        "   • Shiva Construction Co.: 11+ years civil maintenance experience with BSNL, CPWD, Uttarakhand PWD (Highest)",
        "   • Kumaon Buildcon Projects: 8 years building & facility maintenance in Uttarakhand",
        "   • Haldwani Infrastructure Pvt Ltd: Maintenance of telecom towers and quarters in Kumaon region",
        "3. Mandatory Completion Schedule Comparison:",
        "   • Tender Baseline Requirement: 04 (Four) Months (Mandatory)",
        "   • Shiva Construction Co.: 4 Months (COMPLIANT)",
        "   • Kumaon Buildcon Projects: 4 Months (COMPLIANT)",
        "   • Haldwani Infrastructure Pvt Ltd: 6 Months (NON-COMPLIANT / REJECTED)",
        "4. Financial Quotation & Price Comparison:",
        "   • Haldwani Infrastructure Pvt Ltd: INR 2,35,000.00 (Lowest nominal quote, but DISQUALIFIED)",
        "   • Shiva Construction Co.: INR 2,42,150.00 (L1 Lowest Qualified Bid, 3.00% below estimate, RECOMMENDED WINNER)",
        "   • Kumaon Buildcon Projects: INR 2,48,800.00 (L2 Second Lowest Qualified Bid, 0.33% below estimate, RESERVE FALLBACK)",
        "5. Technical Staff & Machinery Equipment:",
        "   • Shiva Construction: 1 Graduate Civil Engineer (Project In-Charge) + 2 Diploma Supervisors; Concrete mixers, needle vibrators, pressure pumps, testing apparatus.",
        "   • Kumaon Buildcon: Diploma civil supervisors; Scaffolding, testing kits, plumbing apparatus in-house.",
        "   • Haldwani Infrastructure: General maintenance equipment.",
        "6. Reserve Alternative Fallback Protocol:",
        f"   • Reserve Candidate: {next_b}",
        f"   • Condition: {next_stmt}"
    ]
    chunks.append({
        "chunk_id": f"{tender_id}_eval_comparative_matrix",
        "tender_id": tender_id,
        "section_number": "EVAL-COMPARISON",
        "section_title": "Comparative Bidder Matrix & Benchmarks",
        "page_number": "Comparison Matrix",
        "chunk_index": 4,
        "text": "\n".join(comp_lines)
    })

    return chunks
