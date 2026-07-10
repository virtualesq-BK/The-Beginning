from .llm_client import chat_json

CLAUSE_TYPES = [
    "지체상금", "면책", "중재", "하자담보", "변경명령(Change Order)",
    "손해배상", "불가항력", "계약해지", "지급조건", "이행보증",
    "준거법", "분쟁해결", "보험", "지식재산권", "기타",
]

_SYSTEM = f"""너는 해외 건설·인프라 계약서를 조항 단위로 분해하는 파서다.
입력된 계약서 텍스트를 조항 단위로 나누고, 각 조항을 다음 유형 중 하나로 분류하라:
{", ".join(CLAUSE_TYPES)}

반드시 아래 JSON 스키마로만 응답하라:
{{
  "clauses": [
    {{"id": 1, "clause_type": "지체상금", "title": "조항 제목", "original_text": "원문 전체"}}
  ]
}}
"""


def parse_contract(raw_text: str) -> dict:
    return chat_json(_SYSTEM, raw_text, temperature=0.0)
