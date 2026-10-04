#!/usr/bin/env python3
"""
BidSahayak reproducible extraction benchmark.

Replaces evals/run_evals.py, which printed hardcoded success and never compared anything.

It reads ground truth from assets/ground_truth.json (values read from the documents by hand),
runs the real pipeline over sample_tenders/*.pdf, and reports per-field accuracy plus every miss.

Usage
-----
  python scripts/benchmark.py --repo . --no-llm            # deterministic tier only (offline, free)
  python scripts/benchmark.py --repo .                     # adds the LLM tier if a key is configured
  python scripts/benchmark.py --repo . --json docs/BENCHMARK.json --md docs/BENCHMARK.md

Exit code: 0 if all field accuracies meet the thresholds below, 1 otherwise.
Ground truth is never derived from the pipeline under test.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

THRESHOLDS = {"emd": 0.90, "deadline": 0.80, "turnover": 0.70, "exemption": 0.90}
ESCAPE = "\033[0m"
OK, BAD, DIM = "\033[32m", "\033[31m", "\033[2m"

HERE = Path(__file__).resolve().parent


def find_gt(repo: Path, given: str | None) -> Path | None:
    cands = []
    if given:
        cands.append(Path(given))
    cands += [repo / "assets/ground_truth.json", repo / "scripts/assets/ground_truth.json",
              HERE / "../assets/ground_truth.json", HERE / "assets/ground_truth.json"]
    for c in cands:
        if c and Path(c).is_file():
            return Path(c).resolve()
    return None


def field_results(matrix, gt: dict) -> dict:
    """Compare an extracted matrix against ground truth. Fields listed in gt['ambiguous_fields']
    (documents that legitimately contain two competing values) are excluded from the tally and
    reported as 'AMB' — the correct system behaviour there is human review, not a guess."""
    """Compare one extracted RequirementMatrix against one ground-truth row."""
    exp_emd = gt.get("emd_amount_inr")
    got_emd = getattr(matrix, "emd_amount", None)
    emd_ok = (got_emd == exp_emd) if exp_emd is not None else (got_emd in (None, 0))

    exp_dl = gt.get("deadline_date")
    got_dl = getattr(matrix, "submission_deadline", None)
    got_dl_d = got_dl.date().isoformat() if hasattr(got_dl, "date") else None
    dl_ok = (got_dl_d == exp_dl) if exp_dl else (got_dl is None)

    exp_tv = gt.get("min_annual_turnover_inr")
    got_tv = getattr(matrix, "min_turnover", None)
    tv_ok = (got_tv == exp_tv) if exp_tv is not None else (got_tv in (None, 0))

    exp_ex = gt.get("emd_exempted_for_mse")
    cats = [c.lower() for c in (getattr(matrix, "emd_exempt_categories", None) or [])]
    got_ex = ("micro" in cats or "small" in cats) if exp_ex is not None else None
    ex_ok = (got_ex == bool(exp_ex)) if exp_ex is not None else True

    out = {
        "emd": (emd_ok, got_emd, exp_emd),
        "deadline": (dl_ok, got_dl_d, exp_dl),
        "turnover": (tv_ok, got_tv, exp_tv),
        "exemption": (ex_ok, got_ex, bool(exp_ex) if exp_ex is not None else None),
    }
    for f in gt.get("ambiguous_fields", []):
        key = {"emd_amount_inr": "emd", "deadline_date": "deadline",
               "min_annual_turnover_inr": "turnover", "emd_exempted_for_mse": "exemption"}.get(f)
        if key:
            out[key] = ("ambiguous", out[key][1], f"AMBIGUOUS — {gt.get('ambiguity_note', '')[:60]}")
    return out


def run(repo: Path, use_llm: bool, only: str | None) -> dict:
    sys.path.insert(0, str(repo))
    from src.ingest import IngestWorker            # noqa: E402
    from src.text_extract import TextWorker        # noqa: E402
    from src.agent.extractor import ExtractorAgent  # noqa: E402

    gt_path = find_gt(repo, only)
    if not gt_path:
        print("ground_truth.json not found — pass --gt <path>", file=sys.stderr)
        sys.exit(2)
    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    try:
        from dotenv import load_dotenv
        load_dotenv(repo / ".env")
        load_dotenv(repo.parent / ".env")
    except Exception:
        pass

    key = (os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")) if use_llm else ""
    extractor = ExtractorAgent(api_key=key)
    ingest, textw = IngestWorker(), TextWorker()

    rows, per_field = [], {k: [0, 0] for k in THRESHOLDS}
    started = time.time()
    for t in gt["tenders"]:
        pdf = repo / "sample_tenders" / t["file"]
        row = {"file": t["file"], "synthetic": t.get("synthetic", True), "run": False}
        if not pdf.is_file():
            row["error"] = "fixture missing"
            rows.append(row)
            continue
        t0 = time.time()
        try:
            ing = ingest.process(str(pdf))
            txt = textw.process(str(pdf), tender_id=ing.tender_id)
            matrix = extractor.extract(txt)
            res = field_results(matrix, t)
            row.update({
                "run": True,
                "tier": getattr(extractor, "last_tier", None),
                "fallback_reason": getattr(extractor, "fallback_reason", None),
                "latency_ms": round((time.time() - t0) * 1000),
                "fields": {k: {"ok": bool(v[0]), "got": v[1], "want": v[2]} for k, v in res.items()}
            })
            for k, v in res.items():
                if v[0] == "ambiguous":
                    continue
                per_field[k][1] += 1
                per_field[k][0] += 1 if v[0] else 0
        except Exception as e:
            row.update({"error": f"{type(e).__name__}: {e}"[:160]})
        rows.append(row)

    acc = {k: (v[0] / v[1] if v[1] else 0.0) for k, v in per_field.items()}
    lat = [r["latency_ms"] for r in rows if r.get("latency_ms")]
    lat.sort()
    summary = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S%z"),
        "repo": str(repo),
        "git_head": os.popen(f"git -C {repo} rev-parse --short HEAD").read().strip() or "n/a",
        "tier": ("llm+deterministic" if key else "deterministic (no API key)"),
        "n_documents": len(rows),
        "per_field": {k: {"correct": per_field[k][0], "of": per_field[k][1], "accuracy": round(acc[k], 3)}
                      for k in per_field},
        "latency_ms": {"p50": lat[len(lat) // 2] if lat else None, "p95": lat[int(len(lat) * 0.95) - 1] if lat else None},
        "thresholds": THRESHOLDS,
        "passed": all(acc[k] >= THRESHOLDS[k] for k in THRESHOLDS),
    }
    return {"summary": summary, "rows": rows, "ground_truth_path": str(gt_path)}


def report(out: dict, quiet: bool) -> None:
    s, rows = out["summary"], out["rows"]
    if not quiet:
        print("\nBidSahayak benchmark — " + s["tier"])
        print(f"repo {s['repo']} @ {s['git_head']}  ·  {s['n_documents']} documents  ·  {s['generated']}\n")
        print(f"{'document':<34} {'emd':<6} {'deadline':<9} {'turnover':<9} {'exempt':<7}")
        print("-" * 74)
        for r in rows:
            if not r.get("run"):
                print(f"{r['file'][:33]:<34} {BAD}ERROR {r.get('error','')[:28]}{ESCAPE}")
                continue
            f = r["fields"]
            cells = "".join(
                (f"{DIM}amb{ESCAPE}" if f[k]["ok"] == "ambiguous" else (f"{OK}ok{ESCAPE}" if f[k]["ok"] else f"{BAD}MISS{ESCAPE}")
                 ).ljust(6 + 9) for k in ("emd", "deadline", "turnover", "exemption"))
            print(f"{r['file'][:33]:<34} {cells}")
        print("-" * 74)
        for k, v in s["per_field"].items():
            colour = OK if s["per_field"][k]["accuracy"] >= s["thresholds"][k] else BAD
            print(f"{k:<10} {v['correct']:>2}/{v['of']:<2}  {colour}{v['accuracy']:.0%}{ESCAPE}"
                  f"   (threshold {s['thresholds'][k]:.0%})")
        if s["latency_ms"]["p50"]:
            print(f"\nlatency   p50 {s['latency_ms']['p50']} ms · p95 {s['latency_ms']['p95']} ms")
        misses = [(r["file"], k, v) for r in rows if r.get("run") for k, v in r["fields"].items()
                  if not v["ok"] and v["ok"] != "ambiguous"]
        print(f"\nmisses ({len(misses)}):")
        for file, k, v in misses[:40]:
            print(f"  {DIM}{file[:30]:<32}{k:<10} got {v['got']!r:<22} want {v['want']!r}{ESCAPE}")
    print(("\nBENCHMARK: PASS" if s["passed"] else "\nBENCHMARK: FAIL — thresholds not met"))


def to_markdown(out: dict) -> str:
    s = out["summary"]
    gt_norm = re.sub(r"^.*?assets[/\\]", "assets/", out["ground_truth_path"]).replace("\\", "/")
    lines = [f"# Extraction benchmark", "",
             f"Generated `{s['generated']}` from commit `{s['git_head']}` · tier: **{s['tier']}** · "
             f"{s['n_documents']} documents.", "",
             f"Ground truth: `{gt_norm}` — read from the documents, never from the pipeline.", "",
             "| Field | Correct | Of | Accuracy | Threshold |", "|---|---|---|---|---|"]
    for k, v in s["per_field"].items():
        lines.append(f"| {k} | {v['correct']} | {v['of']} | {v['accuracy']:.0%} | {s['thresholds'][k]:.0%} |")
    if s["latency_ms"]["p50"]:
        lines += ["", f"Latency: p50 {s['latency_ms']['p50']} ms · p95 {s['latency_ms']['p95']} ms "
                      f"(single machine, {s['tier']} tier)."]
    lines += ["", "## Document Results", "",
              "| Document | Tier | EMD | Deadline | Turnover | Exemption | Time (s) |",
              "|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        if r.get("run"):
            f = r["fields"]
            emd_str = "amb" if f["emd"]["ok"] == "ambiguous" else ("✓" if f["emd"]["ok"] else "✗")
            dl_str = "amb" if f["deadline"]["ok"] == "ambiguous" else ("✓" if f["deadline"]["ok"] else "✗")
            tv_str = "amb" if f["turnover"]["ok"] == "ambiguous" else ("✓" if f["turnover"]["ok"] else "✗")
            ex_str = "amb" if f["exemption"]["ok"] == "ambiguous" else ("✓" if f["exemption"]["ok"] else "✗")
            lat_s = f"{r.get('latency_ms', 0) / 1000:.2f}s"
            tier_val = f"Tier {r.get('tier', 3)}"
            lines.append(f"| `{r['file']}` | {tier_val} | {emd_str} | {dl_str} | {tv_str} | {ex_str} | {lat_s} |")
        else:
            lines.append(f"| `{r['file']}` | ERR | - | - | - | - | {r.get('error', '')[:20]} |")
    lines += ["", "## Misses", ""]
    misses = [(r["file"], k, v) for r in out["rows"] if r.get("run") for k, v in r["fields"].items()
              if not v["ok"] and v["ok"] != "ambiguous"]
    amb = [(r["file"], k) for r in out["rows"] if r.get("run") for k, v in r["fields"].items() if v["ok"] == "ambiguous"]
    if not misses:
        lines.append("None — all compared fields matched ground truth on this run.")
    else:
        lines += ["| Document | Field | Extracted | Ground truth |", "|---|---|---|---|"]
        for f, k, v in misses:
            lines.append(f"| `{f}` | {k} | `{v['got']}` | `{v['want']}` |")
    if amb:
        lines += ["", "## Deliberately ambiguous (excluded from accuracy)", "",
                  "| Document | Field | Why |", "|---|---|---|"] + \
                 [f"| `{f}` | {k} | the document states two competing values; correct behaviour is human review |" for f, k in amb]
    errs = [r for r in out["rows"] if not r.get("run")]
    if errs:
        lines += ["", "## Failures", ""] + [f"- `{r['file']}` — {r.get('error')}" for r in errs]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="BidSahayak extraction benchmark")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--no-llm", action="store_true", help="deterministic tier only")
    ap.add_argument("--gt", default=None, help="path to ground_truth.json")
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = run(repo, use_llm=not a.no_llm, only=a.gt)
    report(out, a.quiet)
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(out, indent=1), encoding="utf-8")
    if a.md:
        Path(a.md).parent.mkdir(parents=True, exist_ok=True)
        Path(a.md).write_text(to_markdown(out), encoding="utf-8")
    return 0 if out["summary"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
