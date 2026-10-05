from fastapi.testclient import TestClient
from src.api import app
import os

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "BidSahayak"


def test_root_serves_frontend():
    res = client.get("/")
    assert res.status_code == 200
    assert "BidSahayak" in res.text


def test_evaluate_endpoint():
    matrix = {
        "tender_id": "TEST-01",
        "title": "Solar Installation",
        "issuing_department": "UPNEDA",
        "emd_amount": 10000,
        "emd_exempt_categories": ["micro", "small"],
        "min_turnover": 1000000,
    }
    profile = {
        "business_name": "Agrawal Electricals",
        "udyam_classification": "Micro",
        "annual_turnover_last_3y": [1200000],
        "is_manufacturing": True,
        "is_trading": False,
    }
    res = client.post("/api/assess/evaluate", json={"matrix": matrix, "profile": profile})
    assert res.status_code == 200
    data = res.json()
    assert data["overall"] == "eligible"
    assert len(data["gaps"]) == 0


def test_override_endpoint():
    matrix = {
        "tender_id": "TEST-02",
        "title": "Road Repair",
        "issuing_department": "PWD UP",
        "min_turnover": 5000000,  # 50 Lakhs
    }
    profile = {
        "business_name": "Agrawal Electricals",
        "annual_turnover_last_3y": [2000000],  # 20L -> initially gap!
    }
    # Initial evaluate -> not-eligible
    res = client.post("/api/assess/evaluate", json={"matrix": matrix, "profile": profile})
    assert res.json()["overall"] == "not-eligible"

    # Human override: corrigendum lowered turnover to 15L
    override_payload = {
        "matrix": matrix,
        "profile": profile,
        "field_name": "min_turnover",
        "new_value": 1500000,
        "operator_note": "Corrigendum-1 reduced turnover requirement to 15 Lakhs",
    }
    res_override = client.post("/api/assess/override", json=override_payload)
    assert res_override.status_code == 200
    data_override = res_override.json()
    assert data_override["overall"] == "eligible"
    assert any(a["action"] == "human_override" for a in data_override["audit_log"])


def test_override_clears_unresolved_field():
    matrix = {
        "tender_id": "TND-UNRES-01",
        "title": "Unresolved Tender",
        "min_turnover": None,
        "unresolved_fields": ["min_turnover", "submission_deadline"],
    }
    profile = {
        "business_name": "Agrawal Electricals",
        "annual_turnover_last_3y": [2000000],
    }
    override_payload = {
        "matrix": matrix,
        "profile": profile,
        "field_name": "min_turnover",
        "new_value": 1500000,
        "operator_note": "Manual input of minimum turnover",
    }
    res_override = client.post("/api/assess/override", json=override_payload)
    assert res_override.status_code == 200
    data = res_override.json()
    # Check that min_turnover is no longer listed as unresolved in the evaluated matrix
    for section in data.get("sections", []):
        if section.get("section_id") == 1:
            assert "min_turnover" not in section.get("details", "")


def test_approve_records_audit_without_mutating_or_fabricating_evidence():
    matrix = {
        "tender_id": "TND-APPROVE-01",
        "title": "Solar Installation",
        "issuing_department": "UPNEDA",
        "emd_amount": 10000,
        "evidence_fields": {
            "emd_amount": {
                "field_name": "emd_amount",
                "value_raw": "₹10,000",
                "value_normalised": 10000,
                "confidence": 0.95,
                "source_page": 2,
                "source_snippet": "EMD is ₹10,000",
            }
        },
    }
    profile = {
        "business_name": "Agrawal Electricals",
        "udyam_classification": "Micro",
        "annual_turnover_last_3y": [1200000],
    }
    approve_payload = {
        "matrix": matrix,
        "profile": profile,
        "field_name": "Earnest Money Deposit (EMD)",
        "operator_note": "Approved by human operator",
    }
    res = client.post("/api/assess/override", json=approve_payload)
    assert res.status_code == 200
    data = res.json()
    # Check audit log entry has human_approval
    assert any(a["action"] == "human_approval" and a["field"] == "Earnest Money Deposit (EMD)" for a in data["audit_log"])
    # Matrix evidence should not contain junk key or fabricated "Operator manual input: None"
    assert "Earnest Money Deposit (EMD)" not in matrix.get("evidence_fields", {})
    for ev in matrix.get("evidence_fields", {}).values():
        assert "Operator manual input: None" not in ev.get("source_snippet", "")


def test_upload_and_process_file():
    pdf_path = os.path.join("sample_tenders", "imd-tender.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            res = client.post("/api/assess/process", files={"file": ("imd-tender.pdf", f, "application/pdf")})
        assert res.status_code == 200
        data = res.json()
        assert "session_id" in data
        assert "trace" in data
        assert len(data["trace"]) >= 3


def test_security_path_traversal_and_magic_bytes():
    # 1. Path traversal attempt must not escape UPLOAD_DIR
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    res = client.post(
        "/api/assess/upload",
        files={"file": ("../../malicious_traversal.pdf", fake_pdf, "application/pdf")}
    )
    # Must succeed in saving safely inside UPLOAD_DIR (or reject) without creating file in root
    assert not os.path.exists("malicious_traversal.pdf")
    assert not os.path.exists("../../malicious_traversal.pdf")

    # 2. Non-PDF magic bytes must be rejected with 400
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00"
    res_fake = client.post(
        "/api/assess/upload",
        files={"file": ("fake.pdf", fake_exe, "application/pdf")}
    )
    assert res_fake.status_code == 400
    assert "missing valid PDF header" in res_fake.json()["detail"]


def test_concurrency_lock_and_queue_limit():
    import threading
    import time
    from src.api import _supervisor_lock

    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    _supervisor_lock.acquire()
    threads = []
    try:
        for _ in range(3):
            t = threading.Thread(
                target=lambda: client.post(
                    "/api/assess/upload",
                    files={"file": ("test.pdf", fake_pdf, "application/pdf")},
                )
            )
            t.start()
            threads.append(t)

        time.sleep(0.15)

        res = client.post(
            "/api/assess/upload",
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        )
        assert res.status_code == 503
        assert "Busy, retry shortly" in res.json()["detail"]
    finally:
        _supervisor_lock.release()
        for t in threads:
            t.join()


def test_upload_filename_none_returns_400():
    from fastapi import UploadFile, HTTPException
    import io
    import pytest
    from src.api import _save_uploaded_pdf

    uf = UploadFile(io.BytesIO(b"%PDF-1.4\n"), filename=None)
    with pytest.raises(HTTPException) as exc:
        _save_uploaded_pdf(uf)
    assert exc.value.status_code == 400
    assert "Filename missing" in exc.value.detail


def test_upload_content_length_exceeds_26mb_rejected_early():
    res = client.post(
        "/api/assess/upload",
        files={"file": ("test.pdf", b"%PDF-1.4\n", "application/pdf")},
        headers={"content-length": str(27 * 1024 * 1024)},
    )
    assert res.status_code == 413


def test_upload_streaming_cap_25mb_aborts_and_deletes_partial():
    from fastapi import UploadFile, HTTPException
    import pytest
    from src.api import _save_uploaded_pdf, UPLOAD_DIR

    class HugeChunkReader:
        def __init__(self, total_size):
            self.remaining = total_size

        def read(self, size=-1):
            if self.remaining <= 0:
                return b""
            chunk_len = min(size if size > 0 else self.remaining, self.remaining)
            self.remaining -= chunk_len
            return b"A" * chunk_len

    uf = UploadFile(HugeChunkReader(26 * 1024 * 1024), filename="huge.pdf")
    before_files = set(os.listdir(UPLOAD_DIR))
    with pytest.raises(HTTPException) as exc:
        _save_uploaded_pdf(uf)
    assert exc.value.status_code == 413
    after_files = set(os.listdir(UPLOAD_DIR))
    assert before_files == after_files
