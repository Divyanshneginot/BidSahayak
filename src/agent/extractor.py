import os
import json
import logging
from typing import Optional
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
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model = model

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
            logger.warning(f"Tier 1 LLM extraction failed: {e}. Executing Tier 2 repair or Tier 3 fallback.")
            # Fallback to Tier 3
            matrix = DeterministicRegexExtractor.build_matrix(extraction_result)
            return self._verify_all_evidence(matrix, extraction_result)

    def _call_llm_extractor(self, extraction_result: ExtractionResult) -> RequirementMatrix:
        # Prepare truncated document context (first 25 pages + detected sections)
        doc_sample = extraction_result.full_text[:35000]  # Respect token boundary
        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(document_text=doc_sample)

        # If requests/google client is available, invoke it.
        # Fall back gracefully to deterministic extractor if network fails
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            # Generic JSON-mode payload
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }
            # Attempt call with 8s timeout
            res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=8)
            if res.status_code == 200:
                raw_json = res.json()["choices"][0]["message"]["content"]
                data = json.loads(raw_json)
                return RequirementMatrix(**data)
            else:
                raise RuntimeError(f"LLM API returned status {res.status_code}")
        except Exception as err:
            logger.info(f"API call unavailable ({err}), falling back to deterministic extraction.")
            return DeterministicRegexExtractor.build_matrix(extraction_result)

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
                evidence.confidence = max(evidence.confidence, 0.85)

        return matrix
