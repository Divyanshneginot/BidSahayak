# BidSahayak Claims & Verification Ledger

Every public claim in this repository is tracked here with its audit status, evidence source, and verification method.

| Claim ID | Public Claim | Prior State | Action Taken | Current Provenance / Artifact | Status |
|---|---|---|---|---|---|
| CLM-01 | "14 live tender documents analyzed" | Stated all 14 were live downloads from 4 Oct 2026 | Clarified | 1 real seed public tender (`imd-tender.pdf`) + 13 synthetic fixtures. Detailed in `sample_tenders/NOTICE.md`. | VERIFIED |
| CLM-02 | "Mean 34.2 pages, 11.4 days, 5.8 pages separation" | Stated as broad statistical sample mean | Deleted | Removed from `PROBLEM_EVIDENCE.md` §4; replaced with qualitative structural patterns. | VERIFIED |
| CLM-03 | "14/14 (100%) extraction accuracy across all fields" | Claimed 100% on all fields | Softened & Measured | Replaced with reproducible benchmark in `docs/BENCHMARK.md` (EMD: 85.7%, Exemption: 92.9%). | VERIFIED |
| CLM-04 | "Zero Confident Hallucinations / 0 Confident Errors" | Theoretical claim | Softened | Replaced with explicit human-review routing on unverified/low-confidence snippets. | VERIFIED |
| CLM-05 | "OCR fallback for raster images" | Listed in architecture table | Corrected | Removed OCR claim; unreadable/raster pages are honestly flagged as `skipped_pages` and routed to human review. | VERIFIED |
| CLM-06 | "CAG UP 73% single-bidding statistic" | Sourced to CAG Report No. 4 of 2017 | Preserved | Verifiable in CAG UP Report No. 4 of 2017 cited in `PROBLEM_EVIDENCE.md` §1. | VERIFIED |
| CLM-07 | "CAG TN 62.39% single-bidding statistic" | Sourced to CAG Report No. 4 of 2023 | Preserved | Verifiable in CAG TN eProcurement Report cited in `PROBLEM_EVIDENCE.md` §1. | VERIFIED |
| CLM-08 | "CAG JJM 24.4% single-tender approvals" | Sourced to CAG Karnataka Report April 2026 | Preserved | Verifiable in published CAG JJM report cited in `PROBLEM_EVIDENCE.md` §1. | VERIFIED |
| CLM-09 | "CAG Union Commercial ₹22.24 Cr paperwork rejections" | Sourced to CAG Report No. 14 of 2025 | Preserved | Verifiable in CAG Report No. 14 of 2025 cited in `PROBLEM_EVIDENCE.md` §1. | VERIFIED |
| CLM-10 | "GeM ₹20 Lakh Crore cumulative GMV, 45.6% to MSEs" | Sourced to GeM / PIB 7 Aug 2026 | Preserved | Verifiable in official PIB/GeM statistics cited in `PROBLEM_EVIDENCE.md` §2. | VERIFIED |
| CLM-11 | "GFR 2017 Rule 170 mandatory EMD exemption for MSEs" | Statutory rule citation | Preserved | Verifiable in Department of Expenditure General Financial Rules 2017. | VERIFIED |
| CLM-12 | "3 to 7 days Class 3 DSC issuance vs short tender deadlines" | CA issuance latency arithmetic | Preserved | Verifiable in Certifying Authority turnaround times and Haryana IS Audit 2026. | VERIFIED |
| CLM-13 | "Zero bid auto-submission" | Architecture design constraint | Preserved | Codebase contains zero API clients or submission endpoints to CPPP or GeM. | VERIFIED |

**Summary**: 13/13 claims verified or adjusted to truth. 0 unverified claims remaining.
