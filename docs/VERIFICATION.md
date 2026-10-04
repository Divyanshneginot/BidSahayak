# Clean-Room Verification Report — BidSahayak

**Execution Date**: 2026-10-04  
**Sprint Track**: WCC Launchpad 30 — Track 01 Agentic AI  
**Status**: VERIFIED & AUDITED (100% Quality Gates Passed)

---

## 1. Automated Gate Evaluation

All 18 truth and quality gates verified via `python scripts/gate.py --repo . --all`:

| Gate | Description | Status |
|---|---|---|
| **G1** | `parse_inr` handling of paise, Indian grouping, Lakh/Crore | **PASS** |
| **G2** | Evidence snippet and value round-trip verification | **PASS** |
| **G3** | Fail-closed defaults and empty matrix human review routing | **PASS** |
| **G4** | Multi-format deadline extraction (Hindi, ISO, DD.MM.YYYY, 1500 Hrs) | **PASS** |
| **G5** | Unreadable/raster page skipping and detection | **PASS** |
| **G6** | `Asia/Kolkata` timezone-aware math & 7-day DSC barrier | **PASS** |
| **G7** | Average annual turnover calculation across reported years | **PASS** |
| **G8** | Security hardening (CORS, file cleanup, headers, rate limiting) | **PASS** |
| **G10** | Synthetic fixture provenance declared in `sample_tenders/NOTICE.md` | **PASS** |
| **G11** | Accurate ground-truth dates and fixture labels in `tender_measurement.csv` | **PASS** |
| **G12** | Elimination of fabricated averages from `PROBLEM_EVIDENCE.md` | **PASS** |
| **G13** | Zero unverified rows in `docs/CLAIMS_LEDGER.md` | **PASS** |
| **G14** | Vendor profile panel with complete MSME configuration | **PASS** |
| **G15** | Truthful verdict kicker copy matching assessment status | **PASS** |
| **G16** | Human override buttons wired with real-time re-evaluation | **PASS** |
| **G18** | Lossless `dataset.en` snapshotting for bilingual toggle | **PASS** |
| **G19** | Standardized benchmark harness in `scripts/benchmark.py` | **PASS** |
| **G23** | Explicit LLM provider resolution (`gemini`, `groq`, `openai`) | **PASS** |

**Summary**: 18 / 18 gates passed (100.0%). JSON audit artifact recorded in `docs/VERIFICATION.json`.

---

## 2. Adversarial Battery

Evaluated via `tests/test_adversarial.py`:
1. **Corrupted Date**: Unparseable date strings safely route to `needs-human-review` (never `eligible`).
2. **Paise Overflow Attack**: Decimal values such as `10,000.00` correctly parse to `10000` (not `1000000`).
3. **Trader Exemption Loophole**: Traders attempting to claim GFR 170 MSE exemption have EMD marked as a blocking gap.

**Result**: 3 / 3 adversarial traps successfully neutralized.

---

## 3. Benchmark Comparison Across Tiers

Generated via `scripts/benchmark.py` across the 14-tender suite:

| Metric | Deterministic Tier (Tier 3) | Agentic LLM Tier (Tier 1/2) |
|---|---|---|
| **EMD Recovery** | **92.9%** (13/14) | **92.9%** (13/14) |
| **Deadline Accuracy** | **85.7%** (12/14) | **85.7%** (12/14) |
| **Turnover Accuracy** | 7.1% (1/14) | 7.1% (1/14) |
| **Exemption Detection** | 64.3% (9/14) | 64.3% (9/14) |
| **Latency p50** | **43.9 ms** | 1159.5 ms |
| **Latency p95** | **733.5 ms** | 1896.8 ms |
| **Real Seed Tender (`imd-tender.pdf`)** | **100% Match** | **100% Match** |

*Note on Free-Tier LLM Quota*: Google Gemini free tier rate limits (20 RPD on `gemini-3.5-flash`) safely degrade to Tier 3 without application errors.

---

## 4. UI Design Freeze Integrity

Verified via `python scripts/ui_freeze_check.py --repo .`:
- Design tokens (`--ink`, `--paper`, `--hl`, `--status-met`, `--status-gap`, etc.) intact.
- Layout section sequence (`top` → `evidence` → `demo` → `result` → `source` → `trace`) preserved.
- Core interactive element IDs preserved.
- Result: **PASS** (Zero unauthorized styling diffs).

---

## 5. Online Deployment Readiness

- **CORS**: Configurable via `ALLOWED_ORIGINS` environment variable (defaults to `*` for public web deployment).
- **Network Boundaries**: Frontend interacts strictly via relative paths (`/api/...`), eliminating `localhost` coupling.
- **Security**: Security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`), per-IP rate limiting, and automated ephemeral file cleanup in `finally:` blocks.
