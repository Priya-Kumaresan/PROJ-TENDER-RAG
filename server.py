"""
FastAPI Backend Server for Tender & BOQ Evaluation Assistant
Serves the HTML/CSS/JavaScript single-page application and provides
REST API endpoints for document analysis, RAG query, and ranking simulation.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure required libraries from local environments are discoverable as fallbacks
for extra in [r"D:\document-intelligence\.venv\Lib\site-packages", r"D:\Python\Lib\site-packages"]:
    if extra not in sys.path:
        sys.path.append(extra)

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Project directories
BASE_DIR = Path(__file__).resolve().parent
RAW_FOLDER = BASE_DIR / "data" / "raw" / "tender_001"
PROCESSED_FOLDER = BASE_DIR / "data" / "processed" / "tender_001"
WEB_DIR = BASE_DIR / "web"

RAW_FOLDER.mkdir(parents=True, exist_ok=True)
PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)
WEB_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Tender & BOQ Analysis API", version="2.0.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_json(file_path: Path) -> Optional[Any]:
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path.name}: {e}")
        return None


def _get_subprocess_env() -> Dict[str, str]:
    sub_env = os.environ.copy()
    extra_paths = [
        r"D:\document-intelligence\.venv\Lib\site-packages",
        r"D:\Python\Lib\site-packages"
    ]
    current_pp = sub_env.get("PYTHONPATH", "")
    sub_env["PYTHONPATH"] = ";".join(extra_paths + ([current_pp] if current_pp else []))
    return sub_env


def _run_pipeline() -> subprocess.CompletedProcess:
    env = _get_subprocess_env()
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "main.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(BASE_DIR)
    )
    return result


# Request Models
class AskRequest(BaseModel):
    question: str
    tender_id: Optional[str] = "tender_001"


class FallbackRequest(BaseModel):
    bidder_id: str
    reason: Optional[str] = "Failed post-qualification verification"


# API Endpoints
@app.get("/api/status")
def get_status():
    tender_file = PROCESSED_FOLDER / "tender.json"
    ranking_file = PROCESSED_FOLDER / "bidder_ranking.json"
    has_data = tender_file.exists() and ranking_file.exists()

    tender_data = _load_json(tender_file) if has_data else None
    ranking_data = _load_json(ranking_file) if has_data else None

    tender_no = "Not Loaded"
    org = "No tender documents evaluated"
    project = "-"
    recommended = "Pending Upload"
    bidders_count = 0

    if tender_data:
        fields = tender_data.get("tender_fields", {})
        tender_no = fields.get("tender_number", {}).get("value", "N/A")
        org = fields.get("organisation", {}).get("value", "N/A")
        project = fields.get("project_name", {}).get("value", "N/A")

    if ranking_data:
        recommended = ranking_data.get("recommended_bidder", "None")
        bidders_count = len(ranking_data.get("ranking_table", []))

    return {
        "has_data": has_data,
        "tender_number": tender_no,
        "organisation": org,
        "project_name": project,
        "recommended_bidder": recommended,
        "bidders_count": bidders_count
    }


@app.get("/api/data")
def get_all_data():
    tender_data = _load_json(PROCESSED_FOLDER / "tender.json")
    tender_boq = _load_json(PROCESSED_FOLDER / "tender_boq.json")
    comparison = _load_json(PROCESSED_FOLDER / "bid_comparison.json") or _load_json(PROCESSED_FOLDER / "comparison.json")
    ranking = _load_json(PROCESSED_FOLDER / "bidder_ranking.json")

    # Load all bidder files
    bidders = {}
    for f in PROCESSED_FOLDER.glob("bidder_*.json"):
        if f.name == "bidder_ranking.json":
            continue
        bidder_data = _load_json(f)
        if bidder_data:
            b_id = bidder_data.get("bidder_id", f.stem)
            bidders[b_id] = bidder_data

    # Tender contractual risks
    risks = []
    if tender_data:
        try:
            from src.risk.risk_analyzer import analyze_risks
            t_fields = tender_data.get("tender_fields", {})
            risks = analyze_risks(t_fields) or []
        except Exception as e:
            print(f"Risk analysis error: {e}")

    return {
        "tender": tender_data,
        "tender_boq": tender_boq,
        "bidders": bidders,
        "comparison": comparison,
        "ranking": ranking,
        "risks": risks
    }


@app.post("/api/rag/ask")
def rag_ask(req: AskRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        from src.rag.rag_pipeline import answer_question
        result = answer_question(req.question, tender_id=req.tender_id or "tender_001")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")


@app.post("/api/ranking/fallback")
def simulate_fallback(req: FallbackRequest):
    ranking_data = _load_json(PROCESSED_FOLDER / "bidder_ranking.json")
    if not ranking_data:
        raise HTTPException(status_code=400, detail="No ranking data available to simulate fallback.")
    try:
        from src.comparison.bidder_ranker import BidderRanker
        ranker = BidderRanker()
        updated = ranker.simulate_fallback(
            ranking_result=ranking_data,
            disqualified_bidder_id=req.bidder_id,
            disqualification_reason=req.reason
        )
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallback recalculation failed: {str(e)}")


@app.post("/api/clear")
def clear_all_data():
    """
    Clears all processed evaluation results and uploaded files, resetting
    the dashboard to a completely fresh state.
    """
    try:
        if PROCESSED_FOLDER.exists():
            for f in PROCESSED_FOLDER.iterdir():
                if f.is_file():
                    try:
                        f.unlink()
                    except Exception:
                        pass

        if RAW_FOLDER.exists():
            for item in RAW_FOLDER.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                elif item.is_file():
                    try:
                        item.unlink()
                    except Exception:
                        pass

        return {"success": True, "message": "All evaluation data cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")


@app.post("/api/analyze")
async def analyze_documents(request: Request):
    """
    Accepts uploaded Common Tender and N Bidder documents, saves them to data/raw/tender_001,
    and executes the automated pipeline.
    """
    form = await request.form()
    
    tender_pdf = form.get("tender_pdf")
    tender_boq = form.get("tender_boq")
    bidder_count_raw = form.get("bidder_count")
    bidder_data_json = form.get("bidder_data_json")

    if not tender_pdf or not tender_boq:
        raise HTTPException(status_code=400, detail="Tender PDF and Tender BOQ files are required.")

    try:
        bidders_info = json.loads(bidder_data_json) if bidder_data_json else []
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid bidder_data_json payload.")

    # 1. Clear previous processed files
    if PROCESSED_FOLDER.exists():
        for f in PROCESSED_FOLDER.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                except Exception:
                    pass

    # 2. Clear previous raw files
    if RAW_FOLDER.exists():
        for item in RAW_FOLDER.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.is_file():
                try:
                    item.unlink()
                except Exception:
                    pass

    # 3. Save Common Tender files
    t_dest = RAW_FOLDER / "tender"
    t_dest.mkdir(parents=True, exist_ok=True)
    t_pdf_path = t_dest / tender_pdf.filename
    with open(t_pdf_path, "wb") as f:
        f.write(await tender_pdf.read())

    t_boq_path = t_dest / tender_boq.filename
    with open(t_boq_path, "wb") as f:
        f.write(await tender_boq.read())

    # 4. Save each Bidder's documents
    names_map = {}
    for b_item in bidders_info:
        b_id = b_item.get("id")
        b_name = b_item.get("name") or b_id
        names_map[b_id] = b_name

        b_folder = RAW_FOLDER / b_id
        b_folder.mkdir(parents=True, exist_ok=True)

        tech_file = form.get(f"file_{b_id}_tech")
        if tech_file and hasattr(tech_file, "filename") and tech_file.filename:
            with open(b_folder / tech_file.filename, "wb") as f:
                f.write(await tech_file.read())

        fin_file = form.get(f"file_{b_id}_fin")
        if fin_file and hasattr(fin_file, "filename") and fin_file.filename:
            with open(b_folder / fin_file.filename, "wb") as f:
                f.write(await fin_file.read())

        boq_file = form.get(f"file_{b_id}_boq")
        if boq_file and hasattr(boq_file, "filename") and boq_file.filename:
            with open(b_folder / boq_file.filename, "wb") as f:
                f.write(await boq_file.read())

    with open(RAW_FOLDER / "bidder_names.json", "w", encoding="utf-8") as f:
        json.dump(names_map, f, indent=4)

    # 5. Run automated pipeline
    result = _run_pipeline()
    if result.returncode != 0:
        return JSONResponse(status_code=500, content={"success": False, "log": result.stderr or result.stdout})

    return {"success": True, "message": "Evaluation pipeline completed successfully!", "log": result.stdout}


# Serve static frontend
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

    @app.get("/")
    def serve_frontend():
        index_file = WEB_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Tender & BOQ Analysis System API running. Web UI loading..."}


if __name__ == "__main__":
    print("\n" + "="*60)
    print("STARTING TENDER & BOQ ANALYSIS FASTAPI WEB SERVER")
    print("URL: http://localhost:8000")
    print("="*60 + "\n")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
