import pytest
from datetime import datetime, timezone, timedelta, date
from src.models import RequirementMatrix, VendorProfile, FieldEvidence
from src.evaluator import evaluate


@pytest.fixture
def base_matrix():
    return RequirementMatrix(
        tender_id="IMD-20190607-001",
        title="Supply & Installation of High Performance Computing Hardware",
        issuing_department="India Meteorological Department",
        portal="CPPP",
        emd_amount=50000,
        emd_exempt_categories=["micro", "small"],
        min_turnover=2000000,  # 20 Lakhs
        turnover_window_years=3,
        min_years_experience=3,
        required_certifications=["ISO 9001"],
        submission_deadline=datetime.now(timezone.utc) + timedelta(days=14),
        technical_bid_date=datetime.now(timezone.utc) + timedelta(days=15),
        requires_class3_dsc=True,
        startup_clause_active=False,
    )


@pytest.fixture
def eligible_micro_profile():
    return VendorProfile(
        business_name="Sahayak Tech Solutions",
        udyam_classification="Micro",
        udyam_valid_until=date(2028, 12, 31),
        udyam_covers_tender_item=True,
        is_manufacturing=True,
        is_trading=False,
        annual_turnover_last_3y=[1500000, 2500000, 2200000],  # Max 25L > 20L
        years_in_business=5,
        certifications_held=["ISO 9001", "MSME"],
        holds_class3_dsc=True,
        startup_india=False,
    )


def test_micro_enterprise_emd_exempt(base_matrix, eligible_micro_profile):
    """Test Case 1: Micro enterprise gets EMD exemption under GFR 170."""
    verdict = evaluate(base_matrix, eligible_micro_profile)
    emd_v = next(v for v in verdict.verdicts if "EMD" in v.requirement)
    assert emd_v.status == "waived"
    assert "GFR 2017 Rule 170" in emd_v.reason
    assert verdict.overall == "eligible"


def test_small_enterprise_emd_exempt(base_matrix, eligible_micro_profile):
    """Test Case 2: Small enterprise also gets EMD exemption."""
    eligible_micro_profile.udyam_classification = "Small"
    verdict = evaluate(base_matrix, eligible_micro_profile)
    emd_v = next(v for v in verdict.verdicts if "EMD" in v.requirement)
    assert emd_v.status == "waived"


def test_medium_enterprise_emd_not_exempt(base_matrix, eligible_micro_profile):
    """Test Case 3: Medium enterprise is explicitly NOT exempt under GFR 170."""
    eligible_micro_profile.udyam_classification = "Medium"
    verdict = evaluate(base_matrix, eligible_micro_profile)
    emd_v = next(v for v in verdict.verdicts if "EMD" in v.requirement)
    assert emd_v.status == "gap"
    assert "Medium enterprises are explicitly NOT exempt" in emd_v.reason
    assert verdict.overall in ["eligible-with-gaps", "not-eligible"]


def test_trading_vendor_emd_not_exempt(base_matrix, eligible_micro_profile):
    """Test Case 4: Trader is NOT exempt under GFR Rule 170 (manufacturing only)."""
    eligible_micro_profile.is_trading = True
    eligible_micro_profile.is_manufacturing = False
    verdict = evaluate(base_matrix, eligible_micro_profile)
    emd_v = next(v for v in verdict.verdicts if "EMD" in v.requirement)
    assert emd_v.status == "gap"
    assert "Trader" in emd_v.reason


def test_udyam_expired_on_bid_opening(base_matrix, eligible_micro_profile):
    """Test Case 5: Udyam certificate expired before opening date -> gap."""
    eligible_micro_profile.udyam_valid_until = date(2020, 1, 1)
    verdict = evaluate(base_matrix, eligible_micro_profile)
    emd_v = next(v for v in verdict.verdicts if "EMD" in v.requirement)
    assert emd_v.status == "gap"
    assert "expires" in emd_v.reason


def test_udyam_not_covering_item(base_matrix, eligible_micro_profile):
    """Test Case 6: Certificate does not cover the tendered item."""
    eligible_micro_profile.udyam_covers_tender_item = False
    verdict = evaluate(base_matrix, eligible_micro_profile)
    emd_v = next(v for v in verdict.verdicts if "EMD" in v.requirement)
    assert emd_v.status == "gap"
    assert "NIC code" in emd_v.reason


def test_turnover_met_in_any_of_three_years(base_matrix, eligible_micro_profile):
    """Test Case 7: Average turnover across 3 years meets threshold (GFR 173 rule)."""
    eligible_micro_profile.annual_turnover_last_3y = [1800000, 2400000, 2100000]
    verdict = evaluate(base_matrix, eligible_micro_profile)
    t_v = next(v for v in verdict.verdicts if "Turnover" in v.requirement)
    assert t_v.status == "met"


def test_turnover_shortfall(base_matrix, eligible_micro_profile):
    """Test Case 8: Turnover below required amount across all years."""
    eligible_micro_profile.annual_turnover_last_3y = [1000000, 1200000, 1500000]  # Max 15L < 20L
    verdict = evaluate(base_matrix, eligible_micro_profile)
    t_v = next(v for v in verdict.verdicts if "Turnover" in v.requirement)
    assert t_v.status == "gap"
    assert "Shortfall" in t_v.reason
    assert verdict.overall == "not-eligible"


def test_startup_india_relaxation(base_matrix, eligible_micro_profile):
    """Test Case 9: GFR Rule 173 startup relaxation for turnover and EMD."""
    base_matrix.startup_clause_active = True
    eligible_micro_profile.startup_india = True
    eligible_micro_profile.annual_turnover_last_3y = [100000]  # Very low turnover
    eligible_micro_profile.years_in_business = 1  # Low experience
    verdict = evaluate(base_matrix, eligible_micro_profile)
    
    t_v = next(v for v in verdict.verdicts if "Turnover" in v.requirement)
    assert t_v.status == "waived"
    assert "Rule 173" in t_v.reason


def test_missing_certifications(base_matrix, eligible_micro_profile):
    """Test Case 10: Missing mandatory ISO 9001 certificate."""
    eligible_micro_profile.certifications_held = ["CMMI"]
    verdict = evaluate(base_matrix, eligible_micro_profile)
    cert_v = next(v for v in verdict.verdicts if "Certifications" in v.requirement)
    assert cert_v.status == "gap"
    assert "ISO 9001" in cert_v.reason


def test_dsc_timing_barrier_impossible(base_matrix, eligible_micro_profile):
    """Test Case 11: Deadline < 7 days + No DSC -> Participation Impossible."""
    base_matrix.submission_deadline = datetime.now(timezone.utc) + timedelta(days=3)
    eligible_micro_profile.holds_class3_dsc = False
    verdict = evaluate(base_matrix, eligible_micro_profile)
    
    assert verdict.participation_impossible is True
    assert "CPPP guidance" in verdict.impossible_reason
    assert verdict.overall == "not-eligible"


def test_confidence_gating_triggers_human_review(base_matrix, eligible_micro_profile):
    """Test Case 12: Low confidence field (< 0.7) forces needs-human-review."""
    base_matrix.evidence_fields["min_turnover"] = FieldEvidence(
        field_name="min_turnover",
        value_raw="turnover around two crore",
        value_normalised=2000000,
        confidence=0.55,  # Below 0.7!
        source_page=4,
        source_snippet="turnover around two crore",
    )
    verdict = evaluate(base_matrix, eligible_micro_profile)
    assert verdict.overall == "needs-human-review"
    assert "min_turnover" in verdict.low_confidence_fields
    assert len(verdict.audit_log) > 0


def test_evaluate_dsc_timing_custom_now():
    """Verify evaluate_dsc_timing strictly uses custom passed now."""
    from zoneinfo import ZoneInfo
    from src.evaluator import evaluate_dsc_timing
    ist = ZoneInfo("Asia/Kolkata")
    now_ref = datetime(2026, 11, 1, 10, 0, tzinfo=ist)
    
    # Exactly 7 days -> gap_addressable
    deadline_7d = now_ref + timedelta(days=7)
    assert evaluate_dsc_timing(deadline_7d, holds_dsc=False, now=now_ref) == "gap_addressable"

    # 6.9 days -> gap_impossible
    deadline_6d = now_ref + timedelta(days=6, hours=23)
    assert evaluate_dsc_timing(deadline_6d, holds_dsc=False, now=now_ref) == "gap_impossible"

    # Already holds DSC -> met
    assert evaluate_dsc_timing(deadline_6d, holds_dsc=True, now=now_ref) == "met"


def test_tender_closed_verdict_past_deadline(base_matrix, eligible_micro_profile):
    """Verify past deadline produces tender closed verdict and not-eligible."""
    from zoneinfo import ZoneInfo
    ist = ZoneInfo("Asia/Kolkata")
    now_ref = datetime(2026, 11, 1, 12, 0, tzinfo=ist)
    base_matrix.submission_deadline = now_ref - timedelta(days=1)
    
    verdict = evaluate(base_matrix, eligible_micro_profile, current_time=now_ref)
    assert verdict.participation_impossible is True
    assert "deadline has passed" in verdict.impossible_reason
    assert verdict.overall == "not-eligible"
    dl_v = next(v for v in verdict.verdicts if v.requirement == "Submission Deadline")
    assert dl_v.status == "gap"
    assert "closed" in dl_v.remedy.lower()


def test_dsc_accurate_wording(base_matrix, eligible_micro_profile):
    """Verify accurate wording for DSC issuance replacing 'mathematically impossible'."""
    from zoneinfo import ZoneInfo
    ist = ZoneInfo("Asia/Kolkata")
    now_ref = datetime(2026, 11, 1, 12, 0, tzinfo=ist)
    base_matrix.submission_deadline = now_ref + timedelta(days=4)
    eligible_micro_profile.holds_class3_dsc = False

    verdict = evaluate(base_matrix, eligible_micro_profile, current_time=now_ref)
    assert "mathematically impossible" not in verdict.impossible_reason
    assert "Vendor lacks Class 3 DSC, so issuance cannot be completed" in verdict.impossible_reason


def test_similar_work_experience_checks(base_matrix, eligible_micro_profile):
    """Verify similar work experience check based on percentage of estimated cost."""
    base_matrix.estimated_cost = 10000000  # 1 Crore
    base_matrix.similar_work_percent = 50.0  # 50% = 50 Lakhs

    # Vendor past work = 60 Lakhs -> met
    eligible_micro_profile.past_work_max_value = 6000000
    v1 = evaluate(base_matrix, eligible_micro_profile)
    sw1 = next(v for v in v1.verdicts if v.requirement == "Similar Work Experience")
    assert sw1.status == "met"

    # Vendor past work = 30 Lakhs -> gap
    eligible_micro_profile.past_work_max_value = 3000000
    v2 = evaluate(base_matrix, eligible_micro_profile)
    sw2 = next(v for v in v2.verdicts if v.requirement == "Similar Work Experience")
    assert sw2.status == "gap"
    assert v2.overall == "not-eligible"


def test_minimum_net_worth_checks(base_matrix, eligible_micro_profile):
    """Verify minimum net worth evaluation."""
    base_matrix.min_net_worth = 2500000  # 25 Lakhs

    # Met
    eligible_micro_profile.net_worth = 3000000
    v1 = evaluate(base_matrix, eligible_micro_profile)
    nw1 = next(v for v in v1.verdicts if v.requirement == "Minimum Net Worth")
    assert nw1.status == "met"

    # Gap
    eligible_micro_profile.net_worth = 1500000
    v2 = evaluate(base_matrix, eligible_micro_profile)
    nw2 = next(v for v in v2.verdicts if v.requirement == "Minimum Net Worth")
    assert nw2.status == "gap"
    assert v2.overall == "not-eligible"

