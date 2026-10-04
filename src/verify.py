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

    @staticmethod
    def _indian_group(n: int) -> str:
        """1234567 -> '12,34,567' (Indian digit grouping)."""
        s = str(abs(int(n)))
        if len(s) <= 3:
            return s
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        return ",".join(parts + [tail])

    @classmethod
    def verify_value(cls, snippet: str, value: Any) -> VerificationResult:
        """Round-trip an extracted value against its own cited snippet (fix F2 / gate G2).

        Contract: (snippet, value) -> VerificationResult. This verifies the VALUE, not just
        that the quote exists. Callers may only LOWER confidence on failure, never raise it.
        """
        if value is None or not snippet:
            return VerificationResult(is_verified=False, match_ratio=0.0,
                                      reason="empty value or snippet - cannot round-trip")
        clean = cls._clean(str(snippet)).lower()

        candidates = []
        sval = str(value)
        candidates.append(sval.lower())
        if isinstance(value, (list, tuple, set)):
            items = [str(x) for x in value]
            if items and all(i.lower() in clean for i in items):
                return VerificationResult(is_verified=True, match_ratio=0.95,
                                          reason="all listed values found in cited snippet")
            candidates = [i.lower() for i in items]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            n = int(value)
            candidates += [f"{n:,}", str(n), cls._indian_group(n), f"{n:,}".replace(",", "")]
            if n % 100_000 == 0 and n < 10_000_000:
                candidates.append(f"{n // 100_000} lakh")
            if n % 10_000_000 == 0:
                candidates.append(f"{n // 10_000_000} crore")
        # date-aware: stored values are ISO, documents write DD-MM-YYYY / DD.MM.YYYY
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", sval)
        if m:
            y, mo, d = m.groups()
            candidates += [f"{d}-{mo}-{y}", f"{d}/{mo}/{y}", f"{d}.{mo}.{y}", f"{y}-{mo}-{d}"]
        for c in candidates:
            if c and len(c) > 2 and c in clean:
                return VerificationResult(is_verified=True, match_ratio=0.95,
                                          reason=f"value '{c}' round-trips against the cited snippet",
                                          verified_snippet=sval)
        return VerificationResult(is_verified=False, match_ratio=0.0,
                                  reason="value/snippet mismatch - operator verification required")

