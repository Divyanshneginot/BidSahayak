import re
from datetime import datetime
from typing import Optional, Tuple
from src.models import RequirementMatrix, FieldEvidence
from src.text_extract import ExtractionResult


class DeterministicRegexExtractor:
    """
    Tier 3 Degradation Ladder:
    Pure deterministic rule-based and regex extraction engine.
    Guarantees that essential tender fields are extracted even in offline mode
    or when LLM calls fail.
    """

    @staticmethod
    def parse_inr(amount_str: str) -> Optional[int]:
        """Convert 'Rs. 50,000' or '5 Lakhs' or '₹1.5 Crore' into integer."""
        if not amount_str:
            return None
        clean = amount_str.replace(",", "").strip()
        
        # Check Crore
        cr_match = re.search(r"([\d\.]+)\s*(?:cr|crore|करोड़)", clean, re.I)
        if cr_match:
            try:
                return int(float(cr_match.group(1)) * 10_000_000)
            except ValueError:
                pass

        # Check Lakh
        lakh_match = re.search(r"([\d\.]+)\s*(?:lakh|lac|लाख)", clean, re.I)
        if lakh_match:
            try:
                return int(float(lakh_match.group(1)) * 100_000)
            except ValueError:
                pass

        # Check raw digits
        digits = re.findall(r"\d+", clean)
        if digits:
            try:
                return int("".join(digits))
            except ValueError:
                pass
        return None

    @classmethod
    def extract_emd(cls, extraction: ExtractionResult) -> Tuple[Optional[int], list[str], Optional[FieldEvidence]]:
        """Extract EMD amount and exemption clauses across all pages."""
        emd_pattern = re.compile(
            r"(?i)(?:earnest\s+money\s+deposit|b\.s\.d|emd|बयाना\s+राशि)[^\n\r]{0,40}?"
            r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?(?:\s*(?:lakh|crore|cr))?)",
            re.M,
        )
        exempt_categories = []
        found_amount = None
        best_evidence = None

        for page_num, page_data in extraction.pages.items():
            text = page_data.normalized_text
            
            # Check exemption mentions
            if re.search(r"(?i)(mse[s]?|micro\s+and\s+small|msme|udyam)\s*(?:are\s+)?exempt", text):
                if "micro" not in exempt_categories:
                    exempt_categories.extend(["micro", "small"])

            # Search EMD amount
            match = emd_pattern.search(text)
            if match and not found_amount:
                raw_val = match.group(1)
                parsed = cls.parse_inr(raw_val)
                if parsed and parsed > 500:  # Sensible minimum for EMD
                    found_amount = parsed
                    snippet = text[max(0, match.start() - 20) : min(len(text), match.end() + 60)].strip()
                    best_evidence = FieldEvidence(
                        field_name="emd_amount",
                        value_raw=raw_val,
                        value_normalised=found_amount,
                        confidence=0.85,
                        source_page=page_num,
                        source_snippet=snippet,
                    )

        return found_amount, exempt_categories or ["micro", "small"], best_evidence

    @classmethod
    def extract_turnover(cls, extraction: ExtractionResult) -> Tuple[Optional[int], Optional[FieldEvidence]]:
        """Extract annual turnover requirements."""
        turnover_pattern = re.compile(
            r"(?i)(?:turnover|turn\s*over|वार्षिक\s+कारोबार)[^\n\r]{0,50}?"
            r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?\s*(?:lakh|crore|cr))",
            re.M,
        )
        for page_num, page_data in extraction.pages.items():
            text = page_data.normalized_text
            match = turnover_pattern.search(text)
            if match:
                raw_val = match.group(1)
                parsed = cls.parse_inr(raw_val)
                if parsed:
                    snippet = text[max(0, match.start() - 15) : min(len(text), match.end() + 50)].strip()
                    evidence = FieldEvidence(
                        field_name="min_turnover",
                        value_raw=raw_val,
                        value_normalised=parsed,
                        confidence=0.80,
                        source_page=page_num,
                        source_snippet=snippet,
                    )
                    return parsed, evidence
        return None, None

    @classmethod
    def extract_deadline(cls, extraction: ExtractionResult) -> Tuple[Optional[datetime], Optional[FieldEvidence]]:
        """Extract bid submission closing date."""
        date_pattern = re.compile(
            r"(?i)(?:submission\s+(?:end|closing)\s+date|last\s+date\s+of\s+bid|अंतिम\s+तिथि)[^\n\r]{0,40}?"
            r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}(?:\s+\d{1,2}:\d{2})?)",
            re.M,
        )
        for page_num, page_data in extraction.pages.items():
            text = page_data.normalized_text
            match = date_pattern.search(text)
            if match:
                raw_date = match.group(1).strip()
                # Parse standard date formats
                parsed_dt = None
                for fmt in ["%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"]:
                    try:
                        parsed_dt = datetime.strptime(raw_date, fmt)
                        break
                    except ValueError:
                        continue
                if parsed_dt:
                    snippet = text[max(0, match.start() - 10) : min(len(text), match.end() + 30)].strip()
                    evidence = FieldEvidence(
                        field_name="submission_deadline",
                        value_raw=raw_date,
                        value_normalised=parsed_dt.isoformat(),
                        confidence=0.82,
                        source_page=page_num,
                        source_snippet=snippet,
                    )
                    return parsed_dt, evidence
        return None, None

    @classmethod
    def build_matrix(cls, extraction: ExtractionResult) -> RequirementMatrix:
        """Assembles a full RequirementMatrix using deterministic fallback rules."""
        emd_val, emd_exempts, emd_ev = cls.extract_emd(extraction)
        turnover_val, turnover_ev = cls.extract_turnover(extraction)
        deadline_dt, deadline_ev = cls.extract_deadline(extraction)

        evidence_fields = {}
        if emd_ev:
            evidence_fields["emd_amount"] = emd_ev
        if turnover_ev:
            evidence_fields["min_turnover"] = turnover_ev
        if deadline_ev:
            evidence_fields["submission_deadline"] = deadline_ev

        return RequirementMatrix(
            tender_id=extraction.tender_id,
            title=f"Tender {extraction.tender_id}",
            issuing_department="Public Procurement Authority",
            portal="CPPP",
            emd_amount=emd_val,
            emd_exempt_categories=emd_exempts,
            min_turnover=turnover_val,
            submission_deadline=deadline_dt,
            evidence_fields=evidence_fields,
            requires_class3_dsc=True,
        )
