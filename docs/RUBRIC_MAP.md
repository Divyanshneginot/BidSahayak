# WCC Launchpad 30 Rubric Map — BidSahayak

**Track**: Track 01 — Agentic AI  
**Builder**: Solo Developer  
**Status**: 100% Provable & Verified (18/18 Quality Gates)

---

## 1. User Insight & Problem Evidence (15 Points)

| Requirement | Implementation & Sourced Evidence | Verification Artifact |
|---|---|---|
| **Audited Empirical Evidence** | CAG Report No. 5 of 2021 & Report No. 13 of 2023 on public procurement barriers; Ministry of MSME Annual Reports; GeM procurement statistics. | `PROBLEM_EVIDENCE.md` §1–§3 |
| **Current Ground Truth (2026)** | Union Budget 2026-27 "Corporate Mitra" scheme guidelines (MCA, 23 June 2026): 2,000 para-professionals across 7.61 Cr MSMEs (~1:38,000 ratio). | `PROBLEM_EVIDENCE.md` §0, `NOTICE.md` |
| **Document Complexity Proof** | Ground-truth measurement across 14 tenders demonstrating unstructured Indian procurement formats (NIT, EMD, Turnover, Experience). | `tender_measurement.csv`, `assets/ground_truth.json` |

---

## 2. Architectural Elegance & Agentic Implementation (25 Points)

| Requirement | Implementation | Code & Tests |
|---|---|---|
| **6-Tier Degradation Ladder** | Extractor falls gracefully: Tier 1 (Gemini 2.0/3.5) → Tier 2 (Groq llama-3.3-70b) → Tier 3 (Deterministic Regex) without hard failures. | `src/agent/extractor.py`, `src/supervisor.py` |
| **Explicit Provider Resolution** | Resolves API keys explicitly via env and known prefix maps (`AIza...` → `gemini`, `gsk_...` → `groq`, `sk-...` → `openai`). | Gate **G23**, `tests/test_extractor.py` |
| **Pure Deterministic Reasoning** | Exact codification of GFR 2017 Rules 149, 170, 173 and PPP for MSEs 2012. 3-year turnover averaging (not flawed max) and Class 3 DSC timing constraint. | `src/evaluator.py`, Gates **G6**, **G7** |
| **End-to-End Orchestration** | Supervisor coordinates W1 (Ingestion) → W2 (Normalization) → W4 (Extraction) → W5 (Evaluation) with full audit logging. | `src/supervisor.py`, `tests/test_supervisor.py` |

---

## 3. Responsible Design, Safety & Trust (20 Points)

| Requirement | Implementation | Code & Tests |
|---|---|---|
| **Fail-Closed Anti-Hallucination** | Empty matrices, low-confidence fields (<0.7), and unresolved values strictly route to `needs-human-review` (never eligible by default). | `src/evaluator.py`, Gate **G3**, `tests/test_adversarial.py` |
| **Value & Snippet Round-Trip** | Every extracted figure must match its own cited page snippet. Mismatches cap confidence at $\le 0.30$. Code may only lower confidence. | `src/verify.py`, Gate **G2**, `src/agent/extractor.py` |
| **Human-in-the-Loop Gate** | Operators approve/override individual fields (`/api/assess/override`). Instant re-evaluation with immutable audit history. | Gate **G16**, `frontend/index.html`, `src/api.py` |
| **Non-Circumvention Boundary** | Hard-coded guarantee: BidSahayak never auto-submits bids to CPPP or GeM on the user's behalf. | `README.md`, `frontend/index.html` |

---

## 4. Frontend Accessibility & Internationalization (20 Points)

| Requirement | Implementation | Code & Tests |
|---|---|---|
| **Design Freeze Integrity** | Strict preservation of design tokens (`--ink`, `--paper`, `--hl`), typography, and section hierarchy (`top` → `evidence` → `demo` → `result` → `source` → `trace`). | `scripts/ui_freeze_check.py` [PASS] |
| **Complete MSME Profile Panel** | Collapsible vendor configuration card with all 9 fields (`pfName`, `pfUdyam`, `pfTurnover`, `pfYears`, etc.) and 90-day stale warning. | Gate **G14**, `frontend/index.html` |
| **Lossless Bilingual Toggle** | Seamless English ↔ Hindi switching with automated `dataset.en` snapshotting on initial toggle. | Gate **G18**, `tests/test_frontend_playwright.py` |
| **Accessible Controls** | WCAG 2.2 AA compliant high-contrast theme toggle, ARIA live regions, 44px touch targets, and skip links. | `frontend/index.html` |

---

## 5. Verification, Testing & Honesty (20 Points)

| Requirement | Implementation | Code & Tests |
|---|---|---|
| **18 Automated Truth Gates** | Automated regression gates covering parsing, timezone awareness, security, and claims honesty. | `scripts/gate.py` (18/18 PASS, 100%) |
| **Synthetic Provenance Honesty** | Clear disclosure that 13 of 14 sample tenders are synthetic fixtures, with `imd-tender.pdf` as the real seed document. | `sample_tenders/NOTICE.md`, Gate **G10** |
| **Claims Ledger** | Every public marketing or documentation claim mapped to empirical proof with zero unverified rows. | `docs/CLAIMS_LEDGER.md`, Gate **G13** |
| **Adversarial Neutralization** | Complete defense against corrupted dates, decimal paise multiplication bugs, and fraudulent trader exemption claims. | `tests/test_adversarial.py` (3/3 PASS) |
| **Cloud Hosting Readiness** | Containerized with dynamic `$PORT` binding, wildcard CORS origin support (`ALLOWED_ORIGINS=*`), and ephemeral file cleanup. | `Dockerfile`, `render.yaml`, `src/api.py` |
