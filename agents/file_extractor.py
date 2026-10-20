import math
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from docx import Document

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", ".doc"}
MAX_PAGES = 20
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
    """구형 .doc 텍스트 추출 — 두 단계 폴백.

    1단계: python-docx로 열기 시도 (일부 .doc는 실제로 OOXML 포맷).
    2단계: olefile로 OLE2 컨테이너를 열어 WordDocument 스트림에서
           UTF-16LE 텍스트를 추출 (Word 97-2003 바이너리 포맷 대응).
    Windows 로컬 환경에서는 추가로 MS Word COM 자동화를 시도한다.
    """
    # ── 1단계: python-docx (OOXML .doc) ──────────────────────────────────
    try:
        text = _extract_docx(file_bytes)
        if text:
            return text
    except Exception:
        pass

    # ── 2단계: olefile OLE2 스트림 추출 (Word 97-2003 바이너리) ──────────
    try:
        import olefile
        import re as _re

        ole = olefile.OleFileIO(BytesIO(file_bytes))
        if not ole.exists("WordDocument"):
            raise ValueError(".doc 파일에서 WordDocument 스트림을 찾을 수 없습니다.")

        raw = ole.openstream("WordDocument").read()
        # 텍스트는 UTF-16LE로 저장되어 있음
        text = raw.decode("utf-16-le", errors="ignore")
        # 제어 문자 제거 (탭·줄바꿈 제외)
        text = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
        text = _re.sub(r" {2,}", " ", text).strip()
        if text:
            _assert_page_limit(_estimate_pages_from_text(text))
            return text
    except ValueError:
        raise
    except Exception as e:
        pass

    # ── 3단계: Windows + MS Word COM (로컬 개발 환경 전용) ───────────────
    if sys.platform == "win32":
        try:
            import win32com.client as win32

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
                raise ValueError(f".doc 파일을 변환하지 못했습니다: {e}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            text = text.strip()
            if text:
                return text
        except ValueError:
            raise
        except Exception:
            pass

    raise ValueError(
        ".doc 파일에서 텍스트를 추출하지 못했습니다. "
        ".docx 또는 .pdf로 변환 후 다시 업로드해주세요."
    )
