# Prior Work & Provenance Disclosure

> Per WCC Launchpad 30 Rule 04: *"If your project builds on prior code, libraries, or frameworks not created during the event, disclose them."*

## 1. What Was Prepared Before Kickoff (10:00 IST, 4 Oct 2026)

Before event kickoff, no repository existed, no code was written, and no implementation commits were made.

Permitted domain research and background knowledge carried into the event (per Rule 02):
- **Domain Understanding**: Knowledge of Central & State procurement structures in India (CPPP / eprocure.gov.in, GeM, State PWD / Jal Nigam portals).
- **Document Anatomy**: Structure of standard Indian Notice Inviting Tender (NIT), Instructions to Bidders (ITB), Tender Information Summary (TIS), and qualification schedules.
- **Legal & Policy Frameworks**: General Financial Rules (GFR 2017) Rules 149, 170, and 173; Public Procurement Policy for Micro and Small Enterprises (MSEs) Order 2012.
- **CAG Audit Findings**: Familiarity with public CAG audit reports (UP PWD road contracts, Karnataka JJM water projects) documenting single-bid tender rates due to buried qualification criteria.
- **Unicode NFKC Handling**: Understanding that Devanagari numerals and conjunct characters require Unicode NFKC normalization for stable matching.

## 2. What Was Built During the Event (4 Oct 10:00 IST – 5 Oct 14:00 IST)

100% of the code, tests, fixtures, scripts, and documentation in this repository were authored during the event window.

Key systems implemented:
1. **PDF Ingestion & Page Extraction (`src/ingest.py`, `src/text_extract.py`)**: PDF metadata validation, magic bytes checking, per-page text extraction via `pypdf`, scanned document detection.
2. **Page-Aware Keyword Retrieval (`src/agent/extractor.py`)**: Scored section extraction across multi-page documents (handling 40–100 page tenders).
3. **Agentic LLM Extraction Loop & Self-Repair (`src/agent/extractor.py`)**: Structured schema extraction with SnippetVerifier citation checking and automatic repair prompt retries.
4. **Deterministic Regex Fallback (`src/regex_fallback.py`)**: Zero-dependency offline parser with Indian currency parsing (lakh/crore/paise).
5. **Deterministic Evaluator (`src/evaluator.py`)**: GFR eligibility engine checking EMD exemptions, turnover averaging, experience, similar work %, net worth, and IST-aware Class-3 DSC deadlines.
6. **FastAPI Web Service & Human-in-the-Loop UI (`src/api.py`, `frontend/index.html`)**: Interactive single-page console with field inspection, operator override, audit trace, and bilingual EN/HI toggle.
7. **Benchmarks & Test Battery**: 38 automated pytest tests, synthetic benchmark (14 docs), real LLM benchmark run, and held-out benchmark from 10 real public tenders.

## 3. AI-Generated Code Disclosure

In accordance with hackathon rules, AI coding assistants (Google Gemini and Anthropic Claude via IDE agent tooling) were utilized during the build window.

- **AI-Generated / AI-Assisted Components**:
  - Boilerplate Pydantic model definitions (`src/models.py`)
  - Initial regex pattern drafts for date and currency extraction
  - ReportLab synthetic test fixture generator script (`scripts/generate_sample_tenders.py`)
  - Test case scaffolding across `tests/`
  - CSS styling and bilingual translation dictionary in `frontend/index.html`

- **Human-Directed Architecture & Core Logic**:
  - System architecture: 2-tier extraction (LLM agent with self-repair + deterministic regex fallback)
  - Anti-hallucination citation verification gate (`SnippetVerifier.verify`)
  - Fail-closed deterministic evaluation rules and IST timezone deadline math
  - Evaluation rubric mapping and test validation suites
