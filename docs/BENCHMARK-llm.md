# LLM-tier benchmark — not run

This file previously reported "Tier 1/2 (Agentic LLM Extraction)" with accuracy identical to the
deterministic tier (13/14, 12/14, 1/14, 9/14) at ~40x the latency. That is the signature of a **failed
LLM call falling back to the deterministic engine**: the request errored, `except Exception` swallowed it,
and the regex matrix was returned — with the run published as if the LLM had answered.

The extractor now records `last_tier` and `fallback_reason` per document, and `scripts/benchmark.py`
prints both. To produce a real LLM-tier benchmark:

```bash
export GEMINI_API_KEY=...        # never commit this
python scripts/benchmark.py --repo . --md docs/BENCHMARK-llm.md
```

Rule: if any document reports `tier=3`, the run is a fallback run and the output must say so in its title.
Delete this file rather than publish an unverified LLM claim.
