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
