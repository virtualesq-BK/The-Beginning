import re

from .llm_client import chat_json

CLAUSE_TYPES = [
    "지체상금", "면책", "중재", "하자담보", "변경명령(Change Order)", "공사변경",
    "손해배상", "불가항력", "계약해지", "지급조건", "이행보증",
    "준거법", "분쟁해결", "보험", "지식재산권", "기타",
]

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


def parse_contract(raw_text: str) -> dict:
    parsed = chat_json(_SYSTEM, raw_text, temperature=0.0)
    parsed["clauses"] = normalize_clauses(parsed.get("clauses", []))
    return parsed
