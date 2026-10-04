import time
from typing import Optional
from pydantic import BaseModel, Field
from src.models import (
    RequirementMatrix,
    VendorProfile,
    BidVerdict,
)
from src.ingest import IngestWorker, IngestResult
from src.text_extract import TextWorker, ExtractionResult
from src.agent.extractor import ExtractorAgent
from src.evaluator import evaluate


class TraceEntry(BaseModel):
    step_name: str
    worker: str
    started_at: float
    duration_ms: float
    status: str
    tier_reached: int
    details: dict = Field(default_factory=dict)


class AssessmentSession(BaseModel):
    session_id: str
    tender_id: str
    current_state: str  # RECEIVED, TEXT_READY, STRUCTURED, EVALUATED, AWAITING_HUMAN, APPROVED
    ingest_result: Optional[IngestResult] = None
    matrix: Optional[RequirementMatrix] = None
    profile: Optional[VendorProfile] = None
    verdict: Optional[BidVerdict] = None
    skipped_pages: list[int] = Field(default_factory=list)
    is_ocr_available: bool = False
    trace: list[TraceEntry] = Field(default_factory=list)


class Supervisor:
    """
    Orchestrates the entire BidSahayak assessment workflow.
    Owns state transitions, audit trace recording, and deterministic gate enforcement.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.ingest_worker = IngestWorker()
        self.text_worker = TextWorker()
        self.extractor_agent = ExtractorAgent(api_key=api_key)

    def process_document(
        self,
        file_path: str,
        profile: Optional[VendorProfile] = None,
    ) -> AssessmentSession:
        session_id = f"SES-{int(time.time())}"
        trace: list[TraceEntry] = []

        # 1. Ingest Step
        t0 = time.time()
        ingest_res = self.ingest_worker.process(file_path)
        d_ms = (time.time() - t0) * 1000
        trace.append(TraceEntry(
            step_name="PDF Ingestion",
            worker="IngestWorker (W1)",
            started_at=t0,
            duration_ms=round(d_ms, 2),
            status="SUCCESS" if ingest_res.is_valid else "FAILED",
            tier_reached=1,
            details={"sha256": ingest_res.sha256_hash, "pages": ingest_res.page_count},
        ))

        if not ingest_res.is_valid:
            return AssessmentSession(
                session_id=session_id,
                tender_id=ingest_res.tender_id,
                current_state="FAILED",
                ingest_result=ingest_res,
                trace=trace,
            )

        # 2. Text Extraction Step
        t0 = time.time()
        text_res = self.text_worker.process(file_path, tender_id=ingest_res.tender_id)
        d_ms = (time.time() - t0) * 1000
        trace.append(TraceEntry(
            step_name="Text Normalization & Section Detection",
            worker="TextWorker (W2)",
            started_at=t0,
            duration_ms=round(d_ms, 2),
            status="SUCCESS",
            tier_reached=1,
            details={
                "is_scanned": text_res.is_scanned_document,
                "skipped_pages": text_res.skipped_pages,
                "sections": text_res.detected_sections,
                "total_chars": len(text_res.full_text),
            },
        ))

        # 3. Requirement Extraction Step (W4)
        t0 = time.time()
        matrix = self.extractor_agent.extract(text_res)
        d_ms = (time.time() - t0) * 1000
        trace.append(TraceEntry(
            step_name="Structured Extraction & Citation Verification",
            worker="ExtractorAgent (W4)",
            started_at=t0,
            duration_ms=round(d_ms, 2),
            status="SUCCESS",
            tier_reached=getattr(self.extractor_agent, "last_tier", 3),
            details={
                "tier": getattr(self.extractor_agent, "last_tier", 3),
                "fallback_reason": getattr(self.extractor_agent, "fallback_reason", None),
                "fields_extracted": len(matrix.evidence_fields),
                "emd": matrix.emd_amount,
                "turnover": matrix.min_turnover,
            },
        ))

        # 4. Evaluation Step (W5 - pure deterministic code)
        verdict = None
        state = "STRUCTURED"
        if profile:
            t0 = time.time()
            verdict = evaluate(matrix, profile)
            d_ms = (time.time() - t0) * 1000
            trace.append(TraceEntry(
                step_name="Deterministic Profile Evaluation",
                worker="EvaluatorWorker (W5)",
                started_at=t0,
                duration_ms=round(d_ms, 2),
                status="SUCCESS",
                tier_reached=1,
                details={"verdict": verdict.overall, "gaps_count": len(verdict.gaps)},
            ))
            state = "AWAITING_HUMAN" if verdict.overall == "needs-human-review" else "EVALUATED"

        return AssessmentSession(
            session_id=session_id,
            tender_id=ingest_res.tender_id,
            current_state=state,
            ingest_result=ingest_res,
            matrix=matrix,
            profile=profile,
            verdict=verdict,
            skipped_pages=text_res.skipped_pages,
            is_ocr_available=text_res.is_ocr_available,
            trace=trace,
        )
