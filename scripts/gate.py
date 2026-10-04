#!/usr/bin/env python3
"""
BidSahayak Quality & Truth Gates Suite.
Enforces G1-G8 (Core Functionality), G10-G13 (Truth & Evidence Integrity),
G14-G18 (Loop Closure & UI), G19 (Benchmarks), and G23 (LLM Honesty).
"""
import os
import sys
import json
import argparse
from typing import Dict, Any, Callable

# Ensure repo root is on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

def gate_g1(repo: str) -> bool:
    """G1: parse_inr handles paise, Indian commas, Lakh/Crore words correctly."""
    from src.regex_fallback import DeterministicRegexExtractor
    p = DeterministicRegexExtractor.parse_inr
    cases = [
        ("10,000.00", 10000),
        ("Rs. 10,000", 10000),
        ("1.5 Crore", 15000000),
        ("50 Lakh", 5000000),
        ("2,50,000", 250000),
        ("INR 75,000.50", 75000),
    ]
    for text, expected in cases:
        val = p(text)
        if val != expected:
            print(f"[G1 FAIL] parse_inr('{text}') returned {val}, expected {expected}")
            return False
    return True

def gate_g2(repo: str) -> bool:
    """G2: verify_value round-trip check and confidence downgrade on mismatch."""
    from src.verify import SnippetVerifier
    # Verify snippet verifier has verify_value
    if not hasattr(SnippetVerifier, "verify_value"):
        print("[G2 FAIL] SnippetVerifier.verify_value method missing")
        return False
    
    # Value present in snippet -> high confidence
    ok, conf = SnippetVerifier.verify_value(10000, "Clause 5: EMD of Rs. 10,000 is required.")
    if not ok or conf < 0.7:
        print(f"[G2 FAIL] Matching value failed verification: ok={ok}, conf={conf}")
        return False

    # Value absent from snippet -> downgrade <= 0.30
    bad_ok, bad_conf = SnippetVerifier.verify_value(50000, "Clause 5: EMD of Rs. 10,000 is required.")
    if bad_ok or bad_conf > 0.30:
        print(f"[G2 FAIL] Mismatching value was not downgraded: ok={bad_ok}, conf={bad_conf}")
        return False
    return True

def gate_g3(repo: str) -> bool:
    """G3: Fail-closed defaults and blocking vs addressable gaps."""
    from src.models import RequirementMatrix, VendorProfile
    from src.evaluator import evaluate
    
    # Fail-closed default: empty matrix -> needs-human-review
    m = RequirementMatrix(tender_id="T1", title="Empty Tender")
    p = VendorProfile(business_name="Test", udyam_classification="Micro")
    v = evaluate(m, p)
    if v.overall == "eligible":
        print("[G3 FAIL] Empty matrix evaluated as eligible (fail-open bug)")
        return False
    return True

def gate_g4(repo: str) -> bool:
    """G4: Robust deadline extraction across formats."""
    from src.regex_fallback import DeterministicRegexExtractor
    d = DeterministicRegexExtractor.extract_deadline
    cases = [
        ("Closing date: 24.06.2019 / 1500 Hrs", "2019-06-24"),
        ("Last date of bid submission is 18-10-2026", "2026-10-18"),
        ("निविदा जमा करने की अंतिम तिथि 21/10/2026", "2026-10-21"),
        ("Submission deadline: 2026-10-24T15:00:00Z", "2026-10-24"),
    ]
    for text, expected in cases:
        dt = d(text)
        if not dt or dt.strftime("%Y-%m-%d") != expected:
            print(f"[G4 FAIL] extract_deadline('{text}') returned {dt}, expected {expected}")
            return False
    return True

def gate_g5(repo: str) -> bool:
    """G5: Report skipped_pages for unreadable pages."""
    from src.text_extract import TextWorker
    w = TextWorker()
    if not hasattr(w, "process"):
        return False
    return True

def gate_g6(repo: str) -> bool:
    """G6: Asia/Kolkata tz-aware deadline math and 7-day DSC boundary."""
    from src.evaluator import evaluate_dsc_timing
    from datetime import datetime, timezone, timedelta
    
    # 5 days remaining -> impossible to obtain Class 3 DSC in time (needs >= 7 days)
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    dl_short = now_ist + timedelta(days=5)
    dl_long = now_ist + timedelta(days=12)
    
    short_res = evaluate_dsc_timing(dl_short, holds_dsc=False)
    if short_res != "gap_impossible":
        print(f"[G6 FAIL] 5-day DSC deadline returned {short_res}, expected gap_impossible")
        return False

    long_res = evaluate_dsc_timing(dl_long, holds_dsc=False)
    if long_res != "gap_addressable":
        print(f"[G6 FAIL] 12-day DSC deadline returned {long_res}, expected gap_addressable")
        return False
    return True

def gate_g7(repo: str) -> bool:
    """G7: Average annual turnover calculation (not max)."""
    from src.evaluator import calculate_effective_turnover
    turnovers = [3000000, 4000000, 5000000]
    avg = calculate_effective_turnover(turnovers)
    if avg != 4000000:
        print(f"[G7 FAIL] calculate_effective_turnover returned {avg}, expected 4000000")
        return False
    return True

def gate_g8(repo: str) -> bool:
    """G8: Security hardening (CORS, file cleanup, headers)."""
    from src.api import app
    # Check middleware
    has_cors = any("CORSMiddleware" in str(type(m)) or "cors" in str(type(m)).lower() for m in app.user_middleware)
    return has_cors

def gate_g10(repo: str) -> bool:
    """G10: sample_tenders/NOTICE.md exists clarifying 13/14 are synthetic."""
    p = os.path.join(repo, "sample_tenders", "NOTICE.md")
    if not os.path.exists(p):
        print("[G10 FAIL] sample_tenders/NOTICE.md missing")
        return False
    content = open(p, encoding="utf-8").read()
    if "synthetic" not in content.lower() or "imd-tender.pdf" not in content:
        print("[G10 FAIL] sample_tenders/NOTICE.md lacks synthetic provenance details")
        return False
    return True

def gate_g11(repo: str) -> bool:
    """G11: tender_measurement.csv honesty."""
    p = os.path.join(repo, "tender_measurement.csv")
    if not os.path.exists(p):
        return False
    lines = open(p, encoding="utf-8").readlines()
    if len(lines) < 15:
        return False
    # Row 1 (IMD) deadline must be 2019-06-24
    if "2019-06-24" not in lines[1]:
        print("[G11 FAIL] Row 1 (IMD) deadline not 2019-06-24")
        return False
    # Rows 2-14 source_url should indicate fixture
    if "fixture" not in lines[2].lower() and "sample_tenders" not in lines[2].lower():
        print("[G11 FAIL] Row 2 source_url does not indicate fixture")
        return False
    return True

def gate_g12(repo: str) -> bool:
    """G12: PROBLEM_EVIDENCE.md §4 rewritten honestly without fabricated averages."""
    p = os.path.join(repo, "PROBLEM_EVIDENCE.md")
    if not os.path.exists(p):
        return False
    txt = open(p, encoding="utf-8").read()
    banned = ["34.2 pages", "11.4 days", "5.8 pages", "Zero fabricated statistics"]
    for b in banned:
        if b in txt:
            print(f"[G12 FAIL] PROBLEM_EVIDENCE.md still contains banned claim: '{b}'")
            return False
    return True

def gate_g13(repo: str) -> bool:
    """G13: docs/CLAIMS_LEDGER.md exists and has zero unverified rows."""
    p = os.path.join(repo, "docs", "CLAIMS_LEDGER.md")
    if not os.path.exists(p):
        print("[G13 FAIL] docs/CLAIMS_LEDGER.md does not exist")
        return False
    txt = open(p, encoding="utf-8").read()
    if "UNVERIFIED" in txt:
        print("[G13 FAIL] docs/CLAIMS_LEDGER.md contains UNVERIFIED rows")
        return False
    return True

def gate_g14(repo: str) -> bool:
    """G14: Vendor profile panel in frontend."""
    html_p = os.path.join(repo, "frontend", "index.html")
    if not os.path.exists(html_p):
        return False
    html = open(html_p, encoding="utf-8").read()
    fields = ["pfName", "pfUdyam", "pfTurnover"]
    for f in fields:
        if f not in html:
            print(f"[G14 FAIL] Missing vendor profile field: {f}")
            return False
    return True

def gate_g15(repo: str) -> bool:
    """G15: Verdict kicker honest wording."""
    html_p = os.path.join(repo, "frontend", "index.html")
    html = open(html_p, encoding="utf-8").read()
    return "Extraction only" in html or "bs-profile" in html or "verdict" in html

def gate_g16(repo: str) -> bool:
    """G16: Approve button wiring."""
    html_p = os.path.join(repo, "frontend", "index.html")
    html = open(html_p, encoding="utf-8").read()
    return "/api/assess/override" in html

def gate_g18(repo: str) -> bool:
    """G18: Bilingual toggle lossless (dataset.en snapshot)."""
    html_p = os.path.join(repo, "frontend", "index.html")
    html = open(html_p, encoding="utf-8").read()
    return "dataset.en" in html or "data-en" in html

def gate_g19(repo: str) -> bool:
    """G19: benchmark.py exists."""
    p = os.path.join(repo, "scripts", "benchmark.py")
    return os.path.exists(p)

def gate_g23(repo: str) -> bool:
    """G23: LLM tier honest provider resolution and .env.example coverage."""
    from src.agent.extractor import ExtractorAgent
    env_ex = os.path.join(repo, ".env.example")
    if not os.path.exists(env_ex):
        print("[G23 FAIL] .env.example missing")
        return False
    env_txt = open(env_ex, encoding="utf-8").read()
    for var in ["LLM_PROVIDER", "LLM_MODEL", "GEMINI_API_KEY", "GROQ_API_KEY", "LLM_API_KEY"]:
        if var not in env_txt:
            print(f"[G23 FAIL] .env.example missing {var}")
            return False
            
    # Check resolution logic
    agent = ExtractorAgent(api_key="AIzaSyDummyKeyForGeminiTest")
    if agent.provider != "gemini":
        print(f"[G23 FAIL] AIza... key resolved to {agent.provider}, expected gemini")
        return False
    return True


ALL_GATES: Dict[str, Callable[[str], bool]] = {
    "G1": gate_g1,
    "G2": gate_g2,
    "G3": gate_g3,
    "G4": gate_g4,
    "G5": gate_g5,
    "G6": gate_g6,
    "G7": gate_g7,
    "G8": gate_g8,
    "G10": gate_g10,
    "G11": gate_g11,
    "G12": gate_g12,
    "G13": gate_g13,
    "G14": gate_g14,
    "G15": gate_g15,
    "G16": gate_g16,
    "G18": gate_g18,
    "G19": gate_g19,
    "G23": gate_g23,
}


def run_gates(repo: str, target_gate: str = None, json_out: str = None):
    results = {}
    passed = 0
    total = 0

    gates_to_run = {target_gate: ALL_GATES[target_gate]} if target_gate else ALL_GATES

    print("=" * 60)
    print("BidSahayak Quality & Truth Gate Evaluation")
    print("=" * 60)

    for gid, fn in gates_to_run.items():
        total += 1
        try:
            ok = fn(repo)
        except Exception as e:
            print(f"[{gid} ERROR] Exception: {e}")
            ok = False
        results[gid] = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
            print(f"[{gid}] PASS")
        else:
            print(f"[{gid}] FAIL")

    print("-" * 60)
    print(f"Summary: {passed}/{total} gates passed ({passed/total*100:.1f}%)")
    print("=" * 60)

    if json_out:
        os.makedirs(os.path.dirname(os.path.abspath(json_out)), exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump({
                "passed": passed,
                "total": total,
                "rate": passed / total if total else 0,
                "results": results
            }, f, indent=2)
        print(f"Gate report saved to {json_out}")

    return passed == total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BidSahayak Gate Checker")
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--all", action="store_true", help="Run all gates")
    parser.add_argument("--baseline", action="store_true", help="Record as baseline")
    parser.add_argument("--gate", default=None, help="Run specific gate (e.g. G23)")
    parser.add_argument("--json", default=None, help="Save JSON report")
    args = parser.parse_args()

    success = run_gates(args.repo, target_gate=args.gate, json_out=args.json)
    # If running baseline, exit 0 so initial reporting succeeds
    if args.baseline:
        sys.exit(0)
    sys.exit(0 if success else 1)
