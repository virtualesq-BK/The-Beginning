import math
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from docx import Document

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", ".doc"}
MAX_PAGES = 5
# PDF가 아닌 형식은 페이지 메타데이터가 없어 글자 수로 추정 (약 A4 1페이지)
CHARS_PER_PAGE = 3000


def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".txt":
        text = file_bytes.decode("utf-8", errors="replace")
        _assert_page_limit(_estimate_pages_from_text(text))
        return text
    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    if ext == ".docx":
        return _extract_docx(file_bytes)
    if ext == ".doc":
        return _extract_doc(file_bytes)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")


def _assert_page_limit(page_count: int) -> None:
    if page_count > MAX_PAGES:
        raise ValueError(
            f"파일은 최대 {MAX_PAGES}페이지까지 업로드할 수 있습니다. (현재 {page_count}페이지)"
        )


def _estimate_pages_from_text(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, math.ceil(len(stripped) / CHARS_PER_PAGE))


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    page_count = len(reader.pages)
    _assert_page_limit(page_count)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError("PDF에서 텍스트를 추출하지 못했습니다. 스캔 이미지 기반 PDF는 현재 지원하지 않습니다.")
    return text


def _extract_docx(file_bytes: bytes) -> str:
    doc = Document(BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs).strip()
    if not text:
        raise ValueError("DOCX 파일에서 텍스트를 추출하지 못했습니다.")
    _assert_page_limit(_estimate_pages_from_text(text))
    return text


def _extract_doc(file_bytes: bytes) -> str:
    """구형 .doc는 python-docx로 읽을 수 없어, 로컬 MS Word를 자동화해 텍스트를 추출한다.
    Windows + MS Word가 설치된 환경에서만 동작한다 (Phase 2 Linux 배포 시 별도 변환 서비스 필요)."""
    if sys.platform != "win32":
        raise ValueError(".doc 변환은 현재 Windows + MS Word 환경에서만 지원됩니다. .docx 또는 .pdf로 변환 후 업로드해주세요.")

    try:
        import win32com.client as win32
    except ImportError:
        raise ValueError(".doc 변환에 필요한 pywin32가 설치되어 있지 않습니다.")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        word = win32.gencache.EnsureDispatch("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(tmp_path, ReadOnly=True)
            try:
                # wdStatisticPages = 2
                page_count = int(doc.ComputeStatistics(2))
                _assert_page_limit(page_count)
                text = doc.Content.Text
            finally:
                doc.Close(False)
        finally:
            word.Quit()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f".doc 파일을 변환하지 못했습니다 (MS Word 설치 여부를 확인해주세요): {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    text = text.strip()
    if not text:
        raise ValueError(".doc 파일에서 텍스트를 추출하지 못했습니다.")
    return text
