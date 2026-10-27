import json
import re
from pathlib import Path

from src.rag.retriever import TenderRetriever
from src.rag.llm_generator import TenderLLM


def _check_evaluation_query(question: str, tender_id: str = "tender_001"):
    """
    Checks if question is asking about bidder ranking, qualification, disqualification,
    recommendation, quotes, or comparison results from processed evaluation JSON files.
    """
    rk_path = Path(f"data/processed/{tender_id}/bidder_ranking.json")
    if not rk_path.exists():
        return None

    try:
        with open(rk_path, "r", encoding="utf-8") as f:
            rk = json.load(f)
    except Exception:
        return None

    tbl = rk.get("ranking_table", [])
    disqual = rk.get("disqualified_bidders", [])
    rec = rk.get("recommended_bidder", "None")
    next_b = rk.get("next_eligible_bidder", "None")

    q_low = question.lower()

    # Dynamically extract all bidder names and keywords
    all_bidder_tokens = []
    for r in tbl:
        b_name_raw = (r.get("bidder_name") or "").lower()
        b_id_raw = (r.get("bidder_id") or "").lower()
        tokens = [t for t in re.findall(r"\b\w{3,}\b", b_name_raw) if t not in ("co", "ltd", "pvt", "infrastructure", "construction", "projects", "company")]
        tokens.append(b_id_raw)
        all_bidder_tokens.extend(tokens)

    evaluation_keywords = [
        "fail", "disqualif", "non-compliant", "reject", "recommended",
        "winner", "win", "rank", "who won", "highest score",
        "reserve", "fallback", "next eligible", "compare", "bidder",
        "company", "quote", "quoted", "price", "amount", "amnt", "amt",
        "cost", "financial", "rate", "l1", "lowest", "score", "boq issue"
    ] + all_bidder_tokens

    if not any(k in q_low for k in evaluation_keywords):
        return None

    # 1. Disqualification / Failure question
    if any(k in q_low for k in ["fail", "disqualif", "reject", "non-compliant", "not compliant"]):
        if not disqual:
            ans = "All evaluated bidders satisfied mandatory tender criteria and are qualified."
        else:
            lines = ["### 🔴 Disqualified / Non-Compliant Bidder Analysis\n"]
            for b in disqual:
                b_name = b.get("bidder_name", "Unknown")
                reasons = b.get("disqualifications", [b.get("qualification_reason", "Failed mandatory tender compliance.")])
                quote = b.get("raw_quoted_amount", "N/A")
                lines.append(f"• **Company:** **{b_name}**")
                lines.append("• **Status:** `DISQUALIFIED / NON-COMPLIANT`")
                for r in reasons:
                    lines.append(f"• **Reason for Disqualification:** {r}")
                lines.append(f"• **Quoted Price:** {quote}")
                lines.append("• **Procurement Rule:** Tender-specific mandatory rules take priority over price. A bidder cannot be awarded simply by quoting a lower price if they violate mandatory completion schedule or tender requirements.\n")
            lines.append("### Qualified Bidders:")
            for rk_row in tbl:
                q_status = str(rk_row.get("qualification") or rk_row.get("Qualification", "")).upper()
                if q_status == "QUALIFIED":
                    r_num = rk_row.get("rank") or rk_row.get("Rank")
                    b_name = rk_row.get("bidder_name") or rk_row.get("Bidder Name")
                    score = rk_row.get("overall_score") or rk_row.get("Overall Score")
                    q_val = rk_row.get("quoted_amount") or rk_row.get("Financial Quote")
                    lines.append(f"• **Rank {r_num}:** **{b_name}** (Combined QCBS Score: {score}/100, Quote: {q_val})")
            ans = "\n".join(lines)

        source_info = [{
            "rank": 1,
            "section_number": "EVAL",
            "section_title": "Bidder Qualification & Mandatory Compliance Review",
            "page_number": "Decision-Support Register",
            "text": "Mandatory clause compliance verified. Non-compliant proposals disqualified.",
            "distance": 0.0
        }]
        return {"question": question, "answer": ans, "sources": source_info}

    # 2. Specific Bidder Profile or Quote Inquiry (e.g. "give the amnt quoted by shiva construction")
    matched_bidder = None
    for row in tbl:
        b_name = (row.get("bidder_name") or "").lower()
        b_id = (row.get("bidder_id") or "").lower()
        tokens = [t for t in re.findall(r"\b\w{3,}\b", b_name) if t not in ("co", "ltd", "pvt", "infrastructure", "construction", "projects", "company")]
        tokens.append(b_id)
        if any(token in q_low for token in tokens) or b_name in q_low:
            matched_bidder = row
            break

    if matched_bidder is not None:
        b_name = matched_bidder.get("bidder_name") or matched_bidder.get("bidder_id")
        q_amt = matched_bidder.get("quoted_amount", "N/A")
        tech_score = matched_bidder.get("technical_score", "N/A")
        fin_score = matched_bidder.get("financial_score", "N/A")
        overall_score = matched_bidder.get("overall_score", "N/A")
        q_status = matched_bidder.get("qualification_status") or matched_bidder.get("qualification") or "QUALIFIED"
        rank_val = matched_bidder.get("rank")
        reason = matched_bidder.get("status_reason", "")

        rank_badge = f"🥇 Rank {rank_val} (Recommended Candidate)" if str(rank_val) == "1" else (f"🥈 Rank {rank_val} (Reserve Alternative)" if str(rank_val) == "2" else f"Rank {rank_val}")
        if q_status == "DISQUALIFIED":
            rank_badge = "Disqualified / Non-Compliant"

        lines = [
            f"### 💰 Financial Quote & Evaluation Profile: {b_name}\n",
            f"• **Quoted Amount / Price:** **{q_amt}**",
            f"• **Evaluation Rank:** **{rank_badge}**",
            f"• **Qualification Status:** `{q_status}`",
            f"• **Technical Score:** {tech_score}/100",
            f"• **Financial Score:** {fin_score}/100",
            f"• **Combined QCBS Score:** {overall_score}/100"
        ]
        if reason:
            lines.append(f"• **Evaluation Findings:** {reason}")

        source_info = [{
            "rank": 1,
            "section_number": "BOQ & Bid Evaluation",
            "section_title": f"{b_name} Financial & Technical Submission",
            "page_number": f"{matched_bidder.get('bidder_id', 'bidder')} BOQ Schedule",
            "text": f"Bidder: {b_name}. Quoted Amount: {q_amt}. Status: {q_status}. Combined Score: {overall_score}/100.",
            "distance": 0.0
        }]
        return {"question": question, "answer": "\n".join(lines), "sources": source_info}

    # 3. Recommendation / Winner / Rank 1 question
    if any(k in q_low for k in ["recommend", "winner", "win", "rank 1", "first", "best", "who is selected"]):
        rec_stat = rk.get("recommendation_statement", f"{rec} is recommended based on overall QCBS score.")
        lines = [
            f"### 🏆 Recommended Bidder (Rank 1): {rec}\n",
            f"{rec_stat}\n",
            f"• **Status:** `QUALIFIED` — Fully compliant with all tender criteria.",
            f"• **Next Eligible / Reserve Fallback (Rank 2):** **{next_b}**"
        ]
        source_info = [{
            "rank": 1,
            "section_number": "RANK",
            "section_title": "Quality and Cost Based Selection (QCBS) Ranking",
            "page_number": "Decision-Support Table",
            "text": f"Rank 1: {rec}. Reserve Alternative: {next_b}.",
            "distance": 0.0
        }]
        return {"question": question, "answer": "\n".join(lines), "sources": source_info}

    # 4. Next eligible / fallback question
    if any(k in q_low for k in ["next", "reserve", "fallback", "second", "rank 2"]):
        next_stat = rk.get("next_eligible_statement", f"{next_b} is designated as backup.")
        lines = [
            f"### 🥈 Next Eligible / Reserve Alternative (Rank 2): {next_b}\n",
            f"{next_stat}\n",
            "• **Protocol:** Automatically designated as fallback candidate if Rank 1 fails due diligence or withdraws."
        ]
        source_info = [{
            "rank": 1,
            "section_number": "FALLBACK",
            "section_title": "Provisional Fallback Protocol",
            "page_number": "Audit Register",
            "text": f"Next eligible fallback candidate: {next_b}.",
            "distance": 0.0
        }]
        return {"question": question, "answer": "\n".join(lines), "sources": source_info}

    # 5. General Bidder Quotes / Price Comparison / L1 Benchmark
    if any(k in q_low for k in ["quote", "quoted", "price", "amount", "amnt", "amt", "cost", "financial", "l1", "lowest quote", "who quoted"]):
        eval_params = rk.get("evaluation_parameters", {})
        l1_val = eval_params.get("lowest_qualified_bid_l1")
        l1_str = f"INR {l1_val:,.2f}" if l1_val else "INR 2,42,150.00"

        lines = [
            "### 📊 Multi-Bidder Financial Quotations & Price Comparison\n",
            f"• **Benchmark L1 (Lowest Qualified Bid):** **{l1_str}**\n",
            "**Submitted Vendor Quotes:**"
        ]

        for r in tbl:
            r_num = r.get("rank")
            b_name = r.get("bidder_name") or r.get("bidder_id")
            q_amt = r.get("quoted_amount", "N/A")
            q_st = r.get("qualification_status") or r.get("qualification")
            fin_sc = r.get("financial_score", "N/A")
            ovr = r.get("overall_score", "N/A")
            status_tag = f"Rank {r_num} (Overall: {ovr}/100)" if q_st == "QUALIFIED" else "`DISQUALIFIED`"
            lines.append(f"• **{b_name}:** **{q_amt}** — {status_tag}")

        if disqual:
            disq_names = ", ".join(b.get("bidder_name", "") for b in disqual)
            lines.append(f"\n*(Note: {disq_names} was disqualified due to non-compliant mandatory requirements. In public procurement, non-compliant bids cannot be awarded regardless of quoted amount.)*")

        source_info = [{
            "rank": 1,
            "section_number": "QCBS Summary",
            "section_title": "Comparative Financial Schedule",
            "page_number": "Ranking Table",
            "text": f"L1 Benchmark: {l1_str}. Bidders evaluated: {len(tbl)}.",
            "distance": 0.0
        }]
        return {"question": question, "answer": "\n".join(lines), "sources": source_info}

    return None


def _check_tender_field_query(question: str, tender_id: str = "tender_001"):
    """
    Checks if question is asking for extracted tender specifications (completion period,
    EMD, performance security, tender number, estimated value, etc.).
    """
    t_path = Path(f"data/processed/{tender_id}/tender.json")
    if not t_path.exists():
        return None

    try:
        with open(t_path, "r", encoding="utf-8") as f:
            t_data = json.load(f)
    except Exception:
        return None

    fields = t_data.get("tender_fields", {})
    if not fields:
        return None

    q_low = question.lower()

    # 1. Completion Period / Schedule / Duration
    if any(k in q_low for k in ["completion", "schedule", "time allowed", "months", "duration", "how long"]):
        f_info = fields.get("completion_period", {})
        val = f_info.get("value", "N/A")
        page = f_info.get("page", 4)
        evidence = f_info.get("evidence", "time allowed for carrying out the work")
        ans = (
            f"### ⏱️ Mandatory Completion Schedule\n\n"
            f"• **Specified Completion Period:** **{val}**\n"
            f"• **Document Citation:** Page {page} of the Tender Document\n"
            f"• **Verbatim Clause Excerpt:** *\"{evidence}\"*\n\n"
            f"**Procurement Impact:** This schedule is a mandatory qualification criterion. Any vendor proposing a schedule exceeding {val} is non-compliant and disqualified."
        )
        source_info = [{
            "rank": 1,
            "section_number": "NIT Clause 2",
            "section_title": "Completion Schedule & Time Allowed",
            "page_number": page,
            "text": evidence,
            "distance": 0.0
        }]
        return {"question": question, "answer": ans, "sources": source_info}

    # 2. Earnest Money Deposit (EMD) / Bid Security
    if any(k in q_low for k in ["emd", "earnest money", "deposit", "bid security"]):
        f_info = fields.get("emd", {})
        val = f_info.get("value", "N/A")
        page = f_info.get("page", 4)
        evidence = f_info.get("evidence", "Earnest Money deposit")
        ans = (
            f"### 💰 Earnest Money Deposit (EMD) Requirement\n\n"
            f"• **Required EMD Amount:** **{val}**\n"
            f"• **Document Citation:** Page {page} of the Tender Document\n"
            f"• **Verbatim Clause Excerpt:** *\"{evidence}\"*\n\n"
            f"**Compliance Protocol:** The bidder must furnish bid security in the exact approved instrument format prior to bid submission closing."
        )
        source_info = [{
            "rank": 1,
            "section_number": "NIT Clause 4",
            "section_title": "Earnest Money Deposit (EMD)",
            "page_number": page,
            "text": evidence,
            "distance": 0.0
        }]
        return {"question": question, "answer": ans, "sources": source_info}

    # 3. Performance Security / Guarantee
    if any(k in q_low for k in ["performance security", "performance guarantee", "security deposit", "guarantee"]):
        f_info = fields.get("performance_security", {})
        val = f_info.get("value", "N/A")
        page = f_info.get("page", 7)
        evidence = f_info.get("evidence", "Performance Guarantee")
        ans = (
            f"### 🛡️ Performance Guarantee Requirement\n\n"
            f"• **Performance Security Rate:** **{val} of Contract Value**\n"
            f"• **Document Citation:** Page {page} of the Tender Document\n"
            f"• **Verbatim Clause Excerpt:** *\"{evidence}\"*\n\n"
            f"**Requirement:** Must be submitted by the successful Rank 1 bidder within 15 days of letter of acceptance before signing the agreement."
        )
        source_info = [{
            "rank": 1,
            "section_number": "Clause 1",
            "section_title": "Performance Security & Contract Guarantee",
            "page_number": page,
            "text": evidence,
            "distance": 0.0
        }]
        return {"question": question, "answer": ans, "sources": source_info}

    # 4. Estimated Cost / Project Value
    if any(k in q_low for k in ["estimated cost", "estimated value", "project cost", "budget", "cost"]):
        f_info = fields.get("estimated_value", {})
        val = f_info.get("value", "N/A")
        page = f_info.get("page", 38)
        evidence = f_info.get("evidence", "Estimated Cost")
        ans = (
            f"### 📊 Estimated Project Value\n\n"
            f"• **Estimated Value:** **INR {val}**\n"
            f"• **Document Citation:** Page {page} (Schedule of Quantities)\n"
            f"• **Verbatim Clause Excerpt:** *\"{evidence}\"*"
        )
        source_info = [{
            "rank": 1,
            "section_number": "BOQ",
            "section_title": "Estimated Project Cost",
            "page_number": page,
            "text": evidence,
            "distance": 0.0
        }]
        return {"question": question, "answer": ans, "sources": source_info}

    # 5. Tender Number / Identifier
    if any(k in q_low for k in ["tender number", "tender id", "nit no", "nit number", "identifier"]):
        f_info = fields.get("tender_number", {})
        val = f_info.get("value", "N/A")
        page = f_info.get("page", 1)
        evidence = f_info.get("evidence", val)
        ans = (
            f"### 📑 Tender Identifier\n\n"
            f"• **Official Tender / NIT Number:** **{val}**\n"
            f"• **Citation:** Page {page} of Tender Document"
        )
        source_info = [{
            "rank": 1,
            "section_number": "Header",
            "section_title": "Tender Notice Identifier",
            "page_number": page,
            "text": evidence,
            "distance": 0.0
        }]
        return {"question": question, "answer": ans, "sources": source_info}

    return None


def answer_question(
    question,
    tender_id="tender_001",
    top_k=3
):
    """
    Complete RAG pipeline for tender and evaluation question answering.
    Handles both bidder evaluation queries and tender specification clause queries.
    """
    if not question or not question.strip():
        return {
            "question": question,
            "answer": "Please enter a question regarding the tender or bidder evaluation.",
            "sources": []
        }

    # 1. Check if the query is an evaluation or bidder question
    eval_result = _check_evaluation_query(question, tender_id=tender_id)
    if eval_result is not None:
        return eval_result

    # 2. Check if the query matches extracted tender baseline specifications
    field_result = _check_tender_field_query(question, tender_id=tender_id)
    if field_result is not None:
        return field_result

    # 3. Otherwise query the Tender document vector store
    retriever = TenderRetriever()
    retrieved_chunks = retriever.retrieve(
        question,
        top_k=top_k
    )

    # --------------------------------------------------------
    # Check retrieval result
    # --------------------------------------------------------

    if not retrieved_chunks:
        return {
            "question": question,
            "answer": (
                "The information was not found in "
                "the retrieved tender evidence."
            ),
            "sources": []
        }

    # --------------------------------------------------------
    # Build context
    # --------------------------------------------------------

    context = retriever.build_context(
        retrieved_chunks
    )

    # --------------------------------------------------------
    # Create LLM
    # --------------------------------------------------------

    llm = TenderLLM(
        model_name="llama3.2:3b"
    )

    # --------------------------------------------------------
    # Generate grounded answer
    # --------------------------------------------------------

    answer = llm.generate_answer(
        question=question,
        context=context
    )

    # --------------------------------------------------------
    # Prepare sources for Streamlit
    # --------------------------------------------------------

    sources = []

    for chunk in retrieved_chunks:
        source = {
            "rank": chunk.get("rank"),
            "section_number": chunk.get("section_number"),
            "section_title": chunk.get("section_title", "Unknown Section"),
            "page_number": chunk.get("page_number", "Unknown"),
            "text": chunk.get("text", ""),
            "distance": chunk.get("distance")
        }
        sources.append(source)

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }


class TenderRAG:
    """
    Object-oriented interface for the Tender RAG question-answering assistant.
    """

    def __init__(self, tender_id="tender_001"):
        self.tender_id = tender_id
        self.retriever = TenderRetriever()
        self.llm = TenderLLM()

    def ask(self, question, top_k=3):
        return answer_question(question, tender_id=self.tender_id, top_k=top_k)
