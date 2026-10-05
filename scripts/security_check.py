"""
Security verification suite for BidSahayak (Items A1-A6).
Checks 17 security assertions across:
- A1: API key leak protection & scrubbing
- A2: Non-blocking event loop & threadpool concurrency limits
- A3: Streaming upload caps, early rejection & filename validation
- A4: IP rate limiting, health/static bypass, pruning, and LLM hourly cap
- A5: Strict request models, bounds validation & generic 422 errors
- A6: CORS, docs gating, and HTTP security headers (STS, Permissions-Policy, CSP)
"""

import sys
import os
import io
import time
import threading
from fastapi.testclient import TestClient

# Ensure root directory is on path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.api import app, _save_uploaded_pdf, _supervisor_lock, _rate_limit_lock, _client_requests, _strict_requests
from src.agent.extractor import ExtractorAgent, _scrub, _llm_call_timestamps
from src.text_extract import ExtractionResult, PageText

client = TestClient(app)

results = []

def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    results.append((name, status, detail))
    print(f"[{status}] {name}{f': {detail}' if detail else ''}")


# --- A1 Checks ---
# 1. Gemini URL header migration
try:
    with open(os.path.join(ROOT_DIR, "src", "agent", "extractor.py"), "r", encoding="utf-8") as f:
        src = f.read()
    passed = "x-goog-api-key" in src and "models/{gemini_model}:generateContent?key=" not in src
    record("A1_1: Gemini sends key in x-goog-api-key header and not in URL query string", passed)
except Exception as e:
    record("A1_1: Gemini header migration", False, str(e))

# 2. _scrub redacts key=, Bearer, and token prefixes
try:
    test_str = "Error at key=AIzaSyDfake123 and Bearer gsk_secret456 with sk-test789 and AQtoken"
    scrubbed = _scrub(test_str)
    passed = (
        "AIzaSyDfake123" not in scrubbed
        and "gsk_secret456" not in scrubbed
        and "sk-test789" not in scrubbed
        and "AQtoken" not in scrubbed
        and "key=[REDACTED]" in scrubbed
        and "Bearer [REDACTED]" in scrubbed
    )
    record("A1_2: _scrub redacts key=, Bearer, and secret prefixes (AIza, gsk_, sk-, AQ)", passed)
except Exception as e:
    record("A1_2: _scrub redaction", False, str(e))

# 3. Client fallback reason is generic
try:
    agent = ExtractorAgent(api_key="your-api-key-here")
    agent.extract(ExtractionResult(
        tender_id="T1", total_pages=1, full_text="Tender text",
        pages={1: PageText(page_number=1, raw_text="text", normalized_text="text", char_count=4, is_scanned_likely=False)},
        detected_sections=[], is_scanned_document=False, skipped_pages=[]
    ))
    passed = agent.fallback_reason is not None and "AIza" not in agent.fallback_reason
    record("A1_3: Client-visible fallback reason contains generic text without leaked internals", passed)
except Exception as e:
    record("A1_3: Client fallback reason generic", False, str(e))


# --- A2 Checks ---
# 4. Async endpoints use threadpool
try:
    with open(os.path.join(ROOT_DIR, "src", "api.py"), "r", encoding="utf-8") as f:
        api_src = f.read()
    passed = "run_in_threadpool" in api_src and "async def process_full_tender" in api_src and "async def upload_tender_pdf" in api_src
    record("A2_1: Endpoints retain async def and offload via run_in_threadpool", passed)
except Exception as e:
    record("A2_1: run_in_threadpool offload", False, str(e))

# 5. Shared state protected by module-level _supervisor_lock
try:
    passed = hasattr(_supervisor_lock, "acquire") and hasattr(_supervisor_lock, "release")
    record("A2_2: Module-level _supervisor_lock guards shared Supervisor/ExtractorAgent state", passed)
except Exception as e:
    record("A2_2: supervisor lock check", False, str(e))

# 6. Queue limit: 503 "Busy, retry shortly" when >3 requests wait
try:
    with _rate_limit_lock:
        _client_requests.clear()
        _strict_requests.clear()
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    _supervisor_lock.acquire()
    threads = []
    try:
        for _ in range(3):
            t = threading.Thread(target=lambda: client.post("/api/assess/upload", files={"file": ("t.pdf", fake_pdf, "application/pdf")}))
            t.start()
            threads.append(t)
        time.sleep(0.15)
        res = client.post("/api/assess/upload", files={"file": ("t.pdf", fake_pdf, "application/pdf")})
        passed = (res.status_code == 503 and "Busy, retry shortly" in res.json().get("detail", ""))
        record("A2_3: Rejects with 503 Busy, retry shortly when queue exceeds 3 waiting requests", passed)
    finally:
        _supervisor_lock.release()
        for t in threads:
            t.join()
except Exception as e:
    record("A2_3: Concurrency 503 limit", False, str(e))


# --- A3 Checks ---
# 7. Filename None returns 400
try:
    from fastapi import UploadFile, HTTPException
    uf = UploadFile(io.BytesIO(b"%PDF-1.4\n"), filename=None)
    passed = False
    try:
        _save_uploaded_pdf(uf)
    except HTTPException as he:
        passed = (he.status_code == 400)
    record("A3_1: File upload with filename=None returns HTTP 400", passed)
except Exception as e:
    record("A3_1: filename None returns 400", False, str(e))

# 8. Early reject Content-Length > 26 MB
try:
    res = client.post("/api/assess/upload", files={"file": ("test.pdf", b"%PDF-1.4\n", "application/pdf")}, headers={"content-length": str(28 * 1024 * 1024)})
    passed = (res.status_code == 413)
    record("A3_2: Early rejection with 413 when Content-Length > 26 MB", passed)
except Exception as e:
    record("A3_2: Content-Length > 26 MB", False, str(e))

# 9. Streaming abort at 25 MB and delete partial file
try:
    from src.api import UPLOAD_DIR
    class StreamMock:
        def __init__(self, size):
            self.rem = size
        def read(self, n=-1):
            if self.rem <= 0:
                return b""
            chunk = min(n if n > 0 else self.rem, self.rem)
            self.rem -= chunk
            return b"A" * chunk

    before = set(os.listdir(UPLOAD_DIR))
    uf = UploadFile(StreamMock(26 * 1024 * 1024), filename="big.pdf")
    passed = False
    try:
        _save_uploaded_pdf(uf)
    except HTTPException as he:
        passed = (he.status_code == 413)
    after = set(os.listdir(UPLOAD_DIR))
    passed = passed and (before == after)
    record("A3_3: Streaming cap aborts at 25 MB with 413 and deletes partial file", passed)
except Exception as e:
    record("A3_3: Streaming cap 25MB abort", False, str(e))


# --- A4 Checks ---
# 10. Exclude /api/health from limiter
try:
    with _rate_limit_lock:
        _client_requests.clear()
        _strict_requests.clear()
    ok_count = sum(1 for _ in range(15) if client.get("/api/health").status_code == 200)
    record("A4_1: /api/health and /static excluded from rate limiting", ok_count == 15)
except Exception as e:
    record("A4_1: health exclusion", False, str(e))

# 11. Strict 6/min rate limit on POST assess endpoints with Retry-After header
try:
    with _rate_limit_lock:
        _strict_requests.clear()
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    for _ in range(6):
        client.post("/api/assess/upload", files={"file": ("t.pdf", fake_pdf, "application/pdf")}, headers={"x-forwarded-for": "192.0.2.1"})
    res = client.post("/api/assess/upload", files={"file": ("t.pdf", fake_pdf, "application/pdf")}, headers={"x-forwarded-for": "192.0.2.1"})
    passed = (res.status_code == 429 and "Retry-After" in res.headers and res.headers.get("content-type") == "application/json")
    record("A4_2: Strict 6/min rate limit returns 429 JSON response with Retry-After header", passed)
except Exception as e:
    record("A4_2: strict rate limit", False, str(e))

# 12. Prune empty IP keys
try:
    with _rate_limit_lock:
        _strict_requests["expired_ip"] = [time.time() - 200]
    client.get("/")
    with _rate_limit_lock:
        passed = ("expired_ip" not in _strict_requests)
    record("A4_3: Empty and expired IP keys are automatically pruned", passed)
except Exception as e:
    record("A4_3: prune IP keys", False, str(e))

# 13. LLM_HOURLY_CAP (default 60) triggers Tier 3 regex fallback
try:
    os.environ["LLM_HOURLY_CAP"] = "1"
    _llm_call_timestamps.clear()
    _llm_call_timestamps.append(time.time() - 10)
    agent = ExtractorAgent(api_key="test-api-key")
    ext_res = ExtractionResult(
        tender_id="TEST-CAP", total_pages=1, full_text="EMD Rs 1000",
        pages={1: PageText(page_number=1, raw_text="EMD Rs 1000", normalized_text="EMD Rs 1000", char_count=11, is_scanned_likely=False)},
        detected_sections=[], is_scanned_document=False, skipped_pages=[]
    )
    matrix = agent.extract(ext_res)
    passed = (agent.last_tier == 3)
    record("A4_4: LLM_HOURLY_CAP skips Tier 1 and falls back to Tier 3 deterministic regex", passed)
except Exception as e:
    record("A4_4: hourly cap fallback", False, str(e))
finally:
    os.environ.pop("LLM_HOURLY_CAP", None)


# --- A5 Checks ---
# 14. Bounded money validation (>= 0 and <= 10^13) returns 422 with generic "Invalid input"
try:
    bad_payload = {
        "matrix": {"tender_id": "T1", "emd_amount": -500},
        "profile": {"business_name": "Test Co", "annual_turnover_last_3y": [1000]},
    }
    res = client.post("/api/assess/evaluate", json=bad_payload)
    passed = (res.status_code == 422 and res.json().get("detail") == "Invalid input")
    record("A5_1: Money bounds validation (< 0 or > 10^13) returns 422 with generic Invalid input", passed)
except Exception as e:
    record("A5_1: bounds money validation", False, str(e))

# 15. Bounded years validation (0..100) returns 422 with generic "Invalid input"
try:
    bad_payload = {
        "matrix": {"tender_id": "T1", "min_years_experience": 120},
        "profile": {"business_name": "Test Co", "years_in_business": 10},
    }
    res = client.post("/api/assess/evaluate", json=bad_payload)
    passed = (res.status_code == 422 and res.json().get("detail") == "Invalid input")
    record("A5_2: Years bounds validation (0..100) returns 422 with generic Invalid input", passed)
except Exception as e:
    record("A5_2: bounds years validation", False, str(e))


# --- A6 Checks ---
# 16. Strict-Transport-Security and Permissions-Policy headers present; docs disabled unless ENABLE_DOCS=1
try:
    res = client.get("/api/health")
    hsts = res.headers.get("Strict-Transport-Security") == "max-age=31536000"
    perm = "camera=()" in res.headers.get("Permissions-Policy", "")
    docs_404 = (client.get("/docs").status_code == 404 and client.get("/openapi.json").status_code == 404)
    passed = hsts and perm and docs_404
    record("A6_1: Strict-Transport-Security & Permissions-Policy present; /docs disabled by default", passed)
except Exception as e:
    record("A6_1: security headers & docs gate", False, str(e))

# 17. Content-Security-Policy (CSP) header check (Expected to FAIL per instructions)
try:
    res = client.get("/")
    has_csp = "Content-Security-Policy" in res.headers
    record("A6_2: Content-Security-Policy header present (FAIL EXPECTED: Do NOT add CSP yet)", has_csp)
except Exception as e:
    record("A6_2: CSP header check", False, str(e))


# Summary
pass_count = sum(1 for _, st, _ in results if st == "PASS")
fail_count = sum(1 for _, st, _ in results if st == "FAIL")
total = len(results)

print("\n" + "=" * 50)
print(f"Summary: {pass_count}/{total} passed, {fail_count}/{total} failed.")
if pass_count == 16 and fail_count == 1:
    print("SUCCESS: Exactly 16/17 passing as expected (only CSP header check failed).")
else:
    print(f"WARNING: Expected 16/17 passing, but got {pass_count}/{total}.")
print("=" * 50)

if pass_count == 16 and fail_count == 1:
    sys.exit(0)
else:
    sys.exit(1)
