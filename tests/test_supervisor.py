import os
import pytest
from src.supervisor import Supervisor
from src.models import VendorProfile


def test_supervisor_end_to_end_assessment():
    pdf_path = os.path.join("sample_tenders", "imd-tender.pdf")
    assert os.path.exists(pdf_path)

    supervisor = Supervisor(api_key=None)

    profile = VendorProfile(
        business_name="Bharat Electronics & Instruments",
        udyam_classification="Micro",
        is_manufacturing=True,
        is_trading=False,
        annual_turnover_last_3y=[2500000],
        years_in_business=4,
        certifications_held=["ISO 9001"],
        holds_class3_dsc=True,
    )

    session = supervisor.process_document(pdf_path, profile=profile)

    assert session.session_id.startswith("SES-")
    assert session.current_state in ["EVALUATED", "AWAITING_HUMAN"]
    assert session.matrix is not None
    assert session.verdict is not None
    assert len(session.trace) >= 4

    # Verify audit trace contains step names and latencies
    step_names = [t.step_name for t in session.trace]
    assert "PDF Ingestion" in step_names
    assert "Text Normalization & Section Detection" in step_names
    assert "Deterministic Profile Evaluation" in step_names
