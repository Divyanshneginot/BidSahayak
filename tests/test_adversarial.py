"""
Adversarial Battery (Phase 4 Verification)
Evaluates trap tenders:
1. Corrupted / unparseable deadline
2. Paise overflow / currency parsing attack
3. Missing EMD with claimed exemption
All cases must resolve strictly to 'needs-human-review' or 'not-eligible' — NEVER 'eligible'.
"""
import pytest
from datetime import datetime, timezone
from src.models import RequirementMatrix, VendorProfile, FieldEvidence
from src.evaluator import evaluate
from src.regex_fallback import DeterministicRegexExtractor


def test_adversarial_corrupted_date():
    """Trap 1: Unparseable / corrupted date string cannot produce an eligible verdict."""
    m = RequirementMatrix(
        tender_id="ADV-01",
        title="Corrupted Date Tender",
        submission_deadline=None,
        unresolved_fields=["submission_deadline"],
        evidence_fields={
            "submission_deadline": FieldEvidence(
                field_name="submission_deadline",
                value_raw="Closing date: 99.99.9999 / invalid",
                value_normalised=None,
                confidence=0.20,
                source_page=1,
                source_snippet="Closing date: 99.99.9999 / invalid",
            )
        }
    )
    p = VendorProfile(business_name="Test Enterprise", udyam_classification="Micro")
    v = evaluate(m, p)
    assert v.overall in ["needs-human-review", "not-eligible"]
    assert v.overall != "eligible"


def test_adversarial_paise_overflow():
    """Trap 2: Decimal paise amounts must not multiply into inflated crores."""
    parsed = DeterministicRegexExtractor.parse_inr("10,000.00")
    assert parsed == 10000
    assert parsed != 1000000

    parsed_crore = DeterministicRegexExtractor.parse_inr("₹ 4.50 Crore")
    assert parsed_crore == 45000000


def test_adversarial_missing_emd_with_exemption_claim():
    """Trap 3: Tender requiring EMD where vendor is a trader falsely claiming MSE exemption."""
    m = RequirementMatrix(
        tender_id="ADV-03",
        title="EMD Required Tender",
        emd_amount=50000,
        emd_exempt_categories=["micro", "small"],
        evidence_fields={
            "emd_amount": FieldEvidence(
                field_name="emd_amount",
                value_raw="₹50,000",
                value_normalised=50000,
                confidence=0.90,
                source_page=1,
                source_snippet="EMD of Rs 50,000 payable",
            )
        }
    )
    # Vendor registered as Trader (not manufacturer) -> exemption denied under GFR 170
    p = VendorProfile(
        business_name="Trader Only Enterprise",
        udyam_classification="Micro",
        is_manufacturing=False,
        is_trading=True
    )
    v = evaluate(m, p)
    assert v.overall in ["needs-human-review", "not-eligible", "eligible-with-gaps"]
    assert v.overall != "eligible"
    assert any(g.status == "gap" and "Trader" in g.reason for g in v.gaps)
