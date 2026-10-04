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

## Architecture

**Put the LLM where language is ambiguous. Put deterministic code where correctness matters.**

| Step | LLM or Code? | Why |
|---|---|---|
| PDF → text | **Code** (pypdf, raster-scan detection) | Deterministic, testable, free |
| Text → requirement fields | **LLM**, schema-constrained | Language is genuinely ambiguous across 40+ phrasings |
| Fields → numbers/dates | **Code**, validating LLM output | Parse and reject anything that doesn't round-trip |
| Compare vs vendor profile | **Code — pure function** | Must be 100% predictable and testable |
| Produce the verdict | **Code** | Follows from the comparison |
| Explain in plain Hindi/English | **LLM** | Explanation is where LLMs earn their keep |

### Design Decisions

1. **The Evaluator is deterministic.** Same inputs → same verdict, always. An LLM deciding eligibility is a bug factory.
2. **No snippet → not shown as fact.** Every extracted field must cite a verifiable source page and snippet. If it can't, it's flagged `needs-human-review`. This is also my prompt-injection defence.
3. **"Never confidently wrong" over "always answers."** The system prefers `needs-human-review` over guessing. Fields below confidence 0.7 are excluded from the verdict until a human confirms.
4. **Four human gates, not one vague "review" screen.** Profile confirmation, extraction review, verdict sign-off, draft release.
5. **There is no code path that submits a bid.** Not to CPPP, not to GeM, not anywhere.

### How the Human Stays in Control

- **Per-field approve/override** — every extracted requirement shows value, confidence, and source snippet. Disagree → type correction → verdict recomputes.
- **Confidence gating** — fields below 0.7 render amber and are excluded from the verdict until confirmed.
- **Audit log** — every agent action, every human override, every timestamp, visible in a "What did the agent do?" panel.
- **No auto-submit, hard-coded.** There is no API client for CPPP or GeM submission in this codebase.

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env with your LLM API key

# 3. Run the server
python -m uvicorn src.api:app --reload

# 4. Run tests
pytest tests/ -v
```

## Live URL

> *Will be added at deployment (hour 20–24)*

## Benchmark Results (14-document suite)

Regenerate with `python scripts/benchmark.py --repo . --no-llm --md docs/BENCHMARK.md`.
Ground truth lives in `assets/ground_truth.json` and is read from the documents, never from the pipeline.

| Field | Correct | Of | Accuracy | Threshold |
|---|---|---|---|---|
| EMD amount | 13 | 13 | **100%** | ≥ 90% |
| Submission deadline | 13 | 14 | **93%** | ≥ 80% |
| Minimum turnover | 14 | 14 | **100%** | ≥ 70% |
| MSE exemption stated | 14 | 14 | **100%** | ≥ 90% |

*Latency:* p50 33 ms · p95 85 ms (deterministic tier, single machine, no API key).
One document's EMD is excluded from the denominator: `aiims_ppe_supply.pdf` states **two** competing
figures (₹40,00,000 and ₹40,000), so the correct output there is human review, not a number.

**Tier note.** These figures are the **deterministic tier** (no LLM). The LLM tier was not run in this
environment because no API key was configured; when a key is present, run `python scripts/benchmark.py --repo .`
and it reports the provider, the resolved model, and — per document — which tier actually answered
(`last_tier`) plus any `fallback_reason`. A run in which any document reports `tier=3` is a fallback run and
must not be published as an LLM result.

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
