# BidSahayak Benchmark — Tier 3 (Deterministic Regex Fallback)

- **Evaluated**: 14 documents
- **EMD Recovery**: 12/14 (85.7%)
- **Deadline Accuracy**: 4/14 (28.6%)
- **Turnover Accuracy**: 1/14 (7.1%)
- **Exemption Detection**: 13/14 (92.9%)
- **Latency**: p50 = 36.8 ms · p95 = 672.4 ms

| Document | EMD OK | Deadline OK | Turnover OK | Exemption OK | Time (s) |
|---|---|---|---|---|---|
| `aiims_ppe_supply.pdf` | ✗ | ✗ | ✗ | ✓ | 0.04s |
| `bccl_coal_handling.pdf` | ✓ | ✓ | ✗ | ✓ | 0.04s |
| `cpwd_facility_management.pdf` | ✓ | ✗ | ✗ | ✓ | 0.03s |
| `imd-tender.pdf` | ✗ | ✗ | ✓ | ✓ | 0.67s |
| `karnataka_jjm_water.pdf` | ✓ | ✓ | ✗ | ✓ | 0.04s |
| `mtd_goods_nic.pdf` | ✓ | ✓ | ✗ | ✓ | 0.03s |
| `nhai_highway_toll.pdf` | ✓ | ✗ | ✗ | ✗ | 0.07s |
| `nicsi_cloud_maintenance.pdf` | ✓ | ✗ | ✗ | ✓ | 0.04s |
| `scanned_police_housing.pdf` | ✓ | ✗ | ✗ | ✓ | 0.03s |
| `smart_classroom_displays.pdf` | ✓ | ✗ | ✗ | ✓ | 0.03s |
| `tn_highways_short_deadline.pdf` | ✓ | ✗ | ✗ | ✓ | 0.03s |
| `up_jal_nigam_hindi.pdf` | ✓ | ✗ | ✗ | ✓ | 0.04s |
| `up_pwd_road_works.pdf` | ✓ | ✗ | ✗ | ✓ | 0.03s |
| `upneda_solar_lights.pdf` | ✓ | ✓ | ✗ | ✓ | 0.03s |
