"""인하우스 변호사가 없는 중소기업·스타트업을 위한 영문 표준계약서 초안 자동생성.

질문지 답변 + knowledge/standard-contract 근거 자료(RAG)를 바탕으로
영문 조항 초안과 조항별 한국어 해설을 함께 생성한다.
"""

from .llm_client import chat_json
from .contract_templates import get_template
from .knowledge_base import build_knowledge_store

DISCLAIMER = (
    "본 초안은 참고용 표준계약서 자료를 바탕으로 AI가 생성한 것으로, 법적 효력이 없습니다. "
    "실제 서명 전에는 반드시 변호사 검토를 받으시기 바랍니다."
)

_knowledge_store = None


def _get_knowledge_store():
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = build_knowledge_store()
    return _knowledge_store


def _format_answers(fields: list[dict], answers: dict) -> str:
    lines = []
    for field in fields:
        key = field["key"]
        value = (answers.get(key) or "").strip()
        if not value:
            continue
        lines.append(f"- {field['label']}: {value}")
    return "\n".join(lines) or "- (추가 정보 없음)"


_SYSTEM_TEMPLATE = """너는 인하우스 변호사가 없는 한국 중소기업·스타트업을 돕는 국제계약 초안 작성 AI다.
아래 계약 유형과 사용자가 입력한 거래 조건을 바탕으로 영문 계약서 초안을 작성하라.

[계약 유형]
{title} ({family})

[사용자 입력 조건]
{answers_text}

[참고 근거자료 (RAG: 표준계약서 실무 가이드)]
{retrieved_context}

작성 원칙:
1. 조항(clause)은 8~12개로 구성하고, 최소한 다음을 포함하라: Parties/Definitions, Scope of Agreement(계약 범위), Term & Termination, Payment/Fees(해당 시), Confidentiality, Intellectual Property(해당 시), Warranties, Indemnification, Limitation of Liability, Governing Law, Dispute Resolution, Miscellaneous(Notices, Entire Agreement, Assignment 등은 하나의 조항으로 묶어도 됨).
2. 각 조항의 영문 본문(body_en)은 실제 계약서에 바로 쓸 수 있는 수준의 격식 있는 영문 계약 문구로 작성하고, 사용자가 입력한 회사명·조건을 반영하라.
3. 각 조항마다 한국어 해설(commentary_kr)을 2~4문장으로 작성하되, (a) 이 조항이 왜 필요한지, (b) 한국 중소기업 입장에서 특히 점검해야 할 리스크, (c) 참고 근거자료에 있는 실무 기준을 반영하라.
4. 손해배상 상한, 인뎀니티 carve-out, 준거법/관할, 지재권 귀속 등 리스크가 큰 조항은 해설에서 반드시 리스크를 짚어라.
5. recitals(전문)는 영문 2~3문장으로 작성하라.
6. signature_block은 양 당사자 서명란을 영문으로 작성하라.

반드시 아래 JSON 스키마로만 응답하라 (다른 텍스트 없이 JSON만):
{{
  "title": "계약서 제목 (영문)",
  "recitals": "전문 영문 텍스트",
  "clauses": [
    {{"clause_no": 1, "heading": "Definitions", "body_en": "...", "commentary_kr": "..."}}
  ],
  "signature_block": "서명란 영문 텍스트"
}}
"""


def generate_contract(template_id: str, answers: dict) -> dict:
    template = get_template(template_id)
    if template is None:
        raise ValueError(f"알 수 없는 계약서 템플릿입니다: {template_id}")

    answers_text = _format_answers(template["fields"], answers)

    query = f"[{template['family']}] {template['title']} {answers_text}"
    retrieved = _get_knowledge_store().query(query, top_k=4)
    retrieved_context = "\n".join(
        f"- [{r['doc_id']}] {r['text']}" for r in retrieved
    ) or "- (관련 근거 없음)"

    system = _SYSTEM_TEMPLATE.format(
        title=template["title"],
        family=template["family"],
        answers_text=answers_text,
        retrieved_context=retrieved_context,
    )

    result = chat_json(system, "위 조건에 맞는 영문 계약서 초안을 생성하라.", temperature=0.3)

    clauses = result.get("clauses") or []
    for idx, clause in enumerate(clauses, start=1):
        clause.setdefault("clause_no", idx)

    return {
        "template_id": template_id,
        "template_title": template["title"],
        "title": result.get("title") or template["title"],
        "recitals": result.get("recitals", ""),
        "clauses": clauses,
        "signature_block": result.get("signature_block", ""),
        "references": [{"doc_id": r["doc_id"], "score": r["score"]} for r in retrieved],
        "disclaimer": DISCLAIMER,
    }
