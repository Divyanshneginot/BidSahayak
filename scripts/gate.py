#!/usr/bin/env python3
"""
BidSahayak release gates.

The single source of truth for "done". A phase is complete when its gates are green.
This script is intentionally honest: it runs the repo's own code and reports what it finds.

Usage
-----
  python scripts/gate.py --repo .                 # every gate
  python scripts/gate.py --repo . --phase 2       # core-repair gates
  python scripts/gate.py --repo . --gate G1       # one gate
  python scripts/gate.py --repo . --json out.json # machine-readable report
  python scripts/gate.py --repo . --baseline      # same as --all, marks output as baseline

Exit code: 0 if all selected gates pass, 1 otherwise.
Never weaken a check to make it pass. Adding a check is always allowed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PHASES = {
    "0": "all",
    "1": ["G10", "G11", "G12", "G13"],
    "2": ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G19", "G21", "G23"],
    "3": ["G14", "G15", "G16", "G18"],
    "4": "all",
}

GATE_TITLES = {
    "G23": "LLM tier is reachable and the trace reports the real tier",
    "G1": "parse_inr handles paise / lakh / crore",
    "G2": "value verified, not just the snippet (no confidence promotion)",
    "G3": "fail closed: unknown inputs never yield 'eligible'",
    "G4": "deadline: real NIT phrasings + explicit unresolved field",
    "G5": "scan honesty: skipped pages reported, claims match code",
    "G6": "timezone: IST math for the DSC window",
    "G7": "turnover uses the average over the stated window; gaps classified",
    "G8": "web hardening: CORS, upload cleanup, security headers",
    "G10": "fixtures labelled as synthetic (provenance notice)",
    "G11": "README numbers are reproducible; unreproducible claims deleted",
    "G12": "dossier §4 no longer contradicts the fixtures",
    "G13": "tender_measurement.csv ground-truth rows corrected",
    "G14": "frontend sends the profile and calls /api/assess/evaluate",
    "G15": "honest labelling: no 'Live' verdict without a verdict",
    "G16": "Approve/override posts to /api/assess/override",
    "G18": "bilingual toggle is lossless (EN->HI->EN)",
    "G19": "reproducible benchmark harness present and passing thresholds",
    "G20": "repo hygiene",
    "G21": "test suite green",
    "G22": "no credentials in the working tree",
}


# ----------------------------------------------------------------------------- helpers
def read(repo: Path, rel: str) -> str:
    p = repo / rel
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def py(repo: Path, code: str, timeout: int = 120) -> tuple[int, str, str]:
    env = dict(os.environ, PYTHONPATH=str(repo), PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=str(repo), capture_output=True,
                           text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"


def sh(repo: Path, cmd: list[str], timeout: int = 300) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 124, "", str(e)


# ----------------------------------------------------------------------------- gates
def g1(repo: Path):
    cases = [("10,000.00", 10000), ("Rs. 10,000.00 (Rupees Ten Thousand only)", 10000),
             ("1,20,000", 120000), ("5 Lakhs", 500000), ("1.5 Crore", 15000000),
             ("₹45,00,000", 4500000), ("50,000", 50000)]
    code = ("import json\n"
            "from src.regex_fallback import DeterministicRegexExtractor as D\n"
            "cases=%r\n"
            "print(json.dumps([[s, D.parse_inr(s)] for s,_ in cases]))\n" % (cases,))
    rc, out, err = py(repo, code)
    if rc != 0:
        return False, f"import/parse_inr failed: {err.splitlines()[-1] if err else rc}"
    got = {s: v for s, v in json.loads(out)}
    bad = [f"{s!r}->{got.get(s)} (want {w})" for s, w in cases if got.get(s) != w]
    return (not bad), ("all 7 cases correct" if not bad else "; ".join(bad[:4]))


def g2(repo: Path):
    src = read(repo, "src/agent/extractor.py") + read(repo, "src/verify.py")
    promoted = re.search(r"confidence\s*=\s*max\(", src) is not None
    has_fn = "def verify_value" in src
    code = ("import json\n"
            "from src.verify import SnippetVerifier as V\n"
            "r=lambda s,v: V.verify_value(s,v)\n"
            "out={'mismatch': bool(r('EMD: Rs. 10,000.00', 1000000).is_verified),\n"
            "     'match':    bool(r('EMD: Rs. 10,000.00', 10000).is_verified)}\n"
            "print(json.dumps(out))\n")
    rc, out, err = py(repo, code)
    if rc != 0:
        return False, f"verify_value missing or failing: {(err or '').splitlines()[-1][:90]}"
    d = json.loads(out)
    ok = has_fn and not promoted and d["match"] and not d["mismatch"]
    ev = []
    if not has_fn: ev.append("no verify_value()")
    if promoted: ev.append("confidence still promoted with max()")
    if d["mismatch"]: ev.append("10,000.00 vs 1000000 accepted")
    if not d["match"]: ev.append("correct value rejected")
    return ok, ("round-trip enforced" if ok else "; ".join(ev))


def g3(repo: Path):
    code = ("import json\n"
            "from src.models import RequirementMatrix, VendorProfile\n"
            "from src.evaluator import evaluate\n"
            "m=RequirementMatrix(tender_id='t',title='t',issuing_department='d')\n"
            "p=VendorProfile(business_name='x',udyam_classification='Micro',annual_turnover_last_3y=[])\n"
            "v=evaluate(m,p)\n"
            "print(json.dumps({'defaults':m.emd_exempt_categories,'overall':v.overall}))\n")
    rc, out, err = py(repo, code)
    if rc != 0:
        return False, f"evaluator import failed: {(err or '').splitlines()[-1][:90]}"
    d = json.loads(out)
    ok = d["defaults"] == [] and d["overall"] != "eligible"
    ev = f"defaults={d['defaults']} overall={d['overall']}"
    return ok, (ev + " (fail-closed)" if ok else ev + " <- assumed exemption / eligible by default")


def g4(repo: Path):
    phrases = ["Closing date and time for submission of tender 24.06.2019 / 1500 Hrs.",
               "Bid submission closing date: 24-10-2026",
               "Last date of bid submission: 25.10.2026 17:00",
               "निविदा जमा करने की अंतिम तिथि: 21-10-2026",
               "Due date for submission 2026-11-02T15:00:00+05:30",
               "Closing Date 18-10-2026"]
    code = (
        "import json\n"
        "from src.text_extract import ExtractionResult, PageText\n"
        "from src.regex_fallback import DeterministicRegexExtractor as D\n"
        "ph=%r\n"
        "res=[]\n"
        "for t in ph:\n"
        "    pg=PageText(page_number=1, raw_text=t, normalized_text=t, char_count=len(t), is_scanned_likely=False)\n"
        "    er=ExtractionResult(tender_id='t', total_pages=1, pages={1:pg}, full_text=t, is_scanned_document=False)\n"
        "    dt,_=D.extract_deadline(er)\n"
        "    res.append(dt.isoformat() if dt else None)\n"
        "from src.models import RequirementMatrix\n"
        "has_field='unresolved_fields' in RequirementMatrix.model_fields\n"
        "print(json.dumps({'parsed':res,'unresolved_field':has_field}))\n" % (phrases,))
    rc, out, err = py(repo, code)
    if rc != 0:
        return False, f"extract_deadline failed: {(err or '').splitlines()[-1][:90]}"
    d = json.loads(out)
    n = sum(1 for x in d["parsed"] if x)
    ok = n >= 5 and d["unresolved_field"]
    ev = f"{n}/6 phrasings parsed; unresolved_fields={'yes' if d['unresolved_field'] else 'no'}"
    return ok, ev


def g5(repo: Path):
    src = read(repo, "src/text_extract.py") + read(repo, "src/api.py")
    readme = read(repo, "README.md")
    reqs = read(repo, "requirements.txt")
    exposed = "skipped_pages" in src
    ocr_claim = bool(re.search(r"\bocr\b", readme, re.I))
    ocr_real = bool(re.search(r"pytesseract|pdf2image|pdfplumber|ocrmypdf|tesseract", reqs, re.I))
    honest = ("skipped" in readme.lower()) if ocr_claim else True
    ok = exposed and (ocr_real or honest)
    ev = f"skipped_pages={'yes' if exposed else 'no'}"
    if ocr_claim and not ocr_real:
        ev += f"; README claims OCR, deps={'ok' if ocr_real else 'absent'}, honest-skip wording={'yes' if honest else 'NO'}"
    return ok, ev


def g6(repo: Path):
    ev46 = read(repo, "src/evaluator.py")
    ist = "ZoneInfo" in ev46
    utc = "timezone.utc" in ev46
    ok = ist and not utc
    return ok, f"ZoneInfo={'yes' if ist else 'no'} raw-utc={'yes' if utc else 'no'}"


def g7(repo: Path):
    ev46 = read(repo, "src/evaluator.py")
    bad = re.search(r"max\(profile\.annual_turnover_last_3y\)", ev46) is not None
    avg = bool(re.search(r"average|sum\(recent\)|/ len\(recent\)", ev46))
    heuristic = "len(gaps) <= 2" in ev46 or "len(gaps)<=2" in ev46
    ok = avg and not bad and not heuristic
    ev = f"average={'yes' if avg else 'no'} max()-bug={'present' if bad else 'gone'} 2-gap-heuristic={'present' if heuristic else 'gone'}"
    return ok, ev


def g8(repo: Path):
    api = read(repo, "src/api.py")
    creds = "allow_credentials=False" in api.replace(" ", "")
    wild = re.search(r'allow_origins=\[\s*"\*"\s*\]', api) is not None
    cleanup = "os.remove" in api or "unlink" in api
    headers = bool(re.search(r"X-Content-Type-Options|Strict-Transport-Security|security_headers", api, re.I))
    ok = creds and not wild and cleanup and headers
    ev = (f"credentials={'locked' if creds else 'OPEN'} wildcard_origin={'present' if wild else 'gone'} "
          f"upload_cleanup={'yes' if cleanup else 'no'} security_headers={'yes' if headers else 'no'}")
    return ok, ev


def g10(repo: Path):
    notice = read(repo, "sample_tenders/NOTICE.md")
    ok = "synthetic" in notice.lower() and "imd-tender.pdf" in notice
    return ok, ("NOTICE.md present and honest" if ok else "sample_tenders/NOTICE.md missing or incomplete")


def g11(repo: Path):
    rm = read(repo, "README.md")
    killed = [t for t in ["14 / 14 (100%)", "0 Confident Errors", "Zero Confident Hallucinations",
                          "< 3 seconds per tender"] if t in rm]
    harness = "scripts/benchmark.py" in rm
    known = "known failure" in rm.lower() or "known limits" in rm.lower()
    ok = not killed and harness and known
    ev = []
    if killed: ev.append(f"unreproducible claims present: {killed}")
    if not harness: ev.append("README does not point at scripts/benchmark.py")
    if not known: ev.append("no Known failure modes / limits section")
    return ok, ("README is reproducible" if ok else "; ".join(ev))


def g12(repo: Path):
    pe = read(repo, "PROBLEM_EVIDENCE.md")
    bad = [t for t in ["34.2 pages", "11.4 days", "5.8 pages", "downloaded on 4 October 2026",
                       "Zero fabricated statistics"] if t in pe]
    honest = "synthetic" in pe.lower() or "fixture" in pe.lower()
    ok = not bad and honest
    ev = f"contradicting aggregates={bad or 'none'}; provenance wording={'present' if honest else 'missing'}"
    return ok, ev


def g13(repo: Path):
    csv_txt = read(repo, "tender_measurement.csv")
    bad_urls = re.findall(r"https?://[^\s,]+", csv_txt)
    live_portals = [u for u in bad_urls if "sample_tenders" not in u]
    imd_ok = "2019-06-24" in csv_txt
    bcc_row = [l for l in csv_txt.splitlines() if l.startswith("5,")]
    bcc_ok = bool(bcc_row) and ("2026-10-25" not in bcc_row[0])
    ok = imd_ok and bcc_ok and len(live_portals) <= 1
    ev = (f"IMD deadline corrected={'yes' if imd_ok else 'no'}; BCCL invented date={'gone' if bcc_ok else 'STILL PRESENT'}; "
          f"live-portal URLs in csv={len(live_portals)}")
    return ok, ev


def g14(repo: Path):
    html = read(repo, "frontend/index.html")
    ok = "/api/assess/evaluate" in html and "pfUdyam" in html and "pfTurnover" in html
    ev = (f"evaluate-call={'yes' if '/api/assess/evaluate' in html else 'no'} "
          f"profile-panel={'yes' if ('pfUdyam' in html and 'pfTurnover' in html) else 'no'}")
    return ok, ev


def g15(repo: Path):
    html = read(repo, "frontend/index.html")
    honest = "Extraction only" in html
    buggy_default = '"UPLOADED TENDER"' in html or "'UPLOADED TENDER'" in html
    ok = honest and not buggy_default
    ev = f"honest-label={'yes' if honest else 'no'} buggy-kicker-default={'present' if buggy_default else 'gone'}"
    return ok, ev


def g16(repo: Path):
    html = read(repo, "frontend/index.html")
    ok = "/api/assess/override" in html
    return ok, ("override wired from the UI" if ok else "Approve buttons still only toggle local state")


def _strip_strings(s: str) -> str:
    """Replace the contents of string literals with nothing, so key-regexes cannot false-match values."""
    out, quote, esc = [], None, False
    for c in s:
        if quote:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                quote = None
                out.append(" ")
                continue
            continue
        if c in ('"', "'"):
            quote = c
            out.append(c)
            continue
        out.append(c)
    return "".join(out)


def _block(js: str, lang: str) -> str:
    """Return the '{...}' literal of a top-level i18n language block, string-aware."""
    i = js.find(f"{lang}:{{")
    if i < 0:
        return ""
    j = js.find("{", i)
    depth, quote, esc = 0, None, False
    for k in range(j, len(js)):
        c = js[k]
        if quote:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                quote = None
            continue
        if c in ('"', "'"):
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return js[j:k + 1]
    return ""


def _dict_keys(js: str, lang: str) -> set:
    """Lex the block at depth 1 and collect every key (quoted or bare) — values are skipped."""
    block = _block(js, lang)
    if not block:
        return set()
    keys, depth, i, n = set(), 0, 0, len(block)
    while i < n:
        c = block[i]
        if c == "/" and i + 1 < n and block[i + 1] == "/":          # line comment
            i = block.find("\n", i)
            if i < 0:
                break
            continue
        if c == "{":
            depth += 1
            i += 1
            continue
        if c == "}":
            depth -= 1
            i += 1
            continue
        if c in ('"', "'"):
            q, j, buf = c, i + 1, []
            while j < n:
                if block[j] == "\\":
                    buf.append(block[j + 1] if j + 1 < n else "")
                    j += 2
                    continue
                if block[j] == q:
                    break
                buf.append(block[j])
                j += 1
            text, k = "".join(buf), j + 1
            kk = k
            while kk < n and block[kk] in " \t\r\n":
                kk += 1
            if depth == 1 and kk < n and block[kk] == ":":
                keys.add(text)
            i = k
            continue
        if c.isalpha() or c in "_$":
            j = i
            while j < n and (block[j].isalnum() or block[j] in "_$"):
                j += 1
            kk = j
            while kk < n and block[kk] in " \t\r\n":
                kk += 1
            if depth == 1 and kk < n and block[kk] == ":":
                keys.add(block[i:j])
            i = j
            continue
        i += 1
    return keys


def g18(repo: Path):
    html = read(repo, "frontend/index.html")
    js = "".join(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S))
    n_elems = len(re.findall(r'data-i18n(?:-html)?="', html))
    en_keys = len(_dict_keys(js, "en"))
    hi_keys = len(_dict_keys(js, "hi"))
    snapshot = bool(re.search(r"dataset\.en\b|data\.enHtml|\.dataset\.enHtml", html))
    ok = snapshot or en_keys >= n_elems
    ev = (f"bilingual elements={n_elems} · en keys={en_keys} · hi keys={hi_keys} · "
          f"EN-default snapshot={'yes' if snapshot else 'NO'} → "
          + ("toggle is lossless" if ok else "EN→HI→EN leaves Hindi text in place"))
    return ok, ev


def g19(repo: Path):
    if not (repo / "scripts/benchmark.py").exists():
        return False, "scripts/benchmark.py missing"
    rc, out, err = sh(repo, [sys.executable, "scripts/benchmark.py", "--repo", ".", "--no-llm", "--quiet"])
    if rc != 0:
        tail = (err or out).strip().splitlines()[-1][:120] if (err or out).strip() else f"exit {rc}"
        return False, f"benchmark below thresholds or failed: {tail}"
    return True, "benchmark harness runs and meets thresholds"


def g23(repo: Path):
    """Provider resolution is explicit, the real tier is reported, and fallbacks are visible."""
    ext = read(repo, "src/agent/extractor.py")
    sup = read(repo, "src/supervisor.py")
    envx = read(repo, ".env.example")
    ev = []

    gemini_prefix = "AIza" in ext
    if not gemini_prefix:
        ev.append("key-prefix map does not recognise 'AIza' (Gemini keys route to the OpenAI endpoint)")

    silent = bool(re.search(r"except\s+Exception\s+as\s+e:[\s\S]{0,180}DeterministicRegexExtractor", ext))
    if silent:
        ev.append("Tier-1 failure still swallowed by a bare except -> silent regex fallback")

    tier_var = re.search(r"(?:self\.)?(last_tier|tier_used|extraction_tier)\s*=", ext) is not None
    if not tier_var:
        ev.append("extractor does not record which tier actually ran")
    if tier_var and not re.search(r"(last_tier|tier_used|extraction_tier)", sup):
        ev.append("Supervisor trace still infers the tier from key presence instead of the recorded tier")
    if "tier_reached=3 if not self.extractor_agent.api_key else 1" in sup.replace(" ", "").replace("\n", " "):
        ev.append("supervisor still hardcodes tier_reached from api_key presence")

    if "GEMINI_API_KEY" not in envx or "GROQ_API_KEY" not in envx or "LLM_PROVIDER" not in envx:
        ev.append(".env.example does not document every env var the code reads")

    ok = not ev
    live = os.getenv("GATE_LIVE_LLM") == "1"
    if ok and live:
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        if not key:
            ev.append("GATE_LIVE_LLM=1 but no key in env")
            ok = False
        else:
            rc, out, err = py(repo, ("from src.agent.extractor import ExtractorAgent as E\n"
                                     "a=E(api_key=None)\n"
                                     "print(a.provider, a.model)\n"), timeout=60)
            ev.append(f"live: provider/model = {out.strip() or err.strip()[:80]}")
    return ok, ("provider explicit, tier reported, fallbacks visible"
                + ("; " + "; ".join(ev) if ev else "") if ok else "; ".join(ev))


def g20(repo: Path):
    scratch = [f.name for f in (repo / "sample_tenders").glob("*")
               if f.name.endswith("-b64.txt") or f.name.startswith("page-") or f.name == "coords.json"] \
        if (repo / "sample_tenders").exists() else []
    ini = read(repo, "pytest.ini")
    reqs = read(repo, "requirements.txt")
    asyncio_bad = ("asyncio_mode" in ini) and ("pytest-asyncio" not in reqs)
    ok = not scratch and not asyncio_bad
    ev = f"scratch files={scratch or 'none'}; pytest.ini asyncio misconfig={'yes' if asyncio_bad else 'no'}"
    return ok, ev


def g21(repo: Path):
    rc, out, err = sh(repo, [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"], timeout=600)
    if rc == 124:
        return False, "pytest timed out"
    tail = (out or err).strip().splitlines()[-1][:140] if (out or err).strip() else ""
    return rc == 0, tail


def g22(repo: Path):
    pats = [r"AIza[0-9A-Za-z_\-]{35}", r"gsk_[A-Za-z0-9]{20,}", r"sk-[A-Za-z0-9]{20,}"]
    hits = []
    for p in repo.rglob("*"):
        if any(part in {".git", "node_modules", "__pycache__", ".venv"} for part in p.parts):
            continue
        if p.is_file() and p.stat().st_size < 2_000_000 and p.suffix.lower() in {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".csv", ".html", ".env", ".example", ""}:
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat in pats:
                if re.search(pat, txt):
                    hits.append(str(p.relative_to(repo)))
                    break
    ok = not hits
    return ok, ("no credential patterns found" if ok else f"possible secrets in: {sorted(set(hits))}")


GATES = {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6, "G7": g7, "G8": g8,
         "G10": g10, "G11": g11, "G12": g12, "G13": g13, "G14": g14, "G15": g15, "G16": g16,
         "G18": g18, "G19": g19, "G20": g20, "G21": g21, "G22": g22, "G23": g23}
ORDER = list(GATES.keys())


def main() -> int:
    ap = argparse.ArgumentParser(description="BidSahayak release gates")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--phase", default=None, choices=list(PHASES.keys()))
    ap.add_argument("--gate", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    repo = Path(a.repo).resolve()
    if a.gate:
        selected = [a.gate]
    elif a.phase and PHASES[a.phase] != "all":
        selected = PHASES[a.phase]
    else:
        selected = ORDER

    print(f"\nBidSahayak release gates — repo: {repo}")
    print(f"{'gate':<5} {'phase':<6} {'title':<58} result")
    print("-" * 118)
    results, t0 = {}, time.time()
    for gid in selected:
        fn = GATES.get(gid)
        if not fn:
            continue
        try:
            ok, evidence = fn(repo)
        except Exception as e:  # a crashing gate is a failing gate
            ok, evidence = False, f"gate crashed: {type(e).__name__}: {e}"
        results[gid] = {"ok": bool(ok), "evidence": evidence, "title": GATE_TITLES.get(gid, "")}
        phase = next((p for p, v in PHASES.items() if v != "all" and gid in v), "-")
        mark = "PASS" if ok else "FAIL"
        print(f"{gid:<5} {phase:<6} {GATE_TITLES.get(gid,'')[:56]:<58} {mark}  {evidence}")

    passed = sum(1 for r in results.values() if r["ok"])
    total = len(results)
    score = round(100 * passed / total, 1) if total else 0.0
    print("-" * 118)
    tag = "BASELINE" if a.baseline else "SCORE"
    print(f"{tag}: {passed}/{total} gates green  →  {score}/100 release readiness   ({time.time()-t0:.1f}s)")
    failing = [g for g, r in results.items() if not r["ok"]]
    if failing:
        print("failing: " + ", ".join(failing))
    print()

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps({
            "repo": str(repo), "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "git_head": sh(repo, ["git", "rev-parse", "HEAD"])[1] or "n/a",
            "baseline": bool(a.baseline), "score": score, "passed": passed, "total": total,
            "gates": results}, indent=1), encoding="utf-8")
        print(f"wrote {a.json}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
