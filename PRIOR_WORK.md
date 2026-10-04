# Prior Work Disclosure

> Per WCC Launchpad 30 Rule 04: *"If your project builds on prior code, libraries, or frameworks not created during the event, disclose them."*

## Prior Projects

Team members previously built two unrelated personal projects:

1. **A tender alert bot** — a notification system for new tenders on government portals (September 2026, public repo). It scraped portal listings and sent alerts. **No code from this project is used in BidSahayak.** BidSahayak does not scrape, does not alert, and solves a different problem (eligibility reasoning, not discovery).

2. **An emergency-response prototype** — an incident coordination dashboard (September 2026, public repo). It used mapping, real-time data, and multi-agent coordination. **No code from this project is used in BidSahayak.** Different domain, different architecture, different users.

Both repositories are left **public and unmodified** so anyone can verify that no code was carried over.

## What We Carried Over (Domain Knowledge — Rule 02 Permitted)

Rule 02 explicitly permits research and discussion before the event. The domain knowledge we carried over:

- **Which government procurement portals exist** (CPPP, GeM) and how tender data is structured
- **Indian tender document anatomy** — where eligibility typically lives (ITB, TIS, SCC, Annexures)
- **Unicode NFKC normalisation** is required for Devanagari text comparison
- **Lakh/crore number formatting** conventions
- **GFR 2017 Rules 149, 170, 173** and the PPP for MSEs Order 2012 — the legal rules governing MSME procurement preferences
- **Deployment experience** with Vercel and Render

## What We Did NOT Do Before 10:00 on 4 Oct 2026

- No repository was created
- No code was written
- No commits were made
- No implementation decisions were finalised

**Every line of code in this repository was written inside the event window (4 Oct 10:00 IST – 5 Oct 16:00 IST).**

## AI Tools Used

See README.md § "AI Tools Used" for full disclosure.
