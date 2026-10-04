# PROBLEM_EVIDENCE.md — repo file template

> This goes in your repo. Fill it in on 4 Oct, hours 1–3.
> It is the **User insight and problem evidence (15 pts)** artefact. Almost no team will
> have one. Every number in here must come from `prep/EVIDENCE_PACK.md` (with its URL) or
> from your own `tender_measurement.csv`. **Nothing invented.**

---

## Method

We did not conduct user interviews inside the 30-hour window, and we say so plainly rather
than implying otherwise. Instead our evidence is three-tiered:

1. **Official audit data** — Comptroller and Auditor General of India (CAG) reports on state
   e-procurement systems, which document low bidder participation with percentages.
2. **Peer-reviewed research** — a hand-collected dataset of 1,000 CPPP tenders, and an
   academic study of MSME participation barriers.
3. **Our own measurement** — 14 live tender documents downloaded from CPPP/GeM on 4 Oct 2026,
   measured by hand for document length and for how dispersed their eligibility conditions
   are. Raw data in `tender_measurement.csv`, source PDFs in `sample_tenders/`.

---

## 1. The problem, in the government's own numbers

**Uttar Pradesh — CAG Report No. 4 of 2017, Contract Management in Road Works:**

> *"majority of tenders (**73 per cent**) were not competitive where only one or two bids were
> received, **despite the existence of large number of registered contractors in each
> district**."*

- Of 802 test-checked contract bonds (2011–16), **110 worth ₹303.64 crore (14%) were awarded
  on a single bid** — *"in none of these cases, retendering was done."*
- In one sample: single bids in 15% of cases, two bids in 60% — *"the number of bids received
  against NITs in **75 per cent** cases was only one or two."*

**Tamil Nadu — CAG Report No. 4 of 2023, eProcurement:**

> *"in 0.84 lakh tenders (**62.39 per cent**) out of 1.34 lakh tenders which received valid
> bids, only one or two bids were received **indicating poor bidder participation**."*

- Sample covered 14 procuring entities = **76% of published tenders (1.32 lakh)** and **71%
  of total tender value (₹1.52 lakh crore)**.
- **₹3,328.49 crore of EMD was collected from 2.17 lakh bidders through offline mode** across
  0.98 lakh tenders. CAG notes delayed refunds mean *"accumulation of funds not belonging to
  the procuring entity."*

**Haryana — CAG Report No. 3 of 2026, Information System Audit of e-Procurement:**

- **3,887 of 12,930 tenders (30.06%)** allowed **less than seven days** for bid submission.
- **5,621 cases (37.31%)** — corrigenda issued without sufficient time to respond,
  *"thereby reducing competition."*
- **Single financial bids opened in 6,895 tenders**, all awarded to the single bidder.

**The pattern is consistent across three states and a decade of audits.** The critical clause
is the UP one: *despite large numbers of registered contractors existing.* Eligible vendors
are present. They are not bidding.

---

## 2. Why — the mechanism

**IJARIIT, "Challenges before Micro, Small and Medium Enterprises":**

> *"Many of the MSMEs are **not aware** that if they are registered with National Small
> Industries Corporation Ltd. they will have an **exemption in EMD and Security Deposit**.
> The majority of government tenders prescribe **high eligibility criteria such as annual
> turnover, past experience etc which deters** participation... One of the key constraining
> factors becomes **awareness** and therefore **lack of knowledge to utilise these
> effectively**."*

**The Leap Journal** — 1,000 randomly sampled awarded CPPP e-tenders, roads and water, five
states, 2018–19. Fraction of tenders receiving enough bids to meet normative competition
thresholds:

| | Maharashtra | Uttar Pradesh | Tamil Nadu | Odisha | Kerala |
|---|---|---|---|---|---|
| Roads | 5% | 5% | **0%** | 34% | 1% |
| Water | 14% | 7% | 1% | 8% | **0%** |

**European Court of Auditors** (corroboration that this is a mechanism, not a local quirk):
**>40% of procurement practitioners cited restrictive criteria or requirements** as the
primary cause of single-bidding — *not* a shortage of suppliers. Named barriers: *"overly
technical specifications, lengthy pre-qualification requirements, compressed timelines, and
burdensome documentation demands... particularly for smaller suppliers, who lack the
administrative capacity to navigate them."* The **Open Contracting Partnership**, analysing
3.5 million contracts, found every additional item of information shared about a tender
**decreases** single-bid risk.

**SIDBI, "Understanding Indian MSME Sector" (May 2025):** *"lack of awareness about the
benefits of registration and anticipation of regulatory scrutiny inhibited **~35% of
respondents** from registering"* on Udyam/UAP at all.

> **Both directions are the same failure.** Vendors are deterred by criteria they haven't
> read, and miss exemptions they already qualify for. That is an information problem — which
> is exactly what an agent that reads the document and compares it to your profile solves.

---

## 3. Our own measurement

*Fill from `tender_measurement.csv`. Example sentences — use your real numbers:*

> We measured **14 active tender documents** downloaded from CPPP and GeM on 4 Oct 2026.
> Eligibility conditions appeared in a mean of **X.X separate sections** per document
> (range X–X) — across the main body, annexures, corrigenda and special conditions.
> Mean document length was **XX pages** (range X–XX).
> **EMD exemption for registered MSEs was stated in N of 14 documents**, and in every case
> in a *different sub-clause* from the EMD requirement itself.
> The mean window between publication and deadline was **XX days**, minimum **X days** —
> in some cases less time than it takes to obtain a Class 3 DSC (3–7 days per CPPP's own
> guidance).
> **N of 14** had no machine-readable text layer at all.

Then, once the extractor works:

> Across the same 14 documents our extractor recovered the EMD amount correctly in **N/14**,
> the deadline in **N/14**, and the turnover requirement in **N/14**. Where it could not
> extract with confidence it returned `needs-human-review` rather than guessing — **M/14**
> cases. Raw results in `tender_measurement.csv`; source PDFs in `sample_tenders/`.

---

## 4. Who this is for

| | |
|---|---|
| Registered MSMEs in India | **7,61,12,097** (7.61 crore) as of 31 Jan 2026 — Ministry of MSME Annual Report 2025–26 |
| Of which **micro** enterprises | ~99%. Only **41,641** medium enterprises in the entire country |
| **Uttar Pradesh** | **86,03,272** registered MSMEs — the second-largest base of any state |
| Activity split | Trading 42.2% · Services 37.6% · Manufacturing 20.1% |
| MSME contribution | ~31.1% of GDP, 48.58% of exports, ~32.8 crore livelihoods |
| MSEs on GeM | **11+ lakh registered**; executed **68% of FY 2025–26 orders**, **47.1% of GMV** (₹2.36 lakh crore) |
| GeM scale | **₹18.4 lakh crore** cumulative GMV; **>₹5 lakh crore** in FY 2025–26; 1.64 lakh+ buyer organisations |
| Public procurement overall | **20–30% of GDP** (₹20–25 lakh crore / ~$500–600bn annually) |

**These are the people who are being told they get 25% of central procurement by law, and
who mostly don't know how to claim it.**

---

## 5. What they are entitled to and don't know

Mandatory under the **Public Procurement Policy for MSEs Order, 2012** (notified under s.11
of the MSMED Act 2006; 25% target mandatory from 1 April 2019):

- **Minimum 25%** of annual central procurement from MSEs — within it **4% for SC/ST-owned**
  and **3% for women-owned**
- **358 items reserved** for exclusive purchase from MSEs — large enterprises cannot bid
- **EMD exemption** and **free tender documents** for Udyam-registered Micro and Small
  enterprises (GFR 2017 **Rule 170**), on submitting a Bid Security Declaration instead
- **L1 + 15% purchase preference** — an MSE quoting within 15% of the lowest bid may match L1
  and supply **up to 25% of the tendered value**
- **GFR Rule 173** — DPIIT-recognised startups get EMD, prior-turnover *and* prior-experience
  relaxation, **but only where the NIT includes the clause**. You have to read the NIT to
  find out.

**The conditionals are the problem.** EMD exemption depends on: Micro-vs-Small-vs-**Medium**
(medium is *not* exempt) × Udyam registration validity on the date of bid opening × whether
the certificate covers the tendered item × whether the NIT includes the startup clause ×
which state (West Bengal is only partial; Maharashtra adds 5% preference beyond the central
15%) × which portal (GeM vs CPPP) × whether it's a manufacturing or a **trading** bid. That
is a decision tree nobody can hold in their head while also running a business.

---

## 6. What it costs to solve this today

| Route | Cost / friction |
|---|---|
| Tender agent or consultant | ~**₹3,000–15,000 per bid**, or a % of contract value *(verify current rates — screenshot 3–5 listings and commit them to `evidence/`)* |
| Class 3 DSC (mandatory for CPPP) | **₹2,000–3,000**, and CPPP's own guidance says CAs take **3–7 days** to issue. Commercial providers quote ₹800–2,500 and 1–2 days. Max validity 2 years. |
| Tender document fee | Free for MSEs; **₹500–5,000** otherwise |
| State portal registration | **₹1,000–10,000** depending on state; admin approval can take 24–72 hours |
| EMD, if not exempt | **2–5% of estimated contract value**, as BG/FDR/DD, valid 45+ days beyond bid validity (one IMD tender specifies **240 days**) |
| Reading it yourself | **XX pages** across **X.X sections**, in officialese — our measurement above |

Note the compounding: a vendor who needs a DSC (3–7 days) facing a tender with **less than
seven days** to bid — which CAG found in **30.06%** of Haryana tenders — mathematically
cannot participate. That is not a motivation problem. It is an arithmetic one.

---

## 7. What exists today and why it isn't enough

| Current option | Why it fails |
|---|---|
| Reading the tender yourself | XX pages, X.X separate sections, three exceptions per requirement, plus annexures |
| Tender agent / consultant | Correct answer, unaffordable at ₹3,000–15,000 per bid for a micro enterprise |
| Portal browsing / alert tools | Tell you a tender **exists**. Say nothing about whether **you** qualify. Keyword matching only |
| Google search | Finds the notice, not the eligibility verdict |
| GeM's own dashboard | Shows opportunities, doesn't reason about your documents against the NIT |

**The gap:** everyone helps you *find* tenders. Nobody helps a small vendor work out *whether
they can win one*, and what paperwork stands between them and submitting.

---

## 8. Honest limits of our research

> **Keep this section.** It is worth Responsible-Design points, not costs. Judges reward
> knowing your limits far more than they punish having them.

- We conducted **no direct user interviews** inside the 30-hour window. Our user evidence is
  documentary and statistical, plus our own measurement of tender documents. We would
  normally validate with 8–10 vendors and could not in this timeframe.
- Our document sample is **14**. It is small, and it skews toward [sectors/states you
  actually picked]. It is not a national survey and we don't present it as one.
- The CAG audit data covers **UP 2011–16, Tamil Nadu ~2023, Haryana ~2024** — real and
  official, but not current-year.
- Some statistics come from secondary aggregators reporting Ministry of MSME / PIB figures;
  where sources disagreed we used the government source and noted the discrepancy.
- Our eligibility verdicts are **advisory**. We have not validated them against a real
  procurement decision or a real awarded contract.
- Procurement rules vary by state, portal and department, and change. Our rules encode GFR
  2017 and the PPP for MSEs Order 2012 as published; a tender may lawfully deviate.
- **The product must never auto-submit a bid.** There is no code path that does so.

---

## Sources

*Full list with URLs in `prep/EVIDENCE_PACK.md`. Cite CAG, PIB, DD News, Ministry of MSME,
GFR 2017 and academic papers — not commercial tender blogs, several of which publish
mutually inconsistent figures.*

- CAG Report No. 4 of 2017 — Contract Management in Road Works, Government of Uttar Pradesh
- CAG Report No. 4 of 2023 — eProcurement, Government of Tamil Nadu
- CAG Report No. 3 of 2026 — Information System Audit of e-Procurement, Haryana
- CAG 2023 — Chapter V, Collusive Bidding and Cartelisation in Tendering
- The Leap Journal (2022) — How competitive is bidding in infrastructure public procurement?
- IJARIIT Vol 3 Issue 4 — Challenges before Micro, Small and Medium Enterprises
- SIDBI (May 2025) — Understanding Indian MSME Sector: Progress and Challenges
- Ministry of MSME — Annual Report 2025–26
- DCMSME — FAQs on Public Procurement Policy for MSEs, Order 2012
- PIB / DD News — GeM ₹18.4 lakh crore cumulative GMV
- CPPP (eprocure.gov.in) — DSC information page; Model Tender Document for Goods
- IJARIIT / Jaggaer / European Court of Auditors — single-bidding causes
