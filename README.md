# BidSahayak

> **Small Indian contractors find government tenders they could win, then abandon them — not because they can't do the work, but because eligibility is buried in 20–60 page documents written in dense officialese.**
>
> BidSahayak reads the tender and answers the only question that matters before you invest two days: **can I bid for this, and what's missing?**

## The Workflow

```
PDF in → requirement matrix → verdict against vendor profile → human approves every field
```

No scraping. No alerting. No accounts. No pricing page. No mobile app.  
If it isn't in that chain, it doesn't exist.

## Track

**01 — Agentic AI** · WCC Launchpad 30 · 4–5 Oct 2026  
**Demo Video:** [BidSahayak YouTube Demo](https://youtu.be/7W3jbwHY0yM)

## Architecture

**Put the LLM where language is ambiguous. Put deterministic code where correctness matters.**

| Step | LLM or Code? | Why |
|---|---|---|
| PDF → text | **Code** (pypdf, raster-scan detection) | Deterministic, testable, free |
| Page-aware section retrieval | **Code** (keyword scoring) | Scans 40–100 page tenders to extract critical ITB/EMD/turnover sections |
| Text → requirement fields | **LLM (Tier 1)**, schema-constrained | Language is genuinely ambiguous across 40+ phrasings |
| Citation verification | **Code** (SnippetVerifier) | Verifies verbatim snippet on cited page; fails closed on hallucinations |
| Agentic repair loop | **LLM (Tier 1)** | On verification failure, calls REPAIR_PROMPT_TEMPLATE (max 2 retries) |
| Regex fallback | **Code (Tier 3)** | Deterministic offline parser if no API key or verification retries exhausted |
| Compare vs vendor profile | **Code — pure function** | Must be 100% predictable, testable, and compliant with GFR 2017 |
| Produce the verdict | **Code** | Follows from comparison (EMD, turnover, similar work, net worth, DSC window) |

### Design Decisions

1. **The Evaluator is deterministic.** Same inputs → same verdict, always. An LLM deciding eligibility is a bug factory.
2. **No snippet → not shown as fact.** Every extracted field must cite a verifiable source page and snippet. If it can't, it's flagged `needs-human-review`.
3. **"Never confidently wrong" over "always answers."** The system prefers `needs-human-review` over guessing. `CONFIDENCE_THRESHOLD` is read from env (default 0.70).
4. **Human in the loop.** Operator can approve/override any field via the UI; overriding clears the field from `unresolved_fields` and instantly recomputes the verdict.
5. **There is no code path that submits a bid.** Not to CPPP, not to GeM, not anywhere.

### How the Human Stays in Control

- **Per-field approve/override** — every extracted requirement shows value, confidence, and source snippet. Disagree → type correction → verdict recomputes.
- **Confidence gating** — fields below threshold render amber and are excluded from the verdict until confirmed.
- **Audit log** — every agent step (initial call, repair attempts, fallback, human overrides) logged to audit trace.
- **No auto-submit, hard-coded.** There is no API client for CPPP or GeM submission in this codebase.

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env with your LLM API key (Groq, Gemini, or OpenAI)

# 3. Run the server
python -m uvicorn src.api:app --reload

# 4. Run tests (38 tests)
pytest tests/ -v
```

## Live URL

> *Will be added at deployment (hour 20–24)*

## Benchmark Results

### 1. Deterministic Tier Benchmark (14 Synthetic + Seed Documents)
Regenerate with `python scripts/benchmark.py --repo . --no-llm --md docs/BENCHMARK.md`.
Ground truth lives in `assets/ground_truth.json` and is read from the documents, never from the pipeline.

| Field | Correct | Of | Accuracy | Threshold |
|---|---|---|---|---|
| EMD amount | 13 | 13 | **100%** | ≥ 90% |
| Submission deadline | 13 | 14 | **93%** | ≥ 80% |
| Minimum turnover | 14 | 14 | **100%** | ≥ 70% |
| MSE exemption stated | 14 | 14 | **100%** | ≥ 90% |

*Latency:* p50 33 ms · p95 85 ms (deterministic tier, single machine, no API key).

### 2. Real LLM-Tier Benchmark Run (`docs/BENCHMARK-llm.md`)
Run with active LLM API key: `python scripts/benchmark.py --repo . --md docs/BENCHMARK-llm.md`.
- **Tier 1 (Agentic LLM Extraction)** ran on all 14 documents with zero fallbacks to Tier 3.
- Accuracy: EMD 85%, Deadline 79%, Turnover 86%, Exemption 93% (p50: 25.8s per tender).

### 3. Held-Out Benchmark from 10 Real Public Tenders (`docs/BENCHMARK-heldout.md`)
Run against 10 real public tenders (64–107 pages each, from IIT Kanpur / CPPP) with zero regex tuning:
`python scripts/benchmark.py --repo . --gt assets/ground_truth_held_out.json --no-llm --md docs/BENCHMARK-heldout.md`
- Results: EMD 10/10 (100%), Deadline 9/10 (90%), Turnover 10/10 (100%), Exemption 10/10 (100%).
- 1 honest miss on `Contractdocument66.pdf` (got '2026-10-08', want None).

### Known Failure Modes & Limitations
1. **Unreadable text layers.** A page whose text layer is tofu/near-empty is reported in `skipped_pages`, excluded from analysis, and surfaced in the UI — never guessed at.
2. **Unstated values.** Where a document states no deadline (`bccl_coal_handling.pdf`) the field is `None` and the field is listed in `unresolved_fields`, routing the verdict to human review instead of inventing a date. Where no turnover clause exists (`tn_highways_short_deadline.pdf`) the value is `None` — a value the earlier CSV asserted but the document does not contain.
3. **Contradictory clauses.** Two competing figures for one field (AIIMS EMD) force human review rather than a confident pick.
4. **Word-unit turnover only in English/Hindi.** "20 crore" and "₹20,00,00,000" are handled; other regional numeral scripts are not.
5. **No OCR.** Image-only pages are skipped rather than transcribed; `is_ocr_available` reports this in the API response.

## Honest Limits

- Sample size: 1 real seed tender + 13 representative fixtures
- Audit data sources: CAG reports 2017–2026
- Verdicts not validated against a real procurement decision
- Rules encode GFR 2017 + PPP for MSEs 2012 as published; a tender may lawfully deviate
- Advisory only — verify against the original tender document before bidding

## AI Tools Used

**AI tools used during the build window:** Google Gemini, GitHub Copilot. Used for: generating implementation from specifications I wrote, drafting test cases from my specs, explaining library APIs, and reviewing extraction prompts. All architecture decisions, the eligibility rule set (derived from GFR 2017 and the Public Procurement Policy for MSEs 2012), the human-in-the-loop gate design, and the evaluation harness were designed by me. No AI output was committed without being read, tested, and understood by me.

## License

MIT
