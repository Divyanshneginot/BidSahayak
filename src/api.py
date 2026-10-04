from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
from typing import Optional

from src.models import (
    RequirementMatrix,
    VendorProfile,
    BidVerdict,
    FieldEvidence,
)
from src.ingest import IngestWorker
from src.text_extract import TextWorker
from src.evaluator import evaluate

app = FastAPI(
    title="BidSahayak API",
    description="Agentic procurement eligibility reasoning engine for Indian MSMEs",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ingest_worker = IngestWorker(max_size_mb=25, max_pages=400)
text_worker = TextWorker()


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "BidSahayak",
        "version": "1.0.0",
        "track": "01 - Agentic AI",
    }


@app.post("/api/assess/upload")
async def upload_tender_pdf(file: UploadFile = File(...)):
    """W1 + W2: Ingest PDF, extract text, detect sections, and return initial metadata."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ingest_result = ingest_worker.process(file_path)
    if not ingest_result.is_valid:
        raise HTTPException(status_code=400, detail=ingest_result.rejection_reason)

    extraction = text_worker.process(file_path, tender_id=ingest_result.tender_id)

    return {
        "tender_id": ingest_result.tender_id,
        "file_name": ingest_result.file_name,
        "page_count": ingest_result.page_count,
        "sha256": ingest_result.sha256_hash,
        "is_scanned": extraction.is_scanned_document,
        "detected_sections": extraction.detected_sections,
        "pages_summary": [
            {"page": p_num, "chars": p_data.char_count, "is_scanned": p_data.is_scanned_likely}
            for p_num, p_data in extraction.pages.items()
        ],
    }


@app.post("/api/assess/evaluate", response_model=BidVerdict)
def run_evaluation(payload: dict):
    """
    W5: Pure deterministic comparison of RequirementMatrix against VendorProfile.
    """
    try:
        matrix_data = payload.get("matrix", {})
        profile_data = payload.get("profile", {})
        
        matrix = RequirementMatrix(**matrix_data)
        profile = VendorProfile(**profile_data)
        
        verdict = evaluate(matrix, profile)
        return verdict
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Evaluation validation error: {str(e)}")


@app.post("/api/assess/override", response_model=BidVerdict)
def override_requirement_field(payload: dict):
    """
    Human Gate G2: Human operator overrides an extracted field.
    Re-runs deterministic evaluation immediately with audit logging.
    """
    matrix_data = payload.get("matrix", {})
    profile_data = payload.get("profile", {})
    override_field = payload.get("field_name")
    new_value = payload.get("new_value")
    operator_note = payload.get("operator_note", "Human override via UI")

    if not override_field:
        raise HTTPException(status_code=400, detail="Missing field_name to override")

    # Apply override
    if override_field in matrix_data:
        matrix_data[override_field] = new_value

    evidence_fields = matrix_data.get("evidence_fields", {})
    if override_field in evidence_fields:
        evidence_fields[override_field]["value_normalised"] = new_value
        evidence_fields[override_field]["confidence"] = 1.0  # Operator certified
        evidence_fields[override_field]["ambiguity"] = f"Overridden by operator: {operator_note}"
    else:
        evidence_fields[override_field] = {
            "field_name": override_field,
            "value_raw": str(new_value),
            "value_normalised": new_value,
            "confidence": 1.0,
            "source_page": 1,
            "source_snippet": f"Operator manual input: {new_value}",
            "ambiguity": operator_note,
        }

    matrix_data["evidence_fields"] = evidence_fields
    matrix = RequirementMatrix(**matrix_data)
    profile = VendorProfile(**profile_data)

    verdict = evaluate(matrix, profile)
    verdict.audit_log.append({
        "action": "human_override",
        "field": override_field,
        "new_value": new_value,
        "note": operator_note,
    })
    return verdict
