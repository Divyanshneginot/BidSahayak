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

## Benchmark Results (14-Tender Suite)
Generated directly via `python scripts/benchmark.py --repo . --no-llm --md docs/BENCHMARK.md`:

- **Suite**: 1 real seed tender (`imd-tender.pdf`, NIT CPU/52/0519/9913) + 13 synthetic fixtures derived from GFR 2017 & state templates.
- **Deterministic Tier Performance**:
  - EMD Recovery: **13 / 14 (92.9%)**
  - Deadline Accuracy: **12 / 14 (85.7%)**
  - Exemption Detection: **9 / 14 (64.3%)**
  - Latency: **p50 = 43.9 ms · p95 = 733.5 ms**
  - **IMD Real Seed Tender**: **100% match** (EMD: ₹10,000, Deadline: 2019-06-24, Turnover: ₹20,00,000, Micro Exemption: Verified)

### Known Failure Modes & Limitations
1. **Scanned / Raster Documents**: Documents lacking a machine-readable text layer (`scanned_police_housing.pdf`) are flagged as unreadable pages and routed to human review rather than guessing.
2. **Unstated Deadlines**: PSU documents that do not state a concrete bid submission date (`bccl_coal_handling.pdf`) correctly yield `None` rather than a hallucinated date.
3. **Complex Multi-Year Turnover Clauses**: Complex turnover clauses requiring financial statement reconciliation require human confirmation.
4. **Deterministic Resilience**: The app works out of the box with zero external LLM API keys via the deterministic fallback engine.

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
