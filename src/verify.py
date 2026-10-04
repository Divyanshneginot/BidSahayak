import unicodedata
import re
from difflib import SequenceMatcher
from typing import Optional, Tuple, Any
from pydantic import BaseModel


class VerificationResult(BaseModel):
    is_verified: bool
    match_ratio: float
    reason: str
    verified_snippet: Optional[str] = None


class SnippetVerifier:
    """
    Verifies that an extracted field's source snippet actually exists
    on the cited document page. Rejects hallucinated citations.
    """

    @staticmethod
    def _clean(text: str) -> str:
        if not text:
            return ""
        norm = unicodedata.normalize("NFKC", text)
        norm = re.sub(r"[\u200b-\u200f\ufeff]", "", norm)
        # Collapse whitespace
        return " ".join(norm.split())

    @staticmethod
    def _strip_punct(text: str) -> str:
        """Strip punctuation and normalize digits/spaces for robust comparison."""
        return re.sub(r"[^\w\s]", "", text)

    @classmethod
    def verify(
        cls,
        snippet: str,
        page_text: str,
        min_fuzzy_ratio: float = 0.80,
    ) -> VerificationResult:
        if not snippet or not snippet.strip():
            return VerificationResult(
                is_verified=False,
                match_ratio=0.0,
                reason="Citation error: empty or blank snippet provided",
            )

        if not page_text or not page_text.strip():
            return VerificationResult(
                is_verified=False,
                match_ratio=0.0,
                reason="Page text is empty or unscannable",
            )

        clean_snippet = cls._clean(snippet)
        clean_page = cls._clean(page_text)

        # 1. Exact substring match
        if clean_snippet in clean_page:
            return VerificationResult(
                is_verified=True,
                match_ratio=1.0,
                reason="Exact substring match verified on cited page",
                verified_snippet=clean_snippet,
            )

        # 2. Case-insensitive substring match
        if clean_snippet.lower() in clean_page.lower():
            return VerificationResult(
                is_verified=True,
                match_ratio=0.99,
                reason="Case-insensitive match verified on cited page",
                verified_snippet=clean_snippet,
            )

        # 3. Punctuation-stripped match (handles "Rs." vs "Rs" and "50,000" vs "50000")
        nopunct_snippet = cls._strip_punct(clean_snippet.lower())
        nopunct_page = cls._strip_punct(clean_page.lower())
        if nopunct_snippet and nopunct_snippet in nopunct_page:
            return VerificationResult(
                is_verified=True,
                match_ratio=0.95,
                reason="Punctuation-normalized match verified on cited page",
                verified_snippet=clean_snippet,
            )

        # 4. Word-level or sliding window fuzzy matching
        snippet_words = clean_snippet.split()
        page_words = clean_page.split()
        n_words = len(snippet_words)

        if n_words > 0 and len(page_words) >= n_words:
            best_ratio = 0.0
            best_window = ""
            for i in range(len(page_words) - n_words + 1):
                window = " ".join(page_words[i : i + n_words])
                ratio = SequenceMatcher(
                    None,
                    cls._strip_punct(clean_snippet.lower()),
                    cls._strip_punct(window.lower()),
                ).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_window = window
                    if best_ratio >= 0.95:
                        break

            if best_ratio >= min_fuzzy_ratio:
                return VerificationResult(
                    is_verified=True,
                    match_ratio=round(best_ratio, 3),
                    reason=f"Fuzzy match verified on cited page ({best_ratio:.1%} similarity)",
                    verified_snippet=best_window,
                )

        return VerificationResult(
            is_verified=False,
            match_ratio=0.0,
            reason=(
                f"Snippet could not be verified on cited page. Flagged for human review."
            ),
        )

    @classmethod
    def verify_value(cls, value: Any, snippet: str) -> Tuple[bool, float]:
        """
        Rounds-trips an extracted value against its cited snippet.
        If the value is not reflected in the snippet text, confidence is downgraded to <= 0.30.
        Code may only lower confidence, never raise it.
        """
        if value is None or not snippet:
            return False, 0.20

        clean_snip = cls._clean(str(snippet)).lower()
        val_str = str(value)

        # 1. Exact substring check
        if val_str in clean_snip:
            return True, 0.85

        # 2. Check formatted number representations (commas, Lakh, Crore)
        if isinstance(value, (int, float)):
            val_int = int(value)
            formatted = f"{val_int:,}"
            if formatted in clean_snip:
                return True, 0.85
            if val_int >= 10_000_000 and val_int % 10_000_000 == 0:
                cr_str = f"{val_int // 10_000_000} cr"
                if cr_str in clean_snip:
                    return True, 0.85
            if val_int >= 100_000 and val_int % 100_000 == 0:
                lakh_str = f"{val_int // 100_000} lakh"
                if lakh_str in clean_snip:
                    return True, 0.85

        # 3. Check raw digit tokens
        val_digits = re.findall(r"\d+", val_str)
        snip_digits = re.findall(r"\d+", clean_snip)
        if val_digits and any(vd in snip_digits for vd in val_digits):
            return True, 0.75

        # Value not found in cited snippet: strictly downgrade to <= 0.30
        return False, 0.25

