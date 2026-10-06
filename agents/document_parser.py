import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from .llm_client import chat_json

CLAUSE_TYPES = [
    "지체상금", "면책", "중재", "하자담보", "변경명령(Change Order)", "공사변경",
    "손해배상", "불가항력", "계약해지", "지급조건", "이행보증",
    "준거법", "분쟁해결", "보험", "지식재산권", "기타",
]

# 게이트웨이 단일 요청 타임아웃 방지: 청크당 최대 글자 수
_PARSE_CHUNK_SIZE = 6000
_PARSE_WORKERS = 4

_SYSTEM = f"""너는 해외 건설·인프라 계약서를 조항 단위로 분해하는 파서다.
입력된 계약서 텍스트를 조항 단위로 나누고, 각 조항을 다음 유형 중 하나로 분류하라:
{", ".join(CLAUSE_TYPES)}

계약서의 계층 구조와 조항 간 참조를 보존해야 한다.
- clause_number: 계약서에 표기된 조항 번호 그대로 (예: "8", "8.7", "20.1"). 없으면 빈 문자열.
- parent_number: 상위 조항 번호 (예: "8.7"의 상위는 "8"). 최상위면 빈 문자열.
- cross_references: 본문이 참조하는 다른 조항 번호 목록 (예: "subject to Sub-Clause 20.1" -> ["20.1"]).

반드시 아래 JSON 스키마로만 응답하라:
{{
  "clauses": [
    {{"id": 1, "clause_number": "8.7", "parent_number": "8", "clause_type": "지체상금",
      "title": "조항 제목", "original_text": "원문 전체", "cross_references": ["20.1"]}}
  ]
}}
"""

_NUMBER = r"\d+(?:\.\d+)*"
_REF_PATTERNS = [
    re.compile(rf"\b(?:Sub-?Clauses?|Clauses?|Articles?|Sections?)\s+({_NUMBER})", re.IGNORECASE),
    re.compile(rf"제\s*(\d+)\s*조(?:\s*제\s*(\d+)\s*항)?"),
]
_LEADING_NUMBER = re.compile(rf"^\s*(?:Sub-?Clause|Clause|Article|Section)?\s*({_NUMBER})(?=[\s.):]|$)", re.IGNORECASE)
_LEADING_KO_NUMBER = re.compile(r"^\s*제\s*(\d+)\s*조")


def extract_cross_references(text: str) -> list[str]:
    """원문에서 "Sub-Clause 20.1", "Clause 8", "제5조 제2항" 같은 조항 참조를 결정론적으로 추출한다."""
    refs: list[str] = []
    for pattern in _REF_PATTERNS:
        for match in pattern.finditer(text or ""):
            groups = [g for g in match.groups() if g]
            ref = ".".join(groups) if pattern.pattern.startswith("제") else groups[0]
            ref = ref.rstrip(".")
            if ref not in refs:
                refs.append(ref)
    return refs


def _infer_clause_number(clause: dict) -> str:
    for source in (clause.get("title", ""), clause.get("original_text", "")):
        match = _LEADING_NUMBER.match(source or "") or _LEADING_KO_NUMBER.match(source or "")
        if match:
            return match.group(1).rstrip(".")
    return ""


def _parent_of(number: str) -> str:
    return number.rsplit(".", 1)[0] if "." in number else ""


def normalize_clauses(clauses: list[dict]) -> list[dict]:
    """LLM 파서 결과를 정규화한다: id 보장, 조항번호/상위번호 보완, 상호참조를 정규식 결과와 병합.

    자기 자신을 가리키는 참조와 조항 제목의 번호(예: "8.7 Delay Damages")는 참조에서 제외한다.
    """
    normalized: list[dict] = []
    for index, clause in enumerate(clauses, start=1):
        c = dict(clause)
        c["id"] = c.get("id") or index
        number = str(c.get("clause_number") or "").strip().rstrip(".") or _infer_clause_number(c)
        c["clause_number"] = number
        c["parent_number"] = str(c.get("parent_number") or "").strip().rstrip(".") or _parent_of(number)

        llm_refs = [str(r).strip().rstrip(".") for r in (c.get("cross_references") or []) if str(r).strip()]
        body = c.get("original_text", "")
        if number:
            # 본문 첫머리의 자기 번호 표기("Sub-Clause 8.7 Delay Damages ...")가 참조로 잡히지 않게 제거
            body = re.sub(rf"^\s*(?:Sub-?Clause|Clause|Article|Section)?\s*{re.escape(number)}\b", "", body, flags=re.IGNORECASE)
        regex_refs = extract_cross_references(body)
        merged: list[str] = []
        for ref in llm_refs + regex_refs:
            if ref and ref != number and ref not in merged:
                merged.append(ref)
        c["cross_references"] = merged
        normalized.append(c)
    return normalized


def _split_into_chunks(text: str, chunk_size: int) -> list[str]:
    """조항 경계를 최대한 보존하며 텍스트를 chunk_size 이하로 분할한다."""
    if len(text) <= chunk_size:
        return [text]

    # 조항 구분 패턴(빈 줄 + 번호로 시작하는 줄)에서 분할 시도
    _BOUNDARY = re.compile(
        r"\n(?=\s*(?:Sub-?Clause|Clause|Article|Section|제\s*\d+\s*조)\s*[\d.])",
        re.IGNORECASE,
    )
    parts = _BOUNDARY.split(text)

    chunks: list[str] = []
    current = ""
    for part in parts:
        if len(current) + len(part) > chunk_size and current:
            chunks.append(current.strip())
            current = part
        else:
            current = current + ("\n" if current else "") + part
    if current.strip():
        chunks.append(current.strip())

    # 패턴 분할이 안 된 경우(단일 덩어리) → 강제 분할
    if len(chunks) == 1 and len(chunks[0]) > chunk_size:
        chunks = [text[i: i + chunk_size] for i in range(0, len(text), chunk_size)]

    return chunks


def _parse_chunk(chunk: str) -> list[dict]:
    try:
        result = chat_json(_SYSTEM, chunk, temperature=0.0)
        return result.get("clauses", [])
    except Exception:
        return []


def parse_contract(raw_text: str) -> dict:
    chunks = _split_into_chunks(raw_text, _PARSE_CHUNK_SIZE)

    if len(chunks) == 1:
        parsed = chat_json(_SYSTEM, chunks[0], temperature=0.0)
        all_clauses = parsed.get("clauses", [])
    else:
        all_clauses = []
        with ThreadPoolExecutor(max_workers=_PARSE_WORKERS) as executor:
            futures = [executor.submit(_parse_chunk, chunk) for chunk in chunks]
            for future in as_completed(futures):
                all_clauses.extend(future.result())

    # id 재부여 (청크별 중복 방지)
    for i, clause in enumerate(all_clauses, start=1):
        clause["id"] = i

    return {"clauses": normalize_clauses(all_clauses)}
