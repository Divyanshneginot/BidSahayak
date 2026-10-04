import re
from datetime import datetime
from typing import Optional, Tuple, Any
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
        """Convert 'Rs. 50,000' or '5 Lakhs' or '₹1.5 Crore' or '10,000.00' into integer."""
        if not amount_str:
            return None
        clean = amount_str.replace(",", "").strip()
        
        # Check Crore
        cr_match = re.search(r"([\d\.]+)\s*(?:cr|crore|करोड़)", clean, re.I)
        if cr_match:
            try:
                return int(round(float(cr_match.group(1)) * 10_000_000))
            except ValueError:
                pass

        # Check Lakh
        lakh_match = re.search(r"([\d\.]+)\s*(?:lakh|lac|लाख)", clean, re.I)
        if lakh_match:
            try:
                return int(round(float(lakh_match.group(1)) * 100_000))
            except ValueError:
                pass

        # Check decimal or standard number e.g. 10000.00 or 75000.50
        num_match = re.search(r"(\d+(?:\.\d+)?)", clean)
        if num_match:
            try:
                return int(round(float(num_match.group(1))))
            except ValueError:
                pass
        return None

    # ---- readability guard ---------------------------------------------------
    TOFU_CHARS = "\u25a0\ufffd"          # ■ and U+FFFD: a text layer with no glyphs

    @classmethod
    def _is_unreadable(cls, text: str) -> bool:
        """True when a text layer carries no extractable meaning (e.g. a Devanagari
        PDF rendered without an embedded font produces U+25A0 for every glyph)."""
        if not text or len(text.strip()) < 40:
            return True
        bad = sum(1 for c in text if c in cls.TOFU_CHARS)
        return (bad / max(1, len(text))) > 0.15

    # ---- MSE / EMD exemption detection ---------------------------------------
    MSE_TERMS = (r"(?:micro\s*(?:and|/|&|-)\s*small|micro\s+enterprises?|small\s+enterprises?|"
                 r"mse[s]?\b|msme[s]?\b|udyam|सूक्ष्म|लघु)")
    GRANT_TERMS = (r"(?:exempt(?:ed|ion)?|eligible\s+for\s+(?:relaxation|exemption)|waiv(?:ed|er)|छूट)")
    TRADER_CARVEOUT = (r"(?:traders?\s+(?:are\s+)?(?:strictly\s+)?not\s+eligible|"
                       r"not\s+(?:be\s+)?applicable\s+(?:to|for)\s+trading|not\s+applicable\s+for\s+trading\s+purpose)")
    SCOPE_CARVEOUTS = [
        r"not\s+(?:for\s+)?fee[\s-]?collection",
        r"not\s+applicable\s+to\s+this\s+(?:contract|tender|work|concession)",
        r"exemption\s+(?:shall\s+)?not\s+apply",
        r"shall\s+not\s+be\s+exempt",
    ]

    @classmethod
    def detect_mse_exemption(cls, text: str) -> Tuple[list, Optional[str], bool]:
        """Bidirectional grant detection around every MSE mention.

        Returns (categories, note, scope_excluded):
          categories   -> ["micro","small"] when a grant is found, else []
          note         -> a bidder-level carve-out worth surfacing (e.g. traders excluded)
          scope_excluded -> True when the exemption is explicitly out of scope for this
                            tender (e.g. "not fee-collection concessions"), which must
                            make the exemption False rather than True.
        """
        if cls._is_unreadable(text):
            return [], None, False
        grants = []
        for m in re.finditer(cls.MSE_TERMS, text, re.I):
            lo, hi = max(0, m.start() - 140), min(len(text), m.end() + 140)
            window = text[lo:hi]
            if re.search(cls.GRANT_TERMS, window, re.I):
                grants.append(window)
        if not grants:
            return [], None, False
        joined = " ".join(grants)
        note = None
        if re.search(cls.TRADER_CARVEOUT, joined, re.I):
            note = ("MSE exemption granted, but traders are excluded - manufacturing / "
                    "service providers only.")
        for pat in cls.SCOPE_CARVEOUTS:
            hit = re.search(pat, joined, re.I)
            if hit:
                scope_note = (note + " | " if note else "") + (
                    f"MSE exemption excluded for this tender's scope: \"{hit.group(0)}\".")
                return [], scope_note, True
        return ["micro", "small"], note, False

    @classmethod
    def extract_emd(cls, extraction: ExtractionResult) -> Tuple[Optional[int], list[str], Optional[FieldEvidence], Optional[str]]:
        """Extract EMD amount and exemption clauses across all pages."""
        emd_pattern = re.compile(
            r"(?i)(?:earnest\s+money\s+deposit|b\.s\.d|emd|बयाना\s+राशि)[^\n\r]{0,40}?"
            r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?(?:\s*(?:lakh|crore|cr))?)",
            re.M,
        )
        exempt_categories = []
        found_amount = None
        best_evidence = None
        exemption_checked = False
        exemption_note = None

        for page_num, page_data in extraction.pages.items():
            text = page_data.normalized_text
            
            # Exemption: bidirectional grant detection with carve-outs (F: G-benchmark exemption field)
            if not exemption_checked:
                cats, note, scope_excluded = cls.detect_mse_exemption(text)
                if cats:
                    exempt_categories = cats
                    exemption_note = note
                    exemption_checked = True
                elif scope_excluded:
                    exemption_note = note          # grant exists but is out of scope for this tender
                    exemption_checked = True

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

        # Fail closed: never default to assumed exemptions
        return found_amount, exempt_categories, best_evidence, exemption_note

    TURNOVER_KW = (r"(?:average\s+(?:annual\s+)?turnover|annual\s+turnover|turn\s*over|"
                   r"औसत\s+वार्षिक\s+कारोबार|वार्षिक\s+कारोबार|कारोबार)")
    TURNOVER_AMOUNT = (r"((?:rs\.?|inr|₹)?\s*\d[\d,]*(?:\.\d+)?"
                       r"\s*(?:crore|cr|lakh|lakhs|lac|करोड़|लाख)?)")
    ELIGIBILITY_CUES = (r"(?:minimum|min\.?|at\s+least|not\s+less\s+than|must\s+(?:have|be|achieve)|"
                        r"should\s+be|average|न्यूनतम|औसत)")

    @classmethod
    def _collect_turnover(cls, text: str):
        """All turnover candidates on one page, as (eligibility_cued, start, parsed, raw, snippet)."""
        pattern = re.compile(cls.TURNOVER_KW + r"[^\n\r]{0,70}?" + cls.TURNOVER_AMOUNT, re.I | re.M)
        out = []
        for m in pattern.finditer(text):
            raw_val, parsed = m.group(1), cls.parse_inr(m.group(1))
            if not parsed or parsed < 100_000:          # below 1 lakh is noise, not an eligibility bar
                continue
            lo, hi = max(0, m.start() - 60), min(len(text), m.end() + 60)
            cued = bool(re.search(cls.ELIGIBILITY_CUES, text[lo:hi], re.I))
            snippet = text[max(0, m.start() - 25):min(len(text), m.end() + 60)].strip()
            out.append((cued, m.start(), parsed, raw_val, snippet))
        return out

    @classmethod
    def extract_turnover(cls, extraction: ExtractionResult) -> Tuple[Optional[int], Optional[FieldEvidence]]:
        """Minimum annual / average turnover requirement.

        Unit words are optional (documents routinely write 'Rs. 25,00,000'), Indian
        grouping is handled via parse_inr, and eligibility-cued clauses win over
        incidental mentions. Unreadable pages are skipped entirely.
        """
        candidates = []
        for page_num, page_data in extraction.pages.items():
            text = page_data.normalized_text
            if cls._is_unreadable(text):
                continue
            for cued, start, parsed, raw_val, snippet in cls._collect_turnover(text):
                candidates.append((0 if cued else 1, page_num, start, parsed, raw_val, snippet, cued))
        if not candidates:
            return None, None
        candidates.sort(key=lambda c: (c[0], c[1], c[2]))
        _, page_num, _, parsed, raw_val, snippet, cued = candidates[0]
        return parsed, FieldEvidence(
            field_name="min_turnover",
            value_raw=raw_val.strip(),
            value_normalised=parsed,
            confidence=0.85 if cued else 0.60,
            source_page=page_num,
            source_snippet=snippet,
            ambiguity=None if cued else "Turnover clause found without an explicit minimum/eligibility cue.",
        )

    @classmethod
    def extract_deadline(cls, extraction_or_text: Any) -> Any:
        """Extract bid submission closing date from ExtractionResult or text string."""
        date_pattern = re.compile(
            r"(?i)(?:submission\s+(?:end|closing)(?:\s+date)?|last\s+date\s+(?:of|for)\s+(?:bid|submission)|"
            r"closing\s+date|due\s+date|submission\s+deadline|bid\s+closing|अंतिम\s+तिथि|निविदा\s+प्रस्तुत)[^\n\r]{0,50}?"
            r"((?:\d{4}-\d{2}-\d{2})|(?:\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}))",
            re.M,
        )

        def _parse_raw(raw: str) -> Optional[datetime]:
            m = re.search(r"(\d{4}-\d{2}-\d{2})|(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})", raw)
            if not m:
                return None
            dstr = m.group(1) or m.group(2)
            for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(dstr, fmt)
                except ValueError:
                    pass
            return None

        # Direct string call support
        if isinstance(extraction_or_text, str):
            match = date_pattern.search(extraction_or_text)
            if match:
                return _parse_raw(match.group(1))
            return _parse_raw(extraction_or_text)

        # ExtractionResult call support
        for page_num, page_data in extraction_or_text.pages.items():
            text = page_data.normalized_text
            match = date_pattern.search(text)
            if match:
                raw_date = match.group(1).strip()
                parsed_dt = _parse_raw(raw_date)
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
        emd_val, emd_exempts, emd_ev, exemption_note = cls.extract_emd(extraction)
        turnover_val, turnover_ev = cls.extract_turnover(extraction)
        deadline_dt, deadline_ev = cls.extract_deadline(extraction)

        evidence_fields = {}
        if emd_ev:
            evidence_fields["emd_amount"] = emd_ev
        if turnover_ev:
            evidence_fields["min_turnover"] = turnover_ev
        if deadline_ev:
            evidence_fields["submission_deadline"] = deadline_ev

        # Fail closed: anything not found is explicitly unresolved, never assumed.
        unresolved = []
        if emd_val is None:
            unresolved.append("emd_amount")
        if turnover_val is None:
            unresolved.append("min_turnover")
        if deadline_dt is None:
            unresolved.append("submission_deadline")
        unreadable = all(cls._is_unreadable(p.normalized_text) for p in extraction.pages.values()) if extraction.pages else True
        if unreadable:
            unresolved = ["emd_amount", "min_turnover", "submission_deadline"]

        if emd_ev and exemption_note:
            emd_ev.ambiguity = exemption_note

        return RequirementMatrix(
            tender_id=extraction.tender_id,
            title=f"Tender {extraction.tender_id}",
            issuing_department="Public Procurement Authority",
            portal="CPPP",
            emd_amount=emd_val,
            emd_exempt_categories=emd_exempts,
            min_turnover=turnover_val,
            submission_deadline=deadline_dt,
            unresolved_fields=unresolved,
            evidence_fields=evidence_fields,
            requires_class3_dsc=True,
        )
