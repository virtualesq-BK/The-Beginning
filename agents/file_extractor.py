from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from docx import Document

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".txt":
        return file_bytes.decode("utf-8", errors="replace")
    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    if ext == ".docx":
        return _extract_docx(file_bytes)
    if ext == ".doc":
        raise ValueError("구형 .doc 형식은 지원하지 않습니다. .docx 또는 .pdf로 변환 후 업로드해주세요.")
    raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
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
    return text
