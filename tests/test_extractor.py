import os
import pytest
from src.text_extract import TextWorker
from src.regex_fallback import DeterministicRegexExtractor
from src.agent.extractor import ExtractorAgent


def test_deterministic_regex_on_imd_tender():
    pdf_path = os.path.join("sample_tenders", "imd-tender.pdf")
    assert os.path.exists(pdf_path)

    worker = TextWorker()
    extraction = worker.process(pdf_path)

    matrix = DeterministicRegexExtractor.build_matrix(extraction)

    assert matrix.tender_id is not None
    # Verify EMD was identified
    assert matrix.emd_amount is not None
    assert matrix.emd_amount == 10000 or matrix.emd_amount > 0
    # Check exemption recognition
    assert "micro" in [c.lower() for c in matrix.emd_exempt_categories]
    assert "small" in [c.lower() for c in matrix.emd_exempt_categories]


def test_extractor_agent_graceful_tier3_fallback():
    pdf_path = os.path.join("sample_tenders", "imd-tender.pdf")
    worker = TextWorker()
    extraction = worker.process(pdf_path)

    # Test with no API key (Tier 3 fallback)
    agent = ExtractorAgent(api_key=None)
    matrix = agent.extract(extraction)

    assert matrix is not None
    assert matrix.emd_amount is not None
    # Ensure evidence verification ran
    if "emd_amount" in matrix.evidence_fields:
        ev = matrix.evidence_fields["emd_amount"]
        assert ev.source_page > 0
        assert len(ev.source_snippet) > 0


def test_inr_parser_variants():
    parse = DeterministicRegexExtractor.parse_inr
    assert parse("₹50,000") == 50000
    assert parse("Rs. 10 Lakhs") == 1000000
    assert parse("1.5 Crore") == 15000000
    assert parse("₹ 2.5 Cr") == 25000000
    assert parse("500000") == 500000
    assert parse("") is None


def test_page_aware_chunking_retrieval_40_pages():
    """Verify that a 40-page tender has critical clauses retrieved with page preservation."""
    from src.text_extract import PageText, ExtractionResult
    pages = {}
    for p in range(1, 41):
        if p == 1:
            text = "NIT No: PWD/2026/01. Notice Inviting Tender for Road Construction."
        elif p == 15:
            text = "Clause 15.1: Earnest Money Deposit (EMD) of Rs. 5,00,000 payable by bidder."
        elif p == 28:
            text = "Clause 28: Minimum average annual turnover of Rs 2 Crore in last 3 financial years."
        elif p == 35:
            text = "Clause 35: Micro and Small enterprises are exempted from EMD under GFR 170."
        else:
            text = f"General conditions of contract page {p}. " * 60  # Boilerplate filler
        pages[p] = PageText(
            page_number=p,
            raw_text=text,
            normalized_text=text,
            char_count=len(text),
            is_scanned_likely=False,
        )

    er = ExtractionResult(
        tender_id="TND-40P",
        total_pages=40,
        pages=pages,
        full_text="\n".join(p.normalized_text for p in pages.values()),
        is_scanned_document=False,
    )

    retrieved = ExtractorAgent._retrieve_relevant_sections(er, max_chars=12000)
    assert "--- PAGE 1 ---" in retrieved
    assert "--- PAGE 15 ---" in retrieved
    assert "--- PAGE 28 ---" in retrieved
    assert "--- PAGE 35 ---" in retrieved
    assert "Earnest Money Deposit (EMD)" in retrieved
    assert "turnover of Rs 2 Crore" in retrieved


def test_agent_repair_loop_on_citation_failure():
    """Test that agent loop calls REPAIR_PROMPT_TEMPLATE when citation verification fails."""
    from src.text_extract import PageText, ExtractionResult

    p1_text = "Tender 101. EMD is Rs. 50,000 payable to director."
    pages = {
        1: PageText(page_number=1, raw_text=p1_text, normalized_text=p1_text, char_count=len(p1_text), is_scanned_likely=False)
    }
    er = ExtractionResult(
        tender_id="TND-REP",
        total_pages=1,
        pages=pages,
        full_text=p1_text,
        is_scanned_document=False,
    )

    agent = ExtractorAgent(api_key="test-mock-key")
    call_count = 0

    def mock_call_llm(prompt_text):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First attempt: hallucinated snippet
            return {
                "tender_id": "TND-REP",
                "title": "Test Tender",
                "emd_amount": 50000,
                "evidence_fields": {
                    "emd_amount": {
                        "field_name": "emd_amount",
                        "value_raw": "50000",
                        "value_normalised": 50000,
                        "confidence": 0.95,
                        "source_page": 1,
                        "source_snippet": "This snippet does not exist on page 1 anywhere!",
                    }
                }
            }
        else:
            # Second attempt (repair): correct verbatim snippet
            return {
                "tender_id": "TND-REP",
                "title": "Test Tender",
                "emd_amount": 50000,
                "evidence_fields": {
                    "emd_amount": {
                        "field_name": "emd_amount",
                        "value_raw": "Rs. 50,000",
                        "value_normalised": 50000,
                        "confidence": 0.95,
                        "source_page": 1,
                        "source_snippet": "EMD is Rs. 50,000 payable to director.",
                    }
                }
            }

    agent._call_llm = mock_call_llm
    matrix = agent.extract(er)

    assert call_count == 2
    assert agent.last_tier == 1
    assert any(step["step"] == "repair_prompt_call" for step in agent.audit_trace)
    assert any(step["step"] == "citation_verification" and step["status"] == "PASS" for step in agent.audit_trace)
    assert matrix.emd_amount == 50000


def test_connection_error_redacts_api_key(monkeypatch):
    """A1: Ensure ConnectionError containing fake key never appears in result or trace."""
    import json
    import requests
    from requests.exceptions import ConnectionError
    from src.text_extract import PageText, ExtractionResult

    fake_key = "AIza_FAKE_TEST_KEY_123"
    fake_token = "Bearer " + "gsk_TEST_TOKEN_123"
    
    p1_text = "NIT No: PWD/2026/01. Notice Inviting Tender. EMD: Rs. 50,000."
    er = ExtractionResult(
        tender_id="TND-ERR-KEY",
        total_pages=1,
        pages={1: PageText(page_number=1, raw_text=p1_text, normalized_text=p1_text, char_count=len(p1_text), is_scanned_likely=False)},
        full_text=p1_text,
        is_scanned_document=False,
    )

    agent = ExtractorAgent(api_key=fake_key)

    def mock_post(*args, **kwargs):
        raise ConnectionError(f"Connection failed at url=https://api.test?key={fake_key} with auth {fake_token}")

    monkeypatch.setattr(requests, "post", mock_post)

    matrix = agent.extract(er)
    assert matrix is not None
    assert agent.last_tier == 3
    assert agent.fallback_reason == "LLM provider unavailable; used deterministic fallback"

    # Verify key never appears in audit trace
    trace_dump = json.dumps(agent.audit_trace)
    assert fake_key not in trace_dump
    assert "gsk_TEST_TOKEN_123" not in trace_dump
    assert "[REDACTED]" in trace_dump or "[REDACTED_KEY]" in trace_dump

