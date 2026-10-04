# Extraction benchmark

Generated `2026-10-04 21:48:00+0530` from commit `4954f4c` · tier: **deterministic (no API key)** · 10 documents.

Ground truth: ssets/ground_truth_held_out.json — read from the documents, never from the pipeline.

| Field | Correct | Of | Accuracy | Threshold |
|---|---|---|---|---|
| emd | 10 | 10 | 100% | 90% |
| deadline | 9 | 10 | 90% | 80% |
| turnover | 10 | 10 | 100% | 70% |
| exemption | 10 | 10 | 100% | 90% |

Latency: p50 2321 ms · p95 4594 ms (single machine, deterministic (no API key) tier).

## Document Results

| Document | Tier | EMD | Deadline | Turnover | Exemption | Time (s) |
|---|---|---|---|---|---|---|
| `held_out/Contractdocument66.pdf` | Tier 3 | ✓ | ✗ | ✓ | ✓ | 2.93s |
| `held_out/Tenderdoc-park67.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 4.64s |
| `held_out/TenderDocAerospace.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 4.59s |
| `held_out/TenderdocSBRA.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 4.58s |
| `held_out/Tenderdocument.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 2.25s |
| `held_out/Tenderdocument47.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 1.42s |
| `held_out/Tenderdocument48.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 1.61s |
| `held_out/Tenderdocument49.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 1.83s |
| `held_out/Tenderdocument50.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 2.32s |
| `held_out/Tenderdocument51.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 1.95s |

## Misses

| Document | Field | Extracted | Ground truth |
|---|---|---|---|
| `held_out/Contractdocument66.pdf` | deadline | `2026-10-08` | `None` |
