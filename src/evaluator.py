from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from typing import Optional
from src.models import (
    RequirementMatrix,
    VendorProfile,
    RequirementVerdict,
    BidVerdict,
)

IST = ZoneInfo("Asia/Kolkata")


def calculate_effective_turnover(turnovers: list[int]) -> int:
    """Calculates average annual turnover across reported financial years (not max)."""
    if not turnovers:
        return 0
    return int(sum(turnovers) / len(turnovers))


def evaluate_dsc_timing(deadline: datetime, holds_dsc: bool) -> str:
    """
    Evaluates whether vendor can obtain Class 3 DSC before deadline.
    Under CPPP guidance, obtaining a new Class 3 DSC takes 3-7 days.
    If vendor lacks DSC and days < 7 -> 'gap_impossible'.
    If vendor lacks DSC and days >= 7 -> 'gap_addressable'.
    If vendor holds DSC -> 'met'.
    """
    if holds_dsc:
        return "met"
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=IST)
    now = datetime.now(deadline.tzinfo)
    days = (deadline - now).total_seconds() / 86400.0
    return "gap_impossible" if days < 7.0 else "gap_addressable"


def evaluate(
    matrix: RequirementMatrix,
    profile: VendorProfile,
    current_time: Optional[datetime] = None,
) -> BidVerdict:
    """
    Pure deterministic comparison engine.
    Compares RequirementMatrix against VendorProfile according to:
    - GFR 2017 Rules 149, 170, 173
    - Public Procurement Policy for MSEs Order 2012
    - Class 3 DSC timing constraint
    - Confidence gating
    """
    now = current_time or datetime.now(IST)
    verdicts: list[RequirementVerdict] = []
    gaps: list[RequirementVerdict] = []
    low_confidence_fields: list[str] = []
    audit_log: list[dict] = []

    # 1. Identify low-confidence fields (< 0.7)
    for field_name, evidence in matrix.evidence_fields.items():
        if evidence.confidence < 0.7:
            low_confidence_fields.append(field_name)
            audit_log.append({
                "action": "flag_low_confidence",
                "field": field_name,
                "confidence": evidence.confidence,
                "snippet": evidence.source_snippet,
            })

    # 2. EMD / Bid Security Evaluation
    if matrix.emd_amount and matrix.emd_amount > 0:
        emd_req = "Earnest Money Deposit (EMD)"
        emd_evidence = matrix.evidence_fields.get("emd_amount")
        evidence_str = emd_evidence.source_snippet if emd_evidence else f"₹{matrix.emd_amount:,}"

        # Check exemptions:
        # Micro or Small enterprises under GFR 170
        is_mse = profile.udyam_classification in ["Micro", "Small"]
        is_medium = profile.udyam_classification == "Medium"
        
        if is_medium:
            # Sourced rule: Medium enterprises get NO exemption under GFR 170
            verdict = RequirementVerdict(
                requirement=emd_req,
                status="gap",
                reason=(
                    f"EMD of ₹{matrix.emd_amount:,} is payable. Medium enterprises are explicitly "
                    "NOT exempt under GFR 2017 Rule 170 (exemption covers Micro and Small only)."
                ),
                evidence=evidence_str,
                remedy=f"Prepare Bank Guarantee / FDR / DD of ₹{matrix.emd_amount:,} as specified in tender.",
            )
            verdicts.append(verdict)
            gaps.append(verdict)

        elif is_mse and "micro" in [c.lower() for c in matrix.emd_exempt_categories]:
            # Validate MSE exemption conditions:
            # Condition A: Trading vs Manufacturing
            if profile.is_trading and not profile.is_manufacturing:
                verdict = RequirementVerdict(
                    requirement=emd_req,
                    status="gap",
                    reason=(
                        "MSE exemption denied: Vendor registered as Trader. GFR Rule 170 and "
                        "Ministry guidelines apply only to manufacturers/service providers, not traders."
                    ),
                    evidence=evidence_str,
                    remedy="Procure directly as manufacturer or deposit full EMD amount.",
                )
                verdicts.append(verdict)
                gaps.append(verdict)
            
            # Condition B: Udyam certificate validity on opening date
            elif profile.udyam_valid_until and matrix.technical_bid_date and profile.udyam_valid_until < matrix.technical_bid_date.date():
                verdict = RequirementVerdict(
                    requirement=emd_req,
                    status="gap",
                    reason=(
                        f"MSE Udyam certificate expires on {profile.udyam_valid_until}, "
                        f"which is before bid opening date {matrix.technical_bid_date.date()}."
                    ),
                    evidence=evidence_str,
                    remedy="Renew Udyam registration before technical bid opening date.",
                )
                verdicts.append(verdict)
                gaps.append(verdict)

            # Condition C: Item coverage
            elif not profile.udyam_covers_tender_item:
                verdict = RequirementVerdict(
                    requirement=emd_req,
                    status="gap",
                    reason="MSE Udyam registration does not cover the tendered category/NIC code.",
                    evidence=evidence_str,
                    remedy="Update Udyam registration to include relevant NIC product code.",
                )
                verdicts.append(verdict)
                gaps.append(verdict)

            else:
                verdict = RequirementVerdict(
                    requirement=emd_req,
                    status="waived",
                    reason=(
                        f"Exempted from EMD of ₹{matrix.emd_amount:,} under GFR 2017 Rule 170 "
                        f"as registered {profile.udyam_classification} enterprise. Submit Bid Security Declaration (BSD)."
                    ),
                    evidence=evidence_str,
                    remedy="Attach valid Udyam Registration Certificate and signed BSD Annexure.",
                )
                verdicts.append(verdict)

        elif matrix.startup_clause_active and profile.startup_india:
            verdict = RequirementVerdict(
                requirement=emd_req,
                status="waived",
                reason="Exempted from EMD under GFR 2017 Rule 173 (DPIIT recognized startup).",
                evidence=evidence_str,
                remedy="Attach DPIIT Startup Recognition Certificate.",
            )
            verdicts.append(verdict)

        else:
            verdict = RequirementVerdict(
                requirement=emd_req,
                status="gap",
                reason=f"Full EMD of ₹{matrix.emd_amount:,} must be deposited. Vendor not MSE/Startup exempt.",
                evidence=evidence_str,
                remedy=f"Arrange FDR/BG for ₹{matrix.emd_amount:,} before bid submission.",
            )
            verdicts.append(verdict)
            gaps.append(verdict)
    else:
        verdicts.append(RequirementVerdict(
            requirement="Earnest Money Deposit (EMD)",
            status="not-applicable",
            reason="No EMD required for this tender (or zero fee).",
        ))

    # 3. Annual Turnover Evaluation
    if matrix.min_turnover and matrix.min_turnover > 0:
        turnover_evidence = matrix.evidence_fields.get("min_turnover")
        evidence_str = turnover_evidence.source_snippet if turnover_evidence else f"₹{matrix.min_turnover:,}"
        
        effective_vendor_turnover = calculate_effective_turnover(profile.annual_turnover_last_3y)
        if effective_vendor_turnover >= matrix.min_turnover:
            verdicts.append(RequirementVerdict(
                requirement="Annual Turnover",
                status="met",
                reason=f"Average annual turnover in last 3 years (₹{effective_vendor_turnover:,}) meets required ₹{matrix.min_turnover:,}.",
                evidence=evidence_str,
            ))
        elif matrix.startup_clause_active and profile.startup_india:
            verdicts.append(RequirementVerdict(
                requirement="Annual Turnover",
                status="waived",
                reason="Turnover requirement relaxed under GFR 2017 Rule 173 for DPIIT recognized startup.",
                evidence=evidence_str,
            ))
        else:
            verdict = RequirementVerdict(
                requirement="Annual Turnover",
                status="gap",
                reason=(
                    f"Required minimum turnover is ₹{matrix.min_turnover:,}, but vendor 3-year average "
                    f"is ₹{effective_vendor_turnover:,} (Shortfall: ₹{matrix.min_turnover - effective_vendor_turnover:,})."
                ),
                evidence=evidence_str,
                remedy="Explore joint-venture (JV) consortium or sub-contractor partnership if permitted in tender.",
            )
            verdicts.append(verdict)
            gaps.append(verdict)

    # 4. Experience / Past Work Evaluation
    if matrix.min_years_experience and matrix.min_years_experience > 0:
        if profile.years_in_business >= matrix.min_years_experience:
            verdicts.append(RequirementVerdict(
                requirement="Experience (Years in Business)",
                status="met",
                reason=f"Vendor has {profile.years_in_business} years in business (minimum required: {matrix.min_years_experience}).",
            ))
        elif matrix.startup_clause_active and profile.startup_india:
            verdicts.append(RequirementVerdict(
                requirement="Experience (Years in Business)",
                status="waived",
                reason="Prior experience criteria relaxed for DPIIT recognized startup.",
            ))
        else:
            verdict = RequirementVerdict(
                requirement="Experience (Years in Business)",
                status="gap",
                reason=f"Vendor has {profile.years_in_business} years in business (minimum required: {matrix.min_years_experience}).",
                remedy="Partner with an established contractor or verify if relaxation applies.",
            )
            verdicts.append(verdict)
            gaps.append(verdict)

    # 5. Required Certifications
    if matrix.required_certifications:
        missing_certs = [
            c for c in matrix.required_certifications
            if c.lower() not in [vc.lower() for vc in profile.certifications_held]
        ]
        if not missing_certs:
            verdicts.append(RequirementVerdict(
                requirement="Mandatory Certifications",
                status="met",
                reason=f"All required certifications held ({', '.join(matrix.required_certifications)}).",
            ))
        else:
            verdict = RequirementVerdict(
                requirement="Mandatory Certifications",
                status="gap",
                reason=f"Missing mandatory certifications: {', '.join(missing_certs)}.",
                remedy=f"Obtain certification ({', '.join(missing_certs)}) or check if undertaking accepted.",
            )
            verdicts.append(verdict)
            gaps.append(verdict)

    # 6. Submission Deadline & Class 3 DSC Timing Barrier (Original CAG/CPPP insight)
    days_to_deadline: Optional[int] = None
    participation_impossible = False
    impossible_reason = None

    if matrix.submission_deadline:
        deadline = matrix.submission_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=IST)
        
        cmp_now = now if now.tzinfo is not None else now.replace(tzinfo=IST)
        diff = deadline - cmp_now
        days_to_deadline = max(0, int(diff.total_seconds() / 86400.0))

        if matrix.requires_class3_dsc:
            dsc_status = evaluate_dsc_timing(deadline, profile.holds_class3_dsc)
            if dsc_status == "gap_impossible":
                participation_impossible = True
                impossible_reason = (
                    f"A new Class 3 DSC takes 3–7 days to issue (official CPPP guidance). "
                    f"This tender closes in {days_to_deadline} days. Unless vendor already possesses "
                    "a valid DSC token, bid submission is mathematically impossible."
                )
                verdict = RequirementVerdict(
                    requirement="Class 3 Digital Signature Certificate (DSC)",
                    status="gap",
                    reason=impossible_reason,
                    remedy="Immediate emergency issuance of Class 3 DSC token via e-Mudhra or (n)Code.",
                )
                verdicts.append(verdict)
                gaps.append(verdict)
            elif dsc_status == "gap_addressable":
                verdict = RequirementVerdict(
                    requirement="Class 3 Digital Signature Certificate (DSC)",
                    status="gap",
                    reason=f"Vendor lacks Class 3 DSC. Tender closes in {days_to_deadline} days.",
                    remedy="Apply for Class 3 DSC immediately (takes 3-5 business days).",
                )
                verdicts.append(verdict)
                gaps.append(verdict)
            else:
                verdicts.append(RequirementVerdict(
                    requirement="Class 3 Digital Signature Certificate (DSC)",
                    status="met",
                    reason="Vendor holds valid Class 3 DSC required for e-procurement portal.",
                ))

    # 7. Overall Verdict Determination
    is_empty_matrix = (
        len(matrix.evidence_fields) == 0
        and matrix.emd_amount is None
        and matrix.min_turnover is None
        and matrix.submission_deadline is None
        and matrix.min_years_experience is None
        and not matrix.required_certifications
    )
    unresolved_fields = getattr(matrix, "unresolved_fields", [])

    blocking_gaps = []
    addressable_gaps = []
    for g in gaps:
        if "Class 3" in g.requirement and participation_impossible:
            blocking_gaps.append(g)
        elif g.requirement in ["Annual Turnover", "Experience (Years in Business)"]:
            blocking_gaps.append(g)
        elif g.requirement == "Mandatory Certifications":
            blocking_gaps.append(g)
        else:
            addressable_gaps.append(g)

    if is_empty_matrix:
        overall = "needs-human-review"
        summary = "Tender matrix contains no extracted requirements. Operator review required before assessment."
    elif unresolved_fields:
        overall = "needs-human-review"
        summary = f"Extraction contains unresolved fields ({', '.join(unresolved_fields)}). Operator review required."
    elif low_confidence_fields and not matrix.evidence_fields.get("_human_approved", False):
        overall = "needs-human-review"
        summary = (
            f"Extraction contains {len(low_confidence_fields)} low-confidence field(s) "
            f"({', '.join(low_confidence_fields)}). Operator review required before final verdict."
        )
    elif participation_impossible or blocking_gaps:
        overall = "not-eligible"
        summary = (
            f"Participation Impossible: {impossible_reason}"
            if participation_impossible
            else f"Vendor does not meet mandatory criteria ({len(blocking_gaps)} blocking gap(s) identified)."
        )
    elif len(addressable_gaps) == 0:
        overall = "eligible"
        summary = "Vendor meets all evaluated eligibility criteria. Ready for bid preparation."
    else:
        overall = "eligible-with-gaps"
        summary = f"Vendor meets core criteria with {len(addressable_gaps)} addressable gap(s). Action required."

    return BidVerdict(
        overall=overall,
        summary=summary,
        verdicts=verdicts,
        gaps=gaps,
        days_to_deadline=days_to_deadline,
        participation_impossible=participation_impossible,
        impossible_reason=impossible_reason,
        low_confidence_fields=low_confidence_fields,
        audit_log=audit_log,
    )
