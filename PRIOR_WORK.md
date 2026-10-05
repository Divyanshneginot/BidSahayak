# Prior Work & Provenance Disclosure

> Per WCC Launchpad 30 Rule 04: *"If your project builds on prior code, libraries, or frameworks not created during the event, disclose them."*

## 1. What Was Prepared Before 10:00 IST (4 Oct 2026)

Before kickoff at 10:00 IST on 4 October 2026, no code repository existed, no commits were made, and no application code was written.

The following assets, research, and plans were prepared beforehand:

### A. The Project Plan
- **Concept & Architecture Plan**: A planning document defining the problem statement: small Indian MSMEs abandon government tenders because eligibility rules are buried in 40–100 page procurement documents. The core architectural decision was planned in advance: use an LLM only for unstructured schema extraction, but strictly enforce a deterministic rules engine for eligibility verification and GFR legal compliance.

### B. Domain Research & Evidence
- **CAG Audit Reports**: Sourced empirical data from Comptroller and Auditor General (CAG) audit reports:
  - CAG UP Report No. 4 of 2017: 73% of road resurfacing tenders received only 1 or 2 bids due to opaque eligibility hurdles.
  - CAG Karnataka JJM Report No. 2 of 2024: 24.4% of water tenders had single-bidder outcomes.
- **Legal & Policy Rules**: Detailed notes on:
  - General Financial Rules (GFR 2017) Rule 149 (GeM procurement), Rule 170 (Bid Security / EMD), and Rule 173 (Transparency and Competition).
  - Public Procurement Policy for Micro and Small Enterprises (MSEs) Order 2012 (mandatory 25% annual procurement, EMD exemptions).
- **Document Anatomy**: Structural mapping of standard Indian Notice Inviting Tender (NIT) layouts, Instructions to Bidders (ITB), Tender Information Summaries (TIS), and CPWD-6 schedules.

### C. Prior Projects (Zero Code Reused)
Two public repositories existed from September 2026:
1. **Tender Alert Bot**: A Telegram alert bot that periodically queried public listings. **Zero lines of code carried over.** BidSahayak does not scrape, alert, or track listings; it analyzes document eligibility.
2. **Emergency Coordination Prototype**: A real-time geospatial incident coordination dashboard. **Zero lines of code carried over.** Different domain, stack, and architecture.
Both repositories remain public and unmodified for audit.

---

## 2. What Was Built During the Event (4 Oct 10:00 IST – 5 Oct 14:00 IST)

All code in this repository was written and committed inside the official hackathon window.

1. **Document Ingestion (`src/ingest.py`, `src/text_extract.py`)**: PDF byte validation, SHA-256 fingerprinting, per-page text extraction via `pypdf`, and scanned page detection.
2. **Page-Aware Section Retrieval (`src/agent/extractor.py`)**: Keyword density algorithm extracting relevant ITB, EMD, and qualification sections across 40–100+ page tenders.
3. **Agentic Extraction Loop & Self-Repair (`src/agent/extractor.py`)**: Structured schema extraction, anti-hallucination citation verification via `SnippetVerifier`, and automated self-repair via `REPAIR_PROMPT_TEMPLATE`.
4. **Deterministic Regex Fallback (`src/regex_fallback.py`)**: Offline regex parser handling Indian currency denominations (paise, lakh, crore).
5. **Deterministic Evaluator (`src/evaluator.py`)**: GFR eligibility engine validating EMD exemptions, turnover averaging across 3 years, past work %, net worth, and IST-aware Class-3 DSC timing.
6. **Web API & Human Console (`src/api.py`, `frontend/index.html`)**: FastAPI backend with operator approve/override endpoints, unresolved field cleanup, audit trace, and bilingual EN/HI toggle.
7. **Testing & Benchmark Batteries**: 40 automated pytest tests, 14-tender synthetic benchmark, real Groq LLM benchmark, and 10-tender real public tender held-out benchmark.

---

## 3. AI-Generated Code Disclosure

In accordance with event guidelines, AI coding assistants (Google Gemini and Anthropic Claude via IDE agent tooling) were utilized during development.

### What AI Generated:
- Boilerplate Pydantic model definitions (`src/models.py`).
- Initial regex drafts for currency and date matching.
- Synthetic fixture generation script (`scripts/generate_sample_tenders.py`) using ReportLab.
- Test scaffolding and parameterized test cases in `tests/`.
- Vanilla HTML/CSS layout structure and bilingual UI translation dictionary in `frontend/index.html`.

### What Was Human-Directed & Authored:
- Two-tier system architecture (LLM extraction with repair + deterministic regex fallback).
- Anti-hallucination verification contract (`SnippetVerifier` enforcing verbatim page matching).
- Fail-closed deterministic evaluation rules, IST timezone math, and GFR 170 compliance logic.
- Held-out ground truth data collection and benchmark scoring harness.
- Verification release gates (`scripts/gate.py`).
