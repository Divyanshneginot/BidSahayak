from datetime import datetime, date
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field


class FieldEvidence(BaseModel):
    field_name: str
    value_raw: str
    value_normalised: Any = None
    confidence: float = Field(ge=0.0, le=1.0)
    source_page: int
    source_snippet: str
    ambiguity: Optional[str] = None


class PastWorkRequirement(BaseModel):
    work_type: str
    min_value: int = 0
    min_count: int = 1


class RequirementMatrix(BaseModel):
    tender_id: str
    title: str = "Tender Document"
    issuing_department: str = "Unknown"
    state: Optional[str] = None
    portal: Optional[str] = "CPPP"
    
    emd_amount: Optional[int] = None
    emd_exempt_categories: list[str] = Field(default_factory=list)
    min_turnover: Optional[int] = None
    turnover_window_years: Optional[int] = 3
    min_years_experience: Optional[int] = None
    required_certifications: list[str] = Field(default_factory=list)
    required_past_work: list[PastWorkRequirement] = Field(default_factory=list)
    submission_deadline: Optional[datetime] = None
    technical_bid_date: Optional[datetime] = None
    financial_bid_date: Optional[datetime] = None
    eligible_categories: list[str] = Field(default_factory=list)
    requires_class3_dsc: bool = True
    startup_clause_active: bool = False
    unresolved_fields: list[str] = Field(default_factory=list)
    
    evidence_fields: dict[str, FieldEvidence] = Field(default_factory=dict)


class VendorProfile(BaseModel):
    business_name: str
    state: str = "Uttar Pradesh"
    udyam_classification: Optional[Literal["Micro", "Small", "Medium"]] = None
    udyam_valid_until: Optional[date] = None
    udyam_covers_tender_item: bool = True
    is_manufacturing: bool = True
    is_trading: bool = False
    annual_turnover_last_3y: list[int] = Field(default_factory=list)
    years_in_business: int = 0
    certifications_held: list[str] = Field(default_factory=list)
    past_work_count: int = 0
    past_work_max_value: int = 0
    holds_class3_dsc: bool = True
    startup_india: bool = False


class RequirementVerdict(BaseModel):
    requirement: str
    status: Literal["met", "gap", "unknown", "waived", "not-applicable"]
    reason: str
    evidence: Optional[str] = None
    remedy: Optional[str] = None


class BidVerdict(BaseModel):
    overall: Literal["eligible", "eligible-with-gaps", "not-eligible", "needs-human-review"]
    summary: str
    verdicts: list[RequirementVerdict] = Field(default_factory=list)
    gaps: list[RequirementVerdict] = Field(default_factory=list)
    days_to_deadline: Optional[int] = None
    approved_by_human: bool = False
    participation_impossible: bool = False
    impossible_reason: Optional[str] = None
    low_confidence_fields: list[str] = Field(default_factory=list)
    audit_log: list[dict] = Field(default_factory=list)
