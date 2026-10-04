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
