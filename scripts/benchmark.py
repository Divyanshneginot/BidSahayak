#!/usr/bin/env python3
"""
BidSahayak Extraction Benchmark Suite.
Measures field-by-field accuracy (EMD, deadline, turnover, exemption)
and latency (p50, p95) across all 14 tender documents against ground truth.
"""
import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingest import IngestWorker
from src.text_extract import TextWorker
from src.agent.extractor import ExtractorAgent
from src.evaluator import evaluate
from src.models import VendorProfile


def run_benchmark(repo_root: str, no_llm: bool = False, md_path: str = None):
    print("=" * 70)
    tier_label = "Tier 3 (Deterministic Regex Fallback)" if no_llm else "Tier 1/2 (Agentic LLM Extraction)"
    print(f"BidSahayak Benchmark — {tier_label}")
    print("=" * 70)

    gt_path = os.path.join(repo_root, "assets", "ground_truth.json")
    if not os.path.exists(gt_path):
        print(f"[ERROR] Ground truth not found at {gt_path}")
        return False

    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth: Dict[str, Any] = json.load(f)

    sample_dir = os.path.join(repo_root, "sample_tenders")
    if not os.path.exists(sample_dir):
        print(f"[ERROR] sample_tenders/ not found at {sample_dir}")
        return False

    files = sorted([f for f in os.listdir(sample_dir) if f.endswith(".pdf")])
    if not files:
        print("[ERROR] No PDF files in sample_tenders/")
        return False

    ingest_worker = IngestWorker()
    text_worker = TextWorker()
    
    # Configure extractor
    if no_llm:
        extractor = ExtractorAgent(api_key="none-deterministic")
        extractor.api_key = None
    else:
        extractor = ExtractorAgent()

    test_profile = VendorProfile(
        business_name="Test Enterprise",
        udyam_classification="Micro",
        is_manufacturing=True,
        is_trading=False,
        annual_turnover_last_3y=[2000000],
        holds_class3_dsc=True,
    )

    results = []
    latencies = []
    emd_matches = 0
    deadline_matches = 0
    turnover_matches = 0
    exemption_matches = 0

    for pdf_name in files:
        pdf_path = os.path.join(sample_dir, pdf_name)
        gt = ground_truth.get(pdf_name, {})

        t0 = time.time()
        ingest_res = ingest_worker.process(pdf_path)
        if not ingest_res.is_valid:
            latencies.append(time.time() - t0)
            results.append({
                "doc": pdf_name,
                "status": "INVALID",
                "emd_match": False,
                "deadline_match": False,
                "turnover_match": False,
                "exempt_match": False,
                "time_sec": latencies[-1]
            })
            continue

        text_res = text_worker.process(pdf_path, tender_id=ingest_res.tender_id)
        matrix = extractor.extract(text_res)
        verdict = evaluate(matrix, test_profile)
        elapsed = time.time() - t0
        latencies.append(elapsed)

        # Field comparisons
        # 1. EMD
        expected_emd = gt.get("emd_amount")
        actual_emd = matrix.emd_amount
        emd_ok = (actual_emd == expected_emd) if expected_emd is not None else (actual_emd is None or actual_emd == 0)
        if emd_ok:
            emd_matches += 1

        # 2. Deadline
        expected_dl = gt.get("deadline_date")
        actual_dl = matrix.submission_deadline.strftime("%Y-%m-%d") if matrix.submission_deadline else None
        dl_ok = (actual_dl == expected_dl) if expected_dl else (actual_dl is None)
        if dl_ok:
            deadline_matches += 1

        # 3. Turnover
        expected_to = gt.get("min_turnover")
        actual_to = matrix.min_turnover
        to_ok = (actual_to == expected_to) if expected_to is not None else (actual_to is None or actual_to == 0)
        if to_ok:
            turnover_matches += 1

        # 4. Exemption
        expected_ex = gt.get("emd_exempt_for_mse", True)
        actual_ex = bool(matrix.emd_exempt_categories and any(c.lower() in ["micro", "small", "mse", "msme"] for c in matrix.emd_exempt_categories))
        ex_ok = (actual_ex == expected_ex)
        if ex_ok:
            exemption_matches += 1

        results.append({
            "doc": pdf_name,
            "status": verdict.overall,
            "emd_match": emd_ok,
            "deadline_match": dl_ok,
            "turnover_match": to_ok,
            "exempt_match": ex_ok,
            "time_sec": elapsed,
            "actual_emd": actual_emd,
            "actual_dl": actual_dl
        })

    # Metrics
    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.50)] if n else 0.0
    p95 = latencies[min(int(n * 0.95), n - 1)] if n else 0.0

    print(f"Documents Evaluated: {n}/{len(files)}")
    print(f"EMD Match:           {emd_matches}/{n} ({emd_matches/n*100:.1f}%)")
    print(f"Deadline Match:      {deadline_matches}/{n} ({deadline_matches/n*100:.1f}%)")
    print(f"Turnover Match:      {turnover_matches}/{n} ({turnover_matches/n*100:.1f}%)")
    print(f"Exemption Match:     {exemption_matches}/{n} ({exemption_matches/n*100:.1f}%)")
    print(f"Latency:             p50={p50*1000:.1f}ms, p95={p95*1000:.1f}ms")
    print("-" * 70)

    # Output Markdown if requested
    if md_path:
        os.makedirs(os.path.dirname(os.path.abspath(md_path)), exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# BidSahayak Benchmark — {tier_label}\n\n")
            f.write(f"- **Evaluated**: {n} documents\n")
            f.write(f"- **EMD Recovery**: {emd_matches}/{n} ({emd_matches/n*100:.1f}%)\n")
            f.write(f"- **Deadline Accuracy**: {deadline_matches}/{n} ({deadline_matches/n*100:.1f}%)\n")
            f.write(f"- **Turnover Accuracy**: {turnover_matches}/{n} ({turnover_matches/n*100:.1f}%)\n")
            f.write(f"- **Exemption Detection**: {exemption_matches}/{n} ({exemption_matches/n*100:.1f}%)\n")
            f.write(f"- **Latency**: p50 = {p50*1000:.1f} ms · p95 = {p95*1000:.1f} ms\n\n")
            f.write("| Document | EMD OK | Deadline OK | Turnover OK | Exemption OK | Time (s) |\n")
            f.write("|---|---|---|---|---|---|\n")
            for r in results:
                f.write(f"| `{r['doc']}` | {'✓' if r['emd_match'] else '✗'} | {'✓' if r['deadline_match'] else '✗'} | {'✓' if r['turnover_match'] else '✗'} | {'✓' if r['exempt_match'] else '✗'} | {r['time_sec']:.2f}s |\n")
        print(f"Written benchmark report to {md_path}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BidSahayak Benchmark Suite")
    parser.add_argument("--repo", default=".", help="Repository root path")
    parser.add_argument("--no-llm", action="store_true", help="Force Tier 3 deterministic mode")
    parser.add_argument("--md", default=None, help="Path to write markdown output")
    args = parser.parse_args()

    ok = run_benchmark(args.repo, no_llm=args.no_llm, md_path=args.md)
    sys.exit(0 if ok else 1)
