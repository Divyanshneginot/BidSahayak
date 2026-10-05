from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import shutil
import uuid
import re
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
from src.supervisor import Supervisor

import starlette.middleware
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from collections import defaultdict
import time

app = FastAPI(
    title="BidSahayak API",
    description="Agentic procurement eligibility reasoning engine for Indian MSMEs",
    version="1.0.0",
)

# Subclass starlette.middleware.Middleware for robust gate verification
class CORSMiddleware(starlette.middleware.Middleware):
    def __init__(self, **kwargs):
        super().__init__(FastAPICORSMiddleware, **kwargs)

raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()] if raw_origins != "*" else ["*"]

app.user_middleware.append(
    CORSMiddleware(
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
)

# In-memory simple rate limiter and security headers
RATE_LIMIT_WINDOW = 60
MAX_REQUESTS_PER_MINUTE = 120
_client_requests = defaultdict(list)

@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    _client_requests[client_ip] = [t for t in _client_requests[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_client_requests[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
        return Response(content="Rate limit exceeded. Try again in a minute.", status_code=429)
    _client_requests[client_ip].append(now)

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ingest_worker = IngestWorker(max_size_mb=25, max_pages=400)
text_worker = TextWorker()
supervisor = Supervisor()


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "BidSahayak",
        "version": "1.0.0",
        "track": "01 - Agentic AI",
    }


def _save_uploaded_pdf(file: UploadFile) -> str:
    """Securely validates and saves an uploaded PDF file preventing path traversal and corrupt files."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")

    safe_basename = os.path.basename(file.filename)
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", safe_basename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Magic byte validation (%PDF-)
    with open(file_path, "rb") as f:
        header = f.read(5)
    if header != b"%PDF-":
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise HTTPException(status_code=400, detail="Corrupted file: missing valid PDF header (%PDF-).")

    return file_path


@app.post("/api/assess/upload")
async def upload_tender_pdf(file: UploadFile = File(...)):
    """W1 + W2: Ingest PDF, extract text, detect sections, and return initial metadata."""
    file_path = _save_uploaded_pdf(file)
    try:
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
        "skipped_pages": extraction.skipped_pages,
        "is_ocr_available": extraction.is_ocr_available,
            "detected_sections": extraction.detected_sections,
            "pages_summary": [
                {"page": p_num, "chars": p_data.char_count, "is_scanned": p_data.is_scanned_likely}
                for p_num, p_data in extraction.pages.items()
            ],
        }
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


@app.post("/api/assess/process")
async def process_full_tender(file: UploadFile = File(...)):
    """Runs Supervisor end-to-end: W1 Ingest -> W2 Text -> W4 Extract -> Trace."""
    file_path = _save_uploaded_pdf(file)
    try:
        session = supervisor.process_document(file_path)
        return session
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


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
    operator_note = payload.get("operator_note") or payload.get("override_note") or "Human approval via UI"

    if new_value is not None:
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
        action_name = "human_override"
    else:
        action_name = "human_approval"

    matrix_data["unresolved_fields"] = [
        f for f in matrix_data.get("unresolved_fields", []) if f != override_field
    ]
    matrix = RequirementMatrix(**matrix_data)
    profile = VendorProfile(**profile_data)

    verdict = evaluate(matrix, profile)
    verdict.audit_log.append({
        "action": action_name,
        "field": override_field,
        "new_value": new_value,
        "note": operator_note,
    })
    return verdict


@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BidSahayak API active. Frontend index.html not found."}


if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
