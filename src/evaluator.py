import os
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
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))


def calculate_effective_turnover(turnovers: list[int]) -> int:
    """Calculates average annual turnover across reported financial years (not max)."""
    if not turnovers:
        return 0
    return int(sum(turnovers) / len(turnovers))


def evaluate_dsc_timing(deadline: datetime, holds_dsc: bool, now: Optional[datetime] = None) -> str:
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
    if now is None:
        now = datetime.now(deadline.tzinfo)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=deadline.tzinfo)
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

    # 1. Identify low-confidence fields (< CONFIDENCE_THRESHOLD)
    for field_name, evidence in matrix.evidence_fields.items():
        if evidence.confidence < CONFIDENCE_THRESHOLD:
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

    # 5. Similar Work Experience Evaluation (% of estimated cost or explicit minimum)
    required_similar_work = None
    if getattr(matrix, "similar_work_min_value", None) and matrix.similar_work_min_value > 0:
        required_similar_work = matrix.similar_work_min_value
    elif (
        getattr(matrix, "estimated_cost", None)
        and getattr(matrix, "similar_work_percent", None)
        and matrix.similar_work_percent > 0
    ):
        required_similar_work = int(matrix.estimated_cost * (matrix.similar_work_percent / 100.0))

    if required_similar_work:
        req_name = "Similar Work Experience"
        ev_desc = f"Single completed work of ₹{required_similar_work:,}"
        if getattr(matrix, "similar_work_percent", None) and getattr(matrix, "estimated_cost", None):
            ev_desc += f" ({matrix.similar_work_percent}% of estimated cost ₹{matrix.estimated_cost:,})"

        if getattr(profile, "past_work_max_value", None) is None:
            verdicts.append(RequirementVerdict(
                requirement=req_name,
                status="unknown",
                reason="Enter your value to check this requirement.",
                evidence=ev_desc,
                remedy="Provide largest single completed similar work in vendor profile to evaluate this requirement.",
            ))
        elif profile.past_work_max_value >= required_similar_work:
            verdicts.append(RequirementVerdict(
                requirement=req_name,
                status="met",
                reason=f"Vendor's largest past work of ₹{profile.past_work_max_value:,} meets required ₹{required_similar_work:,}.",
                evidence=ev_desc,
            ))
        else:
            v = RequirementVerdict(
                requirement=req_name,
                status="gap",
                reason=f"Vendor largest past work ₹{profile.past_work_max_value:,} is below required ₹{required_similar_work:,}.",
                evidence=ev_desc,
                remedy="Partner via joint venture / consortium or furnish additional qualifying completion certificates.",
            )
            verdicts.append(v)
            gaps.append(v)

    # 6. Minimum Net Worth Evaluation
    if getattr(matrix, "min_net_worth", None) and matrix.min_net_worth > 0:
        req_name = "Minimum Net Worth"
        ev_desc = f"₹{matrix.min_net_worth:,}"
        if getattr(profile, "net_worth", None) is None:
            verdicts.append(RequirementVerdict(
                requirement=req_name,
                status="unknown",
                reason="Enter your value to check this requirement.",
                evidence=ev_desc,
                remedy="Provide net worth in vendor profile to evaluate this requirement.",
            ))
        elif profile.net_worth >= matrix.min_net_worth:
            verdicts.append(RequirementVerdict(
                requirement=req_name,
                status="met",
                reason=f"Vendor net worth of ₹{profile.net_worth:,} meets required ₹{matrix.min_net_worth:,}.",
                evidence=ev_desc,
            ))
        else:
            v = RequirementVerdict(
                requirement=req_name,
                status="gap",
                reason=f"Vendor net worth (₹{profile.net_worth:,}) is below mandatory ₹{matrix.min_net_worth:,}.",
                evidence=ev_desc,
                remedy="Submit Chartered Accountant Net Worth Certificate or strengthen audited balance sheet.",
            )
            verdicts.append(v)
            gaps.append(v)

    # 7. Submission Deadline & Class 3 DSC Timing Barrier (Original CAG/CPPP insight)
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

        if diff.total_seconds() < 0:
            participation_impossible = True
            impossible_reason = (
                f"Tender submission deadline has passed ({deadline.strftime('%d-%m-%Y %H:%M %Z')}). "
                "Tender is closed for bidding."
            )
            verdict = RequirementVerdict(
                requirement="Submission Deadline",
                status="gap",
                reason=impossible_reason,
                remedy="Tender is closed. Submission no longer permitted.",
            )
            verdicts.append(verdict)
            gaps.append(verdict)
        elif matrix.requires_class3_dsc:
            dsc_status = evaluate_dsc_timing(deadline, profile.holds_class3_dsc, now=cmp_now)
            if dsc_status == "gap_impossible":
                participation_impossible = True
                impossible_reason = (
                    f"A new Class 3 DSC takes 3–7 days to issue (official CPPP guidance). "
                    f"This tender closes in {days_to_deadline} days. Vendor lacks Class 3 DSC, "
                    "so issuance cannot be completed before the deadline."
                )
                verdict = RequirementVerdict(
                    requirement="Class 3 Digital Signature Certificate (DSC)",
                    status="gap",
                    reason=impossible_reason,
                    remedy="apply immediately — issuance takes 3–7 days",
                )
                verdicts.append(verdict)
                gaps.append(verdict)
            elif dsc_status == "gap_addressable":
                verdict = RequirementVerdict(
                    requirement="Class 3 Digital Signature Certificate (DSC)",
                    status="gap",
                    reason=f"Vendor lacks Class 3 DSC. Tender closes in {days_to_deadline} days.",
                    remedy="apply immediately — issuance takes 3–7 days",
                )
                verdicts.append(verdict)
                gaps.append(verdict)
            else:
                verdicts.append(RequirementVerdict(
                    requirement="Class 3 Digital Signature Certificate (DSC)",
                    status="met",
                    reason="Vendor holds valid Class 3 DSC required for e-procurement portal.",
                ))

    # 8. Overall Verdict Determination
    is_empty_matrix = (
        len(matrix.evidence_fields) == 0
        and matrix.emd_amount is None
        and matrix.min_turnover is None
        and matrix.submission_deadline is None
        and matrix.min_years_experience is None
        and not matrix.required_certifications
        and getattr(matrix, "similar_work_min_value", None) is None
        and getattr(matrix, "min_net_worth", None) is None
    )
    unresolved_fields = getattr(matrix, "unresolved_fields", [])

    blocking_gaps = []
    addressable_gaps = []
    for g in gaps:
        if "Class 3" in g.requirement and participation_impossible:
            blocking_gaps.append(g)
        elif g.requirement in [
            "Annual Turnover",
            "Experience (Years in Business)",
            "Similar Work Experience",
            "Minimum Net Worth",
            "Submission Deadline",
        ]:
            blocking_gaps.append(g)
        elif g.requirement == "Mandatory Certifications":
            blocking_gaps.append(g)
        else:
            addressable_gaps.append(g)


    has_unknown_requirements = any(v.status == "unknown" for v in verdicts)

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
    elif has_unknown_requirements:
        overall = "needs-human-review"
        summary = "Vendor input required for eligibility requirements. Enter your values to determine final eligibility."
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
