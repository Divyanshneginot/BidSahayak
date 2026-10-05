# Extraction benchmark

Generated `2026-10-05 17:17:41+0530` from commit `b26d2ef` · tier: **deterministic (no API key)** · 14 documents.

Ground truth: `assets/ground_truth.json` — read from the documents, never from the pipeline.

| Field | Correct | Of | Accuracy | Threshold |
|---|---|---|---|---|
| emd | 13 | 13 | 100% | 90% |
| deadline | 14 | 14 | 100% | 80% |
| turnover | 14 | 14 | 100% | 70% |
| exemption | 14 | 14 | 100% | 90% |

Latency: p50 25 ms · p95 59 ms (single machine, deterministic (no API key) tier).

## Document Results

| Document | Tier | EMD | Deadline | Turnover | Exemption | Time (s) |
|---|---|---|---|---|---|---|
| `imd-tender.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 1.28s |
| `mtd_goods_nic.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.03s |
| `up_pwd_road_works.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.02s |
| `karnataka_jjm_water.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.02s |
| `bccl_coal_handling.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.03s |
| `upneda_solar_lights.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.02s |
| `aiims_ppe_supply.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.02s |
| `smart_classroom_displays.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.02s |
| `cpwd_facility_management.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.03s |
| `nicsi_cloud_maintenance.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.03s |
| `up_jal_nigam_hindi.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.03s |
| `scanned_police_housing.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.01s |
| `nhai_highway_toll.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.06s |
| `tn_highways_short_deadline.pdf` | Tier 3 | ✓ | ✓ | ✓ | ✓ | 0.02s |

## Misses

None — all compared fields matched ground truth on this run.
