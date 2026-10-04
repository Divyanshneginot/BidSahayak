import unicodedata
import re
from typing import Optional
from pydantic import BaseModel, Field
import pypdf


class PageText(BaseModel):
    page_number: int  # 1-indexed
    raw_text: str
    normalized_text: str
    char_count: int
    is_scanned_likely: bool


class ExtractionResult(BaseModel):
    tender_id: str
    total_pages: int
    pages: dict[int, PageText]
    full_text: str
    is_scanned_document: bool
    detected_sections: list[str] = Field(default_factory=list)


class TextWorker:
    def __init__(self, min_chars_per_page: int = 50, scan_ratio_threshold: float = 0.3):
        self.min_chars_per_page = min_chars_per_page
        self.scan_ratio_threshold = scan_ratio_threshold

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Applies Unicode NFKC normalization, strips zero-width chars,
        and normalizes Devanagari and Latin whitespace.
        """
        if not text:
            return ""
        # 1. NFKC normalization
        norm = unicodedata.normalize("NFKC", text)
        # 2. Remove non-printable / zero-width characters
        norm = re.sub(r"[\u200b-\u200f\ufeff]", "", norm)
        # 3. Collapse excessive whitespace but keep single newlines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in norm.splitlines()]
        return "\n".join(line for line in lines if line)

    def process(self, file_path: str, tender_id: str = "TND") -> ExtractionResult:
        reader = pypdf.PdfReader(file_path)
        total_pages = len(reader.pages)
        pages_dict: dict[int, PageText] = {}
        scanned_page_count = 0
        all_text_parts: list[str] = []

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            raw_text = page.extract_text() or ""
            norm_text = self.normalize_text(raw_text)
            char_count = len(norm_text)
            is_scanned = char_count < self.min_chars_per_page

            if is_scanned:
                scanned_page_count += 1

            pages_dict[page_num] = PageText(
                page_number=page_num,
                raw_text=raw_text,
                normalized_text=norm_text,
                char_count=char_count,
                is_scanned_likely=is_scanned,
            )
            all_text_parts.append(f"--- PAGE {page_num} ---\n{norm_text}")

        # Scan ratio check
        is_scanned_document = (
            (scanned_page_count / total_pages) >= self.scan_ratio_threshold
            if total_pages > 0
            else False
        )

        full_text = "\n\n".join(all_text_parts)

        # Detect canonical Indian tender sections
        sections = []
        section_patterns = [
            ("NIT", r"(?i)(notice\s+inviting\s+tender|निविदा\s+आमंत्रण\s+सूचना)"),
            ("TIS", r"(?i)(tender\s+information\s+summary|निविदा\s+सूचना\s+सारांश)"),
            ("ITB", r"(?i)(instructions\s+to\s+bidders|बोलीदाताओं\s+के\s+लिए\s+निर्देश)"),
            ("SCC", r"(?i)(special\s+conditions\s+of\s+contract|विशेष\s+शर्तें)"),
            ("GCC", r"(?i)(general\s+conditions\s+of\s+contract|सामान्य\s+शर्तें)"),
            ("ELIGIBILITY", r"(?i)(eligibility\s+criteria|qualifying\s+requirements|पात्रता\s+मानदंड)"),
            ("EMD_SECTION", r"(?i)(earnest\s+money\s+deposit|bid\s+security\s+declaration|बयाना\s+राशि)"),
            ("ANNEXURE", r"(?i)(annexure|appendix|प्रपत्र|परिशिष्ट)"),
        ]
        for name, pat in section_patterns:
            if re.search(pat, full_text):
                sections.append(name)

        return ExtractionResult(
            tender_id=tender_id,
            total_pages=total_pages,
            pages=pages_dict,
            full_text=full_text,
            is_scanned_document=is_scanned_document,
            detected_sections=sections,
        )
