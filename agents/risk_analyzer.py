from .llm_client import chat, chat_json
from .risk_rules import get_rules_for
from .sac_chunker import augment_with_summary
from .knowledge_base import build_knowledge_store

_SUMMARY_SYSTEM = """너는 해외 건설 계약서 전체를 한 문단(300자 이내)으로 요약하는 전문가다.
계약 유형(EPC/FIDIC 등), 발주자/시공사, 계약금액 규모, 공사 개요를 포함하여 요약하라."""

_knowledge_store = None


def _get_knowledge_store():
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = build_knowledge_store()
    return _knowledge_store


def summarize_document(clause_texts: list[str]) -> str:
    joined = "\n\n".join(clause_texts)
    return chat(_SUMMARY_SYSTEM, joined, temperature=0.2)


_RISK_SYSTEM = """너는 해외 건설·인프라 계약 리스크를 분석하는 법률 AI다.
아래 정보를 바탕으로 이 조항의 리스크를 평가하라.

[문서 전체 요약 (SAC: Summary-Augmented Context)]
{doc_summary}

[점검 규칙]
{rules}

[RAG 검색 결과: 관련 국제 실무 기준]
{retrieved_context}

위험도는 1(낮음)~5(매우 높음)점으로 산정하고, 근거를 조항 원문에서 직접 인용하라.
RAG 검색 결과에서 관련 기준을 인용할 경우 해당 doc_id를 references에 포함하라.
반드시 아래 JSON 스키마로만 응답하라:
{{
  "risk_score": 1,
  "risk_reason": "위험도 산정 근거",
  "evidence_quote": "원문에서 인용한 근거 문구",
  "recommendation": "수정 권고사항",
  "references": ["KB-XXX-001"],
  "requires_lawyer_review": false
}}
risk_score가 4 이상이면 requires_lawyer_review를 반드시 true로 설정하라.
"""


def analyze_clause(clause_type: str, translated_text: str, doc_summary: str) -> dict:
    rules = get_rules_for(clause_type)
    rules_text = "\n".join(f"- {r}" for r in rules) if rules else "- (해당 유형 전용 규칙 없음, 일반 법률 리스크 관점에서 검토)"

    sac_query = augment_with_summary(clause_type, translated_text, doc_summary)
    retrieved = _get_knowledge_store().query(sac_query, top_k=3)
    retrieved_context = "\n".join(
        f"- [{r['doc_id']}] (유사도 {r['score']:.2f}) {r['text']}" for r in retrieved
    ) or "- (관련 근거 없음)"

    system = _RISK_SYSTEM.format(doc_summary=doc_summary, rules=rules_text, retrieved_context=retrieved_context)
    result = chat_json(system, translated_text, temperature=0.2)
    result["risk_score"] = max(1, min(5, int(result.get("risk_score", 1))))
    if result["risk_score"] >= 4:
        result["requires_lawyer_review"] = True
    result["retrieval"] = [{"doc_id": r["doc_id"], "score": r["score"]} for r in retrieved]
    return result
