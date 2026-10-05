# Held-Out Benchmark Tender Sources

The held-out evaluation suite (`assets/ground_truth_held_out.json`, `docs/BENCHMARK-heldout.md`) evaluates deterministic extraction on 10 real-world Indian public tender PDFs (64–107 pages each). Because these large PDFs are git-ignored (`sample_tenders/held_out/`), this ledger documents their origin and download sources for reproducibility.

> **Note on Verification**: Direct download URLs are tracked below. Where exact live-portal URLs were not saved in the repository, a `[CONFIRM URL]` marker is provided. Do not guess or invent URLs.

---

## Held-Out Tenders (IIT Kanpur / CPPP eProcure)

| # | Filename | Tender Reference / Title | Issuing Department & Portal | Est. Cost / EMD | Source / Download Location |
|---|---|---|---|---|---|
| 1 | `held_out/Contractdocument66.pdf` | Ref: `66/EE/Elect/2026-27`<br>Real electrical tender (66 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹9,76,430<br>EMD: ₹19,529 | [CONFIRM URL] (Search Ref `66/EE/Elect/2026-27` on eprocure.gov.in) |
| 2 | `held_out/Tenderdoc-park67.pdf` | Ref: `36/Civil/D3/2026-27`<br>Park 67 civil works (69 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹5,66,995<br>EMD: ₹11,334 | [CONFIRM URL] (Search Ref `36/Civil/D3/2026-27` on eprocure.gov.in) |
| 3 | `held_out/TenderDocAerospace.pdf` | Ref: `35/Civil/D3/2026-27`<br>Aerospace Dept civil works (65 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹3,31,501<br>EMD: ₹6,630 | [CONFIRM URL] (Search Ref `35/Civil/D3/2026-27` on eprocure.gov.in) |
| 4 | `held_out/TenderdocSBRA.pdf` | Ref: `34/Civil/D3/2026-27`<br>SBRA civil works (73 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹26,23,918<br>EMD: ₹52,478 | [CONFIRM URL] (Search Ref `34/Civil/D3/2026-27` on eprocure.gov.in) |
| 5 | `held_out/Tenderdocument.pdf` | Ref: `23/Civil/D2/2026-27`<br>Civil works tender (64 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹3,00,172<br>EMD: ₹6,003 | [CONFIRM URL] (Search Ref `23/Civil/D2/2026-27` on eprocure.gov.in) |
| 6 | `held_out/Tenderdocument47.pdf` | Ref: `47/EE/Elect/2026-27`<br>Electrical maintenance tender (66 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹3,46,157<br>EMD: ₹6,923 | [CONFIRM URL] (Search Ref `47/EE/Elect/2026-27` on eprocure.gov.in) |
| 7 | `held_out/Tenderdocument48.pdf` | Ref: `48/EE/Elect/2026-27`<br>Electrical work tender (65 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹9,19,350<br>EMD: ₹18,387 | [CONFIRM URL] (Search Ref `48/EE/Elect/2026-27` on eprocure.gov.in) |
| 8 | `held_out/Tenderdocument49.pdf` | Ref: `49/EE/Elect/2026-27`<br>Electrical work tender (66 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹4,32,894<br>EMD: ₹8,658 | [CONFIRM URL] (Search Ref `49/EE/Elect/2026-27` on eprocure.gov.in) |
| 9 | `held_out/Tenderdocument50.pdf` | Ref: `50/EE/Elect/2026-27`<br>Electrical work tender (107 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹16,72,324<br>EMD: ₹33,446 | [CONFIRM URL] (Search Ref `50/EE/Elect/2026-27` on eprocure.gov.in) |
| 10 | `held_out/Tenderdocument51.pdf` | Ref: `51/EE/Elect/2026-27`<br>Electrical work tender (74 pp) | Institute Works Department, IIT Kanpur<br>Portal: `eprocure.gov.in` | Est: ₹4,16,861<br>EMD: ₹8,337 | [CONFIRM URL] (Search Ref `51/EE/Elect/2026-27` on eprocure.gov.in) |

---

## Instructions to Reproduce Held-Out Benchmark

1. Place the 10 tender PDF files into `sample_tenders/held_out/`.
2. Run the deterministic held-out benchmark:
   ```bash
   python scripts/benchmark.py --repo . --gt assets/ground_truth_held_out.json --no-llm --md docs/BENCHMARK-heldout.md
   ```
