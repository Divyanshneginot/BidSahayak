# Extraction benchmark

Generated `2026-10-04 21:57:28+0530` from commit `4954f4c` · tier: **llm+deterministic** · 14 documents.

Ground truth: ssets/ground_truth.json — read from the documents, never from the pipeline.

| Field | Correct | Of | Accuracy | Threshold |
|---|---|---|---|---|
| emd | 11 | 13 | 85% | 90% |
| deadline | 11 | 14 | 79% | 80% |
| turnover | 12 | 14 | 86% | 70% |
| exemption | 13 | 14 | 93% | 90% |

Latency: p50 25877 ms · p95 32902 ms (single machine, llm+deterministic tier).

## Document Results

| Document | Tier | EMD | Deadline | Turnover | Exemption | Time (s) |
|---|---|---|---|---|---|---|
| `imd-tender.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 20.87s |
| `mtd_goods_nic.pdf` | Tier 1 | ✗ | ✗ | ✗ | ✗ | 33.33s |
| `up_pwd_road_works.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 6.45s |
| `karnataka_jjm_water.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 20.12s |
| `bccl_coal_handling.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 27.41s |
| `upneda_solar_lights.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 25.88s |
| `aiims_ppe_supply.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 19.07s |
| `smart_classroom_displays.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 27.07s |
| `cpwd_facility_management.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 26.36s |
| `nicsi_cloud_maintenance.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 19.06s |
| `up_jal_nigam_hindi.pdf` | Tier 1 | ✓ | ✗ | ✓ | ✓ | 27.92s |
| `scanned_police_housing.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 25.45s |
| `nhai_highway_toll.pdf` | Tier 1 | ✗ | ✗ | ✗ | ✓ | 32.90s |
| `tn_highways_short_deadline.pdf` | Tier 1 | ✓ | ✓ | ✓ | ✓ | 3.57s |

## Misses

| Document | Field | Extracted | Ground truth |
|---|---|---|---|
| `mtd_goods_nic.pdf` | emd | `None` | `100000` |
| `mtd_goods_nic.pdf` | deadline | `None` | `2026-10-24` |
| `mtd_goods_nic.pdf` | turnover | `None` | `2500000` |
| `mtd_goods_nic.pdf` | exemption | `False` | `True` |
| `up_jal_nigam_hindi.pdf` | deadline | `None` | `2026-10-21` |
| `nhai_highway_toll.pdf` | emd | `None` | `1000000` |
| `nhai_highway_toll.pdf` | deadline | `None` | `2026-11-02` |
| `nhai_highway_toll.pdf` | turnover | `None` | `20000000` |
