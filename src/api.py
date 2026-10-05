from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
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
from starlette.concurrency import run_in_threadpool
import threading
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
STRICT_REQUESTS_PER_MINUTE = 6
LLM_HOURLY_CAP = int(os.getenv("LLM_HOURLY_CAP", "60"))

_client_requests: dict[str, list[float]] = {}
_strict_requests: dict[str, list[float]] = {}
_rate_limit_lock = threading.Lock()

@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    # Exclude /api/health and /static from the limiter
    if path == "/api/health" or path.startswith("/api/health") or path.startswith("/static"):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    now = time.time()

    with _rate_limit_lock:
        # Prune empty IP keys
        for ip in list(_client_requests.keys()):
            active = [t for t in _client_requests[ip] if now - t < RATE_LIMIT_WINDOW]
            if active:
                _client_requests[ip] = active
            else:
                _client_requests.pop(ip, None)

        for ip in list(_strict_requests.keys()):
            active = [t for t in _strict_requests[ip] if now - t < RATE_LIMIT_WINDOW]
            if active:
                _strict_requests[ip] = active
            else:
                _strict_requests.pop(ip, None)

        # Stricter limit of 6/min per IP on POST /api/assess/process and /api/assess/upload
        if request.method == "POST" and path in ("/api/assess/process", "/api/assess/upload"):
            strict_list = _strict_requests.get(client_ip, [])
            if len(strict_list) >= STRICT_REQUESTS_PER_MINUTE:
                retry_after = max(1, int(RATE_LIMIT_WINDOW - (now - strict_list[0])))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Assessment rate limit exceeded. Maximum 6 uploads per minute."},
                    headers={"Retry-After": str(retry_after)},
                )
            _strict_requests.setdefault(client_ip, []).append(now)

        # General rate limit (120/min)
        general_list = _client_requests.get(client_ip, [])
        if len(general_list) >= MAX_REQUESTS_PER_MINUTE:
            retry_after = max(1, int(RATE_LIMIT_WINDOW - (now - general_list[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute."},
                headers={"Retry-After": str(retry_after)},
            )
        _client_requests.setdefault(client_ip, []).append(now)

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


def _save_uploaded_pdf(file: UploadFile, content_length: Optional[int] = None) -> str:
    """Securely validates and saves an uploaded PDF file in 1 MB chunks, capping at 25 MB."""
    if file.filename is None or not str(file.filename).strip():
        raise HTTPException(status_code=400, detail="Filename missing or invalid.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")

    # Early rejection if Content-Length > 26 MB
    cl = content_length
    if cl is None and hasattr(file, "headers") and file.headers:
        val = file.headers.get("content-length")
        if val is not None:
            try:
                cl = int(val)
            except (ValueError, TypeError):
                pass
    if cl is not None and cl > 26 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large: Content-Length exceeds 26 MB.")

    safe_basename = os.path.basename(file.filename)
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", safe_basename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    chunk_size = 1024 * 1024  # 1 MB
    max_bytes = 25 * 1024 * 1024  # 25 MB
    total_bytes = 0

    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = file.file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(status_code=413, detail="File size exceeds maximum 25 MB limit.")
                buffer.write(chunk)
    except Exception:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise

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


_supervisor_lock = threading.Lock()
_wait_counter_lock = threading.Lock()
_waiting_requests_count = 0
MAX_WAITING_REQUESTS = 3


async def _run_guarded(func):
    """Executes a synchronous callable in the threadpool under _supervisor_lock, limiting waiting queue to 3."""
    global _waiting_requests_count
    with _wait_counter_lock:
        if _waiting_requests_count >= MAX_WAITING_REQUESTS:
            raise HTTPException(status_code=503, detail="Busy, retry shortly")
        _waiting_requests_count += 1

    decremented = False

    def in_thread():
        nonlocal decremented
        global _waiting_requests_count
        with _supervisor_lock:
            if not decremented:
                with _wait_counter_lock:
                    _waiting_requests_count -= 1
                    decremented = True
            return func()

    try:
        return await run_in_threadpool(in_thread)
    finally:
        if not decremented:
            with _wait_counter_lock:
                if not decremented:
                    _waiting_requests_count -= 1
                    decremented = True


@app.post("/api/assess/upload")
async def upload_tender_pdf(request: Request, file: UploadFile = File(...)):
    """W1 + W2: Ingest PDF, extract text, detect sections, and return initial metadata."""
    cl_hdr = request.headers.get("content-length")
    cl_val = int(cl_hdr) if cl_hdr and cl_hdr.isdigit() else None
    if cl_val and cl_val > 26 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Content-Length exceeds 26 MB limit.")

    def _execute():
        file_path = _save_uploaded_pdf(file, content_length=cl_val)
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
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass

    return await _run_guarded(_execute)


@app.post("/api/assess/process")
async def process_full_tender(request: Request, file: UploadFile = File(...)):
    """Runs Supervisor end-to-end: W1 Ingest -> W2 Text -> W4 Extract -> Trace."""
    cl_hdr = request.headers.get("content-length")
    cl_val = int(cl_hdr) if cl_hdr and cl_hdr.isdigit() else None
    if cl_val and cl_val > 26 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Content-Length exceeds 26 MB limit.")

    def _execute():
        file_path = _save_uploaded_pdf(file, content_length=cl_val)
        try:
            session = supervisor.process_document(file_path)
            return session
        finally:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass

    return await _run_guarded(_execute)


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
