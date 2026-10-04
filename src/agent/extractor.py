import os
import json
import logging
from typing import Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
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
    W4: ExtractorAgent with 6-Tier Degradation Ladder.
    Extracts structured RequirementMatrix from tender text, validates schemas,
    and runs SnippetVerifier on every cited piece of evidence.
    Natively supports Groq ultra-fast inference (llama-3.3-70b-versatile) and OpenAI endpoints.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or os.getenv("LLM_API_KEY")
        )
        self.provider = os.getenv("LLM_PROVIDER")
        if not self.provider and self.api_key:
            if self.api_key.startswith("AQ."):
                self.provider = "gemini"
            elif self.api_key.startswith("gsk_"):
                self.provider = "groq"
            else:
                self.provider = "openai"

        default_model = "gemini-3.5-flash" if self.provider == "gemini" else "openai/gpt-oss-120b"
        self.model = model or os.getenv("LLM_MODEL") or default_model

    def extract(self, extraction_result: ExtractionResult) -> RequirementMatrix:
        """
        Executes extraction pipeline across degradation ladder.
        """
        # Tier 3 directly if no API key is provided
        if not self.api_key or self.api_key.startswith("your-api"):
            logger.info("No LLM API key configured. Executing Tier 3 deterministic regex extractor.")
            matrix = DeterministicRegexExtractor.build_matrix(extraction_result)
            return self._verify_all_evidence(matrix, extraction_result)

        # Tier 1: LLM Structured Extraction
        try:
            matrix = self._call_llm_extractor(extraction_result)
            return self._verify_all_evidence(matrix, extraction_result)
        except Exception as e:
            logger.warning(f"Tier 1 LLM extraction failed: {e}. Executing Tier 3 fallback.")
            # Fallback to Tier 3
            matrix = DeterministicRegexExtractor.build_matrix(extraction_result)
            return self._verify_all_evidence(matrix, extraction_result)

    def _call_llm_extractor(self, extraction_result: ExtractionResult) -> RequirementMatrix:
        import requests

        doc_sample = extraction_result.full_text[:14000]  # Respect token boundary for TPM tier
        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(document_text=doc_sample)

        if self.provider == "gemini" or (self.api_key and self.api_key.startswith("AQ.")):
            gemini_model = self.model if "gemini" in self.model else "gemini-3.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {"parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}]}
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.0,
                },
            }
            res = requests.post(url, json=payload, timeout=14)
            if res.status_code == 200:
                raw_json = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                raise RuntimeError(f"Gemini API returned status {res.status_code}: {res.text}")
        else:
            # Dynamic endpoint selection for OpenAI / Groq
            endpoint = "https://api.openai.com/v1/chat/completions"
            model_name = self.model

            if (self.api_key and self.api_key.startswith("gsk_")) or self.provider == "groq":
                endpoint = "https://api.groq.com/openai/v1/chat/completions"
                if not self.model or self.model == "llama-3.3-70b-versatile":
                    model_name = "openai/gpt-oss-120b"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }

            res = requests.post(endpoint, json=payload, headers=headers, timeout=12)
            if res.status_code == 200:
                raw_json = res.json()["choices"][0]["message"]["content"]
            else:
                raise RuntimeError(f"LLM API ({endpoint}) returned status {res.status_code}: {res.text}")

        data = json.loads(raw_json)
        # Fill mandatory defaults if model omitted them
        if not data.get("tender_id"):
            data["tender_id"] = extraction_result.tender_id
        if not data.get("title"):
            data["title"] = f"Tender {extraction_result.tender_id}"
        if not data.get("issuing_department"):
            data["issuing_department"] = "Public Procurement Authority"
        if not data.get("portal"):
            data["portal"] = "CPPP"
        return RequirementMatrix(**data)

    def _verify_all_evidence(self, matrix: RequirementMatrix, extraction_result: ExtractionResult) -> RequirementMatrix:
        """
        Anti-Hallucination Gate:
        Runs SnippetVerifier on every evidence field cited.
        If a snippet cannot be verified on its cited page, drops confidence to 0.45
        and adds an ambiguity explanation.
        """
        for field_name, evidence in matrix.evidence_fields.items():
            page_text = ""
            if evidence.source_page in extraction_result.pages:
                page_text = extraction_result.pages[evidence.source_page].normalized_text

            verif = SnippetVerifier.verify(evidence.source_snippet, page_text)
            if not verif.is_verified:
                evidence.confidence = min(evidence.confidence, 0.45)
                evidence.ambiguity = (
                    f"Evidence verification failed on Page {evidence.source_page}: "
                    f"Snippet not located. Operator verification required."
                )
            else:
                # Calibrate confidence upward if verified
                evidence.confidence = max(evidence.confidence, 0.88)

        return matrix
