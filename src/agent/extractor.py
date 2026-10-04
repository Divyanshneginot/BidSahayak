import os
import re
import json
import logging
from typing import Optional, Any
try:
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv()
    parent_env = Path(__file__).resolve().parents[2] / ".env"
    if parent_env.exists():
        load_dotenv(parent_env)
except ImportError:
    pass

from src.models import RequirementMatrix, FieldEvidence
from src.text_extract import ExtractionResult
from src.verify import SnippetVerifier
from src.regex_fallback import DeterministicRegexExtractor
from src.agent.prompts import (
    SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT_TEMPLATE,
    REPAIR_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class ExtractorAgent:
    """
    W4: ExtractorAgent with verifiable Agent Loop.
    Architecture:
    - Tier 1: LLM Extraction with Page-Aware Section Retrieval (Gemini / Groq / OpenAI)
    - Anti-Hallucination Gate: Citation & Value Verification via SnippetVerifier
    - Agentic Self-Repair: On verification failure, calls REPAIR_PROMPT_TEMPLATE (max 2 retries)
    - Tier 3: Deterministic Regex Extractor (zero-dependency fallback)
    Every step is recorded in self.audit_trace.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.provider = os.getenv("LLM_PROVIDER")
        if api_key is None:
            if self.provider == "groq":
                self.api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
            elif self.provider == "openai":
                self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            elif self.provider == "gemini":
                self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
            else:
                self.api_key = (
                    os.getenv("GROQ_API_KEY")
                    or os.getenv("LLM_API_KEY")
                    or os.getenv("GEMINI_API_KEY")
                )
        else:
            self.api_key = api_key

        if not self.provider and self.api_key:
            if self.api_key.startswith("AIza") or self.api_key.startswith("AQ."):
                self.provider = "gemini"
            elif self.api_key.startswith("gsk_"):
                self.provider = "groq"
            elif self.api_key.startswith("sk-"):
                self.provider = "openai"
            else:
                self.provider = "gemini"

        default_model = "gemini-2.0-flash" if self.provider == "gemini" else "openai/gpt-oss-120b"
        self.model = model or os.getenv("LLM_MODEL") or default_model
        self.last_tier = 3
        self.fallback_reason: Optional[str] = None
        self.audit_trace: list[dict] = []

    @classmethod
    def _retrieve_relevant_sections(cls, extraction_result: ExtractionResult, max_chars: int = 24000) -> str:
        """
        Page-aware chunking and keyword/section retrieval.
        Scans all document pages (handling 40+ page tenders) for critical procurement clauses:
        - Basic tender info (pages 1-2)
        - ITB (Instructions to Bidders)
        - Eligibility criteria (turnover, experience, net worth)
        - EMD / Bid Security clauses & Bank Guarantee requirements
        - Exemption clauses (GFR 170/173, MSME, Startups)
        - Critical dates (submission deadline, opening date)
        - Annexures & Proformas
        Returns concatenated page excerpts prefixed with '--- PAGE {n} ---'.
        """
        if not extraction_result.pages:
            return extraction_result.full_text[:max_chars]

        total_chars = sum(len(p.normalized_text) for p in extraction_result.pages.values())
        if total_chars <= max_chars:
            return "\n\n".join(
                f"--- PAGE {p_num} ---\n{p_data.normalized_text}"
                for p_num, p_data in sorted(extraction_result.pages.items())
            )

        SECTION_KEYWORDS = [
            (r"(?i)\b(earnest\s+money|bid\s+security|emd|बयाना\s+राशि)\b", 4),
            (r"(?i)\b(turnover|annual\s+turnover|कारोबार|वार्षिक\s+कारोबार)\b", 4),
            (r"(?i)\b(eligibility|qualifying|qualification|criteria|पात्रता|शर्तें)\b", 3),
            (r"(?i)\b(exemption|exempted|msme|udyam|startup|gfr\s*170|gfr\s*173|छूट)\b", 4),
            (r"(?i)\b(deadline|closing\s+date|last\s+date|due\s+date|submission\s+date|अंतिम\s+तिथि)\b", 3),
            (r"(?i)\b(similar\s+work|experience|past\s+performance|अनुभव)\b", 3),
            (r"(?i)\b(net\s+worth|solvency|financial\s+standing)\b", 3),
            (r"(?i)\b(class\s*3\s*dsc|digital\s+signature|dsc)\b", 2),
            (r"(?i)\b(instructions\s+to\s+bidders|itb|बोलीदाताओं)\b", 2),
            (r"(?i)\b(annexure|appendix|proforma|schedule|प्रपत्र)\b", 2),
        ]

        scored_pages: list[tuple[int, int, str]] = []
        for page_num, page_data in sorted(extraction_result.pages.items()):
            text = page_data.normalized_text
            score = 0
            if page_num == 1:
                score += 5
            elif page_num == 2:
                score += 3

            for pattern, weight in SECTION_KEYWORDS:
                if re.search(pattern, text):
                    score += weight

            scored_pages.append((score, page_num, text))

        chosen_pages: set[int] = {1}
        if 2 in extraction_result.pages:
            chosen_pages.add(2)

        remaining = [sp for sp in scored_pages if sp[1] not in chosen_pages and sp[0] > 0]
        remaining.sort(key=lambda x: x[0], reverse=True)

        current_chars = sum(len(extraction_result.pages[p].normalized_text) for p in chosen_pages)
        for score, page_num, text in remaining:
            if current_chars + len(text) > max_chars:
                remaining_budget = max_chars - current_chars
                if remaining_budget >= 800:
                    chosen_pages.add(page_num)
                break
            chosen_pages.add(page_num)
            current_chars += len(text)

        chunks = []
        for page_num in sorted(chosen_pages):
            p_text = extraction_result.pages[page_num].normalized_text
            chunks.append(f"--- PAGE {page_num} ---\n{p_text}")

        return "\n\n".join(chunks)

    def extract(self, extraction_result: ExtractionResult) -> RequirementMatrix:
        """
        Executes real agent loop:
        1. Page-aware section retrieval
        2. LLM structured extraction (Tier 1)
        3. Verification of citations & values via SnippetVerifier
        4. Self-repair loop (up to 2 retries via REPAIR_PROMPT_TEMPLATE on verification failures)
        5. Deterministic regex fallback (Tier 3) if LLM fails or fails verification repeatedly
        """
        self.audit_trace = []

        # Zero API key -> direct deterministic Tier 3 fallback
        if not self.api_key or self.api_key.startswith("your-api"):
            logger.info("No LLM API key configured. Executing Tier 3 deterministic regex extractor.")
            self.last_tier = 3
            self.fallback_reason = "No API key configured - running Tier 3 deterministic regex"
            self.audit_trace.append({
                "step": "deterministic_fallback",
                "tier": 3,
                "reason": self.fallback_reason,
            })
            matrix = DeterministicRegexExtractor.build_matrix(extraction_result)
            verified_matrix, _ = self._verify_all_evidence(matrix, extraction_result)
            return verified_matrix

        # Real Agent Loop with Self-Repair (Tier 1)
        doc_text = self._retrieve_relevant_sections(extraction_result)
        initial_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(document_text=doc_text)
        max_retries = 2
        last_error = None
        last_raw_dict = None
        failures = []

        for attempt in range(max_retries + 1):
            try:
                if attempt == 0:
                    self.audit_trace.append({
                        "step": "initial_extraction_call",
                        "tier": 1,
                        "provider": self.provider,
                        "model": self.model,
                        "attempt": attempt,
                    })
                    raw_dict = self._call_llm(initial_prompt)
                else:
                    self.audit_trace.append({
                        "step": "repair_prompt_call",
                        "tier": 1,
                        "attempt": attempt,
                        "validation_errors": [f["error"] for f in failures],
                    })
                    val_err_str = "\n".join(f"- Field '{f['field']}': {f['error']}" for f in failures)
                    repair_prompt = REPAIR_PROMPT_TEMPLATE.format(
                        validation_error=val_err_str,
                        previous_output=json.dumps(last_raw_dict or {}, indent=2),
                    )
                    raw_dict = self._call_llm(repair_prompt)

                last_raw_dict = raw_dict
                matrix = self._parse_matrix_dict(raw_dict, extraction_result.tender_id)
                verified_matrix, failures = self._verify_all_evidence(matrix, extraction_result)

                if not failures:
                    self.audit_trace.append({
                        "step": "citation_verification",
                        "status": "PASS",
                        "attempt": attempt,
                        "verified_fields": list(matrix.evidence_fields.keys()),
                    })
                    self.last_tier = 1
                    self.fallback_reason = None
                    return verified_matrix
                else:
                    self.audit_trace.append({
                        "step": "citation_verification",
                        "status": "FAIL",
                        "attempt": attempt,
                        "failures": failures,
                    })
                    last_error = f"Verification failures on fields: {[f['field'] for f in failures]}"

            except Exception as e:
                logger.warning(f"Agent loop attempt {attempt} encountered error: {e}")
                last_error = str(e)
                self.audit_trace.append({
                    "step": "llm_call_error",
                    "attempt": attempt,
                    "error": str(e),
                })

        logger.warning(f"LLM verification unresolved after {max_retries} attempts: {last_error}. Executing Tier 3 fallback.")
        self.last_tier = 3
        self.fallback_reason = f"LLM tier failed verification: {last_error}"
        self.audit_trace.append({
            "step": "fallback_to_regex",
            "tier": 3,
            "reason": self.fallback_reason,
        })
        matrix = DeterministicRegexExtractor.build_matrix(extraction_result)
        verified_matrix, _ = self._verify_all_evidence(matrix, extraction_result)
        return verified_matrix

    def _call_llm(self, prompt_text: str) -> dict:
        import requests

        if (self.provider == "gemini" or (self.api_key and (self.api_key.startswith("AIza") or self.api_key.startswith("AQ.")))) and self.provider != "groq":
            gemini_model = self.model if "gemini" in self.model else "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt_text}"}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.0,
                },
            }
            res = requests.post(url, json=payload, timeout=20)
            if res.status_code == 200:
                raw_json = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                raise RuntimeError(f"Gemini API returned status {res.status_code}: {res.text}")
        else:
            endpoint = "https://api.openai.com/v1/chat/completions"
            model_name = self.model

            if (self.api_key and self.api_key.startswith("gsk_")) or self.provider == "groq":
                endpoint = "https://api.groq.com/openai/v1/chat/completions"
                if not self.model or self.model in ["llama-3.3-70b-versatile", "default"]:
                    model_name = "openai/gpt-oss-120b"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_text},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }
            import time
            raw_json = None
            for retry_429 in range(4):
                res = requests.post(endpoint, json=payload, headers=headers, timeout=25)
                if res.status_code == 429:
                    time.sleep(7)
                    continue
                if res.status_code == 200:
                    raw_json = res.json()["choices"][0]["message"]["content"]
                    break
                else:
                    raise RuntimeError(f"LLM API ({endpoint}) returned status {res.status_code}: {res.text}")
            if raw_json is None:
                raise RuntimeError(f"LLM API ({endpoint}) rate limited after 4 retries")

        clean_json = raw_json.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
            clean_json = re.sub(r"\s*```$", "", clean_json)
        return json.loads(clean_json)

    @staticmethod
    def _parse_matrix_dict(data: dict, tender_id: str) -> RequirementMatrix:
        for str_field in ["tender_id", "title", "issuing_department", "state", "portal"]:
            if str_field in data and isinstance(data[str_field], dict):
                data[str_field] = str(data[str_field].get("value") or "")
        if not data.get("tender_id"):
            data["tender_id"] = tender_id
        if not data.get("title"):
            data["title"] = f"Tender {tender_id}"
        if not data.get("issuing_department"):
            data["issuing_department"] = "Public Procurement Authority"
        if not data.get("portal"):
            data["portal"] = "CPPP"
        for list_field in ["required_certifications", "required_past_work", "emd_exempt_categories", "unresolved_fields"]:
            if data.get(list_field) is None:
                data[list_field] = []
        if isinstance(data.get("evidence_fields"), list):
            data["evidence_fields"] = {
                item.get("field_name", f"field_{i}"): item
                for i, item in enumerate(data["evidence_fields"])
                if isinstance(item, dict)
            }
        if "evidence_fields" in data and isinstance(data["evidence_fields"], dict):
            cleaned_ev = {}
            for k, v in data["evidence_fields"].items():
                if isinstance(v, dict):
                    v.setdefault("field_name", k)
                    if v.get("source_page") is not None and v.get("source_snippet"):
                        v["value_raw"] = str(v.get("value_raw") or "")
                        cleaned_ev[k] = v
            data["evidence_fields"] = cleaned_ev
        return RequirementMatrix(**data)

    def _verify_all_evidence(
        self, matrix: RequirementMatrix, extraction_result: ExtractionResult
    ) -> tuple[RequirementMatrix, list[dict]]:
        """
        Anti-Hallucination Gate:
        Runs SnippetVerifier on every evidence field cited.
        Collects failures for agent repair loop.
        """
        failures = []
        for field_name, evidence in matrix.evidence_fields.items():
            if evidence.source_page is None or not evidence.source_snippet:
                continue
            page_text = ""
            if evidence.source_page in extraction_result.pages:
                page_text = extraction_result.pages[evidence.source_page].normalized_text

            verif = SnippetVerifier.verify(evidence.source_snippet, page_text)
            if not verif.is_verified:
                evidence.confidence = min(evidence.confidence, 0.45)
                evidence.ambiguity = (
                    f"Evidence verification failed on Page {evidence.source_page}: "
                    f"Snippet not located on cited page. Operator verification required."
                )
                failures.append({
                    "field": field_name,
                    "error": f"Snippet '{evidence.source_snippet[:50]}...' not found on page {evidence.source_page}",
                    "source_page": evidence.source_page,
                    "snippet": evidence.source_snippet,
                })
            else:
                val_to_check = (
                    evidence.value_normalised
                    if evidence.value_normalised is not None
                    else evidence.value_raw
                )
                val_res = SnippetVerifier.verify_value(evidence.source_snippet, val_to_check)
                if not val_res.is_verified:
                    evidence.confidence = min(evidence.confidence, 0.30)
                    evidence.ambiguity = (
                        f"Value round-trip verification failed on Page {evidence.source_page}: "
                        f"{val_res.reason}"
                    )
                    failures.append({
                        "field": field_name,
                        "error": f"Extracted value '{val_to_check}' does not match snippet on page {evidence.source_page}",
                        "source_page": evidence.source_page,
                        "snippet": evidence.source_snippet,
                    })

        return matrix, failures
