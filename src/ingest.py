import hashlib
import os
from typing import Optional
from pydantic import BaseModel
import pypdf


class IngestResult(BaseModel):
    tender_id: str
    file_path: str
    file_name: str
    file_size_bytes: int
    sha256_hash: str
    page_count: int
    is_valid: bool
    rejection_reason: Optional[str] = None


class IngestWorker:
    def __init__(self, max_size_mb: int = 25, max_pages: int = 400):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_pages = max_pages

    def process(self, file_path: str, tender_id: Optional[str] = None) -> IngestResult:
        if not os.path.exists(file_path):
            return IngestResult(
                tender_id=tender_id or "unknown",
                file_path=file_path,
                file_name=os.path.basename(file_path),
                file_size_bytes=0,
                sha256_hash="",
                page_count=0,
                is_valid=False,
                rejection_reason=f"File not found: {file_path}",
            )

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        # 1. Size check
        if file_size > self.max_size_bytes:
            return IngestResult(
                tender_id=tender_id or file_name,
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                sha256_hash="",
                page_count=0,
                is_valid=False,
                rejection_reason=f"File exceeds maximum size limit of {self.max_size_bytes // (1024 * 1024)} MB",
            )

        # 2. Compute SHA-256
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        sha256 = hasher.hexdigest()

        # 3. PDF verification & Page count
        try:
            reader = pypdf.PdfReader(file_path)
            if reader.is_encrypted:
                return IngestResult(
                    tender_id=tender_id or sha256[:12],
                    file_path=file_path,
                    file_name=file_name,
                    file_size_bytes=file_size,
                    sha256_hash=sha256,
                    page_count=0,
                    is_valid=False,
                    rejection_reason="PDF is password-encrypted. Unprotected document required.",
                )

            page_count = len(reader.pages)
            if page_count > self.max_pages:
                return IngestResult(
                    tender_id=tender_id or sha256[:12],
                    file_path=file_path,
                    file_name=file_name,
                    file_size_bytes=file_size,
                    sha256_hash=sha256,
                    page_count=page_count,
                    is_valid=False,
                    rejection_reason=f"PDF page count ({page_count}) exceeds limit of {self.max_pages} pages",
                )

            return IngestResult(
                tender_id=tender_id or f"TND-{sha256[:8].upper()}",
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                sha256_hash=sha256,
                page_count=page_count,
                is_valid=True,
            )

        except Exception as e:
            return IngestResult(
                tender_id=tender_id or "invalid",
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                sha256_hash=sha256,
                page_count=0,
                is_valid=False,
                rejection_reason=f"Corrupt or non-PDF file: {str(e)}",
            )
