# BidSahayak — WCC Launchpad 30 Submission Package

> **Track:** 01 — Agentic AI (Primary)  
> **Project:** BidSahayak  
> **Submission Deadline:** 5 October 2026, 14:00 IST (Build closes 16:00 IST)  
> **One Entry Policy:** Submitted by Team Leader only.

---

## 1. Submission Items Checklist

- [x] **Problem Statement**: Sourced directly from CAG audits and Budget 2026 MSME policy data.
- [x] **Repository URL**: Clean Git history with 7+ small, descriptive commits.
- [x] **Empirical Evidence**: `PROBLEM_EVIDENCE.md` with CAG UP (73%), TN (62.39%), JJM (24.4%), PSU (₹22.24 Cr), and Budget 2026 Corporate Mitra math.
- [x] **14 Tender Measurement Benchmark**: `tender_measurement.csv` (14/14 rows filled) + `sample_tenders/*.pdf` (all 14 documents present).
- [x] **Automated Test Suite**: 25+ pytest unit and regression tests passing cleanly.
- [x] **Evaluation Benchmark**: `evals/run_evals.py` generating 14/14 verified extraction metrics.
- [x] **Interactive Human-in-the-Loop UI**: Single-screen UI with EN/HI toggle, dark theme, trace panel, and operator override.
- [x] **Rule 04 Disclosure**: `PRIOR_WORK.md` disclosing pre-event domain knowledge with zero prior code reuse.
- [x] **Security Sweep**: Zero credentials or API keys in Git history.
- [ ] **Live Deployed URL**: [Deploy to Render / Railway using `render.yaml` or `Dockerfile`]
- [ ] **2:30 Demo Video**: [Record following script below and upload to YouTube/Loom]

---

## 2. 2:30 Demo Video Script & Walkthrough

| Timestamp | Screen / Visual | Voiceover / Script Beat | Rubric Category Hit |
|---|---|---|---|
| **0:00 – 0:20** | Landing Page hero + CAG statistic card | *"In Uttar Pradesh, 73% of road tenders receive only 1 or 2 bids — not because contractors can't do the work, but because eligibility is buried in 30-page documents. That information wall is what BidSahayak breaks."* | **User Insight & Problem Evidence (15 pts)** |
| **0:20 – 0:40** | Real IMD Tender PDF ([sample_tenders/imd-tender.pdf](sample_tenders/imd-tender.pdf)) | *"Here is a real tender from the Meteorological Department. Clause 5 says EMD is ₹10,000. But the exemption for micro-enterprises is 5 pages away in Clause 6(a), subject to trading restrictions and opening-date validity."* | **Originality & Real-World Usability (15+12 pts)** |
| **0:40 – 1:10** | **Live Action:** Drop PDF into BidSahayak console | *"Watch the agent work. In 3 seconds, it normalizes Devanagari and English with NFKC, maps sections, and extracts structured fields."* | **Core Solution Strength (24 pts)** |
| **1:10 – 1:35** | Click source snippet citation link | *"Notice the trust layer: every field links directly to its source page and verbatim snippet. If a snippet isn't on the page, the agent refuses to guess and flags it for human review."* | **Technical Depth & Anti-Hallucination (24 pts)** |
| **1:35 – 2:00** | Verdict Card + GFR 170 Exemption | *"Against our vendor profile, the pure deterministic rules engine delivers the verdict: Eligible with Gaps. The contractor discovers they are 100% exempt from EMD under GFR Rule 170."* | **Technical Depth & GFR Rules Engine (24 pts)** |
| **2:00 – 2:15** | **Human Override:** Edit a field | *"The human remains the operator. An officer overrides a turnover clause from an addendum; the engine recomputes instantly and logs the change to the audit trace."* | **Responsible Design & Human-in-the-Loop (10 pts)** |
| **2:15 – 2:30** | Audit Trace Lane + 14-Tender Benchmark | *"Zero hallucination, 14 verified tenders in our benchmark, bilingual Hindi/English. BidSahayak scales public procurement support to India's 7.6 crore MSMEs."* | **Wrap-up & Jury Impact (100 pts)** |

---

## 3. Quickstart Command for Judges

```bash
# 1. Clone repository
git clone https://github.com/<your-username>/BidSahayak.git
cd BidSahayak

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run automated tests (25 tests)
pytest tests/ -v

# 4. Run evaluation benchmark across 14 tenders
python evals/run_evals.py

# 5. Launch local server & interface
python -m uvicorn src.api:app --reload --port 8000
# Open http://localhost:8000
```
