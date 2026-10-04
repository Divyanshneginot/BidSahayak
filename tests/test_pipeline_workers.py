import os
import pytest
from src.ingest import IngestWorker
from src.text_extract import TextWorker
from src.verify import SnippetVerifier


def test_ingest_worker_real_pdf():
    pdf_path = os.path.join("sample_tenders", "imd-tender.pdf")
    assert os.path.exists(pdf_path), "Sample IMD tender PDF must exist"
    
    worker = IngestWorker(max_size_mb=25, max_pages=100)
    result = worker.process(pdf_path)
    
    assert result.is_valid is True
    assert result.page_count > 0
    assert len(result.sha256_hash) == 64
    assert result.file_size_bytes > 0


def test_ingest_worker_missing_file():
    worker = IngestWorker()
    result = worker.process("non_existent_file.pdf")
    assert result.is_valid is False
    assert "File not found" in result.rejection_reason


def test_text_worker_nfkc_and_sections():
    pdf_path = os.path.join("sample_tenders", "imd-tender.pdf")
    worker = TextWorker()
    result = worker.process(pdf_path)
    
    assert result.total_pages > 0
    assert 1 in result.pages
    assert len(result.full_text) > 100
    # Check section detection
    assert len(result.detected_sections) > 0


def test_snippet_verifier_exact_and_fuzzy():
    page_text = (
        "GOVERNMENT OF INDIA, INDIA METEOROLOGICAL DEPARTMENT. "
        "The bidder must submit an Earnest Money Deposit of Rs 50,000 "
        "in the form of Bank Guarantee or FDR valid for 240 days."
    )
    
    # Exact match
    res1 = SnippetVerifier.verify(
        snippet="Earnest Money Deposit of Rs 50,000",
        page_text=page_text
    )
    assert res1.is_verified is True
    assert res1.match_ratio == 1.0

    # Slight punctuation/spacing difference (fuzzy match)
    res2 = SnippetVerifier.verify(
        snippet="Earnest Money Deposit of Rs. 50000",
        page_text=page_text
    )
    assert res2.is_verified is True
    assert res2.match_ratio >= 0.85

    # Completely false / hallucinated snippet
    res3 = SnippetVerifier.verify(
        snippet="Turnover must be minimum 50 crore Rupees strictly",
        page_text=page_text
    )
    assert res3.is_verified is False
    assert "could not be verified" in res3.reason
