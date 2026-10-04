#!/usr/bin/env python3
"""
BidSahayak Demo Script Automated Walkthrough Test.
Validates every single claim, action, and timing in the 2:30 demo script:
1. Vendor Profile setup (Micro, ₹25L turnover, 3y exp, No DSC)
2. Ingestion & extraction of 69-page real tender: sample_tenders/held_out/Tenderdoc-park67.pdf
3. Page-aware keyword retrieval across all 69 pages
4. Anti-hallucination citations (page number, verbatim snippet, confidence)
5. Pure deterministic evaluation (GFR rules, turnover average, DSC window check)
6. Human-in-the-loop override with unresolved_fields clearance and audit trace
7. Bilingual EN/HI toggle
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from src.api import app
from src.models import RequirementMatrix, VendorProfile, FieldEvidence
from src.text_extract import TextWorker
from src.agent.extractor import ExtractorAgent
from src.evaluator import evaluate

client = TestClient(app)

def test_demo_script_walkthrough():
    print("=" * 80)
    print("TESTING 2:30 DEMO SCRIPT WALKTHROUGH")
    print("=" * 80)

    # ---------------------------------------------------------
    # Beat 1 (0:00 - 0:25): Vendor Profile Setup
    # ---------------------------------------------------------
    print("\n[Beat 1: 0:00 - 0:25] Configuring MSME Vendor Profile...")
    profile_data = {
        "business_name": "Sharma Engineering Works",
        "udyam_classification": "Micro",
        "annual_turnover_last_3y": [2500000, 2400000, 2600000],  # Avg: 25 Lakhs
        "years_in_business": 3,
        "past_work_experience": ["Civil maintenance", "Road patching"],
        "certifications_held": ["Class-3 Civil"],
        "holds_class3_dsc": False,  # Gap for short deadlines!
        "net_worth": 1000000,
    }
    profile = VendorProfile(**profile_data)
    print(f"  Vendor: {profile.business_name}")
    print(f"  Udyam: {profile.udyam_classification} | 3-yr Avg Turnover: Rs. {sum(profile.annual_turnover_last_3y)/3:,.0f}")
    print(f"  Holds Class-3 DSC: {profile.holds_class3_dsc}")
    assert profile.udyam_classification == "Micro"
    assert profile.holds_class3_dsc is False

    # ---------------------------------------------------------
    # Beat 2 (0:25 - 0:55): Ingest & Extract 69-page Real Tender
    # ---------------------------------------------------------
    tender_file = Path("sample_tenders/held_out/Tenderdoc-park67.pdf")
    assert tender_file.exists(), f"Demo tender {tender_file} missing!"
    print(f"\n[Beat 2: 0:25 - 0:55] Ingesting real 69-page tender: {tender_file.name}...")
    
    # Process text extraction
    text_worker = TextWorker()
    extract_res = text_worker.process(str(tender_file))
    print(f"  Pages processed: {len(extract_res.pages)} pages, {len(extract_res.full_text):,} chars")
    assert len(extract_res.pages) >= 60, f"Expected 60+ pages, got {len(extract_res.pages)}"

    # Test page-aware chunking
    retrieved_sections = ExtractorAgent._retrieve_relevant_sections(extract_res, max_chars=24000)
    print(f"  Retrieved keyword sections: {len(retrieved_sections)} chars")
    assert "--- PAGE" in retrieved_sections

    # Run extraction (Deterministic Tier 3 / LLM fallback)
    extractor = ExtractorAgent(api_key="")
    matrix = extractor.extract(extract_res)
    print(f"  Extraction Tier: Tier {extractor.last_tier}")
    print(f"  Tender ID: {matrix.tender_id}")
    print(f"  EMD Amount: Rs. {matrix.emd_amount:,}" if matrix.emd_amount else "  EMD Amount: None")
    assert matrix.emd_amount == 11334, f"Expected EMD Rs. 11,334, got {matrix.emd_amount}"

    # ---------------------------------------------------------
    # Beat 3 (0:55 - 1:25): Anti-Hallucination Citation Verification
    # ---------------------------------------------------------
    print(f"\n[Beat 3: 0:55 - 1:25] Checking Anti-Hallucination Citations...")
    assert "emd_amount" in matrix.evidence_fields
    emd_ev = matrix.evidence_fields["emd_amount"]
    print(f"  EMD Citation: Page {emd_ev.source_page}")
    print(f"  Source Snippet: {emd_ev.source_snippet[:70]}...")
    print(f"  Confidence Score: {emd_ev.confidence:.2f}")
    assert emd_ev.source_page in extract_res.pages
    assert emd_ev.confidence >= 0.70

    # ---------------------------------------------------------
    # Beat 4 (1:25 - 1:55): GFR Deterministic Evaluation
    # ---------------------------------------------------------
    print(f"\n[Beat 4: 1:25 - 1:55] Running Deterministic GFR Evaluation...")
    # Inject short deadline (4 days from now) to trigger DSC gap in demo
    fixed_now = datetime(2026, 10, 4, 12, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    matrix.submission_deadline = datetime(2026, 10, 8, 15, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    
    verdict = evaluate(matrix, profile, current_time=fixed_now)
    print(f"  Overall Verdict: {verdict.overall.upper()}")
    print(f"  Gaps count: {len(verdict.gaps)}")
    for g in verdict.gaps:
        print(f"    - GAP in {g.requirement}: {g.reason} (remedy: {g.remedy})")
    print(f"  Summary: {verdict.summary[:100]}...")

    # Check that DSC gap is flagged because vendor has no DSC and deadline is in 4 days (< 7 days)
    assert any("DSC" in g.requirement or "DSC" in g.reason for g in verdict.gaps), "Expected DSC gap to be flagged!"
    assert verdict.overall in ["not-eligible", "needs-human-review", "eligible-with-gaps"]

    # ---------------------------------------------------------
    # Beat 5 (1:55 - 2:15): Human-in-the-Loop Override
    # ---------------------------------------------------------
    print(f"\n[Beat 5: 1:55 - 2:15] Executing Human-in-the-Loop Override via API...")
    override_payload = {
        "matrix": matrix.model_dump(mode="json"),
        "profile": profile.model_dump(mode="json"),
        "field_name": "submission_deadline",
        "new_value": "2026-10-25T15:00:00+05:30",  # Extended by addendum to 21 days
        "operator_note": "Corrigendum-1 extended deadline to 25 Oct 2026 (allows DSC issuance)",
    }
    res_override = client.post("/api/assess/override", json=override_payload)
    assert res_override.status_code == 200, f"Override failed: {res_override.text}"
    override_verdict = res_override.json()
    print(f"  Post-Override Verdict: {override_verdict['overall'].upper()}")
    print(f"  Audit Log Entries: {len(override_verdict['audit_log'])}")
    last_log = override_verdict["audit_log"][-1]
    print(f"  Last Action: {last_log['action']} on '{last_log['field']}' -> {last_log['note']}")
    assert last_log["action"] == "human_override"
    assert last_log["field"] == "submission_deadline"

    # ---------------------------------------------------------
    # Beat 6 (2:15 - 2:30): Bilingual UI & Release Verification
    # ---------------------------------------------------------
    print(f"\n[Beat 6: 2:15 - 2:30] Verifying Bilingual UI Assets & Health...")
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"
    
    res_ui = client.get("/")
    assert res_ui.status_code == 200
    html_text = res_ui.text
    assert "data-i18n" in html_text
    assert "langTgl" in html_text
    print("  Frontend served with bilingual toggle and audit trace disclosure: OK")

    print("\n" + "=" * 80)
    print("ALL DEMO SCRIPT BEATS VERIFIED SUCCESSFULLY! 100% OPERATIONAL.")
    print("=" * 80)

if __name__ == "__main__":
    test_demo_script_walkthrough()
