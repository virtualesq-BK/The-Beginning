from .llm_client import chat, chat_json
from .risk_rules import get_rules_for
from .sac_chunker import augment_with_summary
from .knowledge_base import hybrid_retrieve

_SUMMARY_SYSTEM_KO = """너는 해외 건설 계약서 전체를 한 문단(300자 이내)으로 요약하는 전문가다.
계약 유형(EPC/FIDIC 등), 발주자/시공사, 계약금액 규모, 공사 개요를 포함하여 요약하라."""

_SUMMARY_SYSTEM_EN = """You are an expert who summarizes an entire international construction contract in a single paragraph (under 300 characters).
Include the contract type (EPC/FIDIC, etc.), employer/contractor, contract value scale, and project overview in the summary."""

_SUMMARY_SYSTEMS = {"ko": _SUMMARY_SYSTEM_KO, "en": _SUMMARY_SYSTEM_EN}


def summarize_document(clause_texts: list[str], language: str = "ko") -> str:
    joined = "\n\n".join(clause_texts)
    system = _SUMMARY_SYSTEMS.get(language, _SUMMARY_SYSTEM_KO)
    return chat(system, joined, temperature=0.2)


_RISK_SYSTEM_KO = """너는 해외 건설·인프라 계약 리스크를 분석하는 법률 AI다.
답은 단순 결론이 아니라 반드시 "Evidence -> Reasoning -> Conclusion" 순서로
감사 가능한(auditable) 근거를 남겨야 한다. risk_score만 산정하고 끝내지 마라.

[문서 전체 요약 (SAC: Summary-Augmented Context)]
{doc_summary}

[적용 가능한 Rule (Legal Decision Model 노드)]
{rules}

[RAG 검색 결과: 관련 국제 실무 기준]
{retrieved_context}

[이 계약서에서 연결된 조항 (Clause Graph: 상위조항/상호참조/의미유사)]
{related_clauses}

위험도는 1(낮음)~5(매우 높음)점으로 산정한다.
위 [적용 가능한 Rule]에 rule_id가 있다면 실제로 이 조항에 해당하는 rule_id만
골라 rules_applied에 넣어라 (해당 없으면 빈 배열).
연결된 조항의 내용이 이 조항의 위험을 키우거나 줄이면 risk_reason에 해당 조항 번호를 밝혀라.
반드시 아래 JSON 스키마로만 응답하라:
{{
  "risk_score": 1,
  "rules_applied": ["FIDIC-DELAY-LD", "FIDIC-DELAY-NOTICE"],
  "evidence_quote": "원문에서 인용한 근거 문구 (Evidence)",
  "risk_reason": "위 evidence와 rule을 근거로 왜 위험한지에 대한 추론 과정 (Reasoning)",
  "business_impact": "실무상 어떤 결과로 이어지는지 (예: 지연 발생 시 LD+추가 손해배상 중복 가능)",
  "recommendation": "수정 권고사항 (Conclusion)",
  "negotiation_point": "협상 시 요구할 구체적 지점 (예: Notice 기간 7 -> 14일)",
  "alternative_text": "대체 문구 초안",
  "references": ["KB-XXX-001"],
  "requires_lawyer_review": false
}}
risk_score가 4 이상이면 requires_lawyer_review를 반드시 true로 설정하라.
"""

_RISK_SYSTEM_EN = """You are a legal AI that analyzes risk in international construction and infrastructure contracts.
Your answer must leave an auditable "Evidence -> Reasoning -> Conclusion" trail, not just a bare score.

[Overall document summary (SAC: Summary-Augmented Context)]
{doc_summary}

[Applicable Rules (Legal Decision Model nodes)]
{rules}

[RAG search results: related international practice standards]
{retrieved_context}

[Linked clauses in this contract (Clause Graph: parent / cross-reference / semantic)]
{related_clauses}

Rate the risk on a scale of 1 (low) to 5 (very high).
If the [Applicable Rules] above include rule_id values, select only the ones that
actually apply to this clause into rules_applied (empty array if none apply).
If a linked clause increases or reduces this clause's risk, name that clause number in risk_reason.
Respond ONLY with the following JSON schema:
{{
  "risk_score": 1,
  "rules_applied": ["FIDIC-DELAY-LD", "FIDIC-DELAY-NOTICE"],
  "evidence_quote": "quoted supporting text from the original clause (Evidence)",
  "risk_reason": "reasoning connecting the evidence and rule to the risk conclusion (Reasoning)",
  "business_impact": "practical consequence (e.g. LD plus duplicate damages may both apply on delay)",
  "recommendation": "recommended revision (Conclusion)",
  "negotiation_point": "concrete negotiation ask (e.g. Notice period 7 -> 14 days)",
  "alternative_text": "draft alternative clause text",
  "references": ["KB-XXX-001"],
  "requires_lawyer_review": false
}}
If risk_score is 4 or higher, requires_lawyer_review must be set to true.
"""

_RISK_SYSTEMS = {"ko": _RISK_SYSTEM_KO, "en": _RISK_SYSTEM_EN}
_NO_RULES_TEXT = {
    "ko": "- (해당 유형 전용 규칙 없음, 일반 법률 리스크 관점에서 검토)",
    "en": "- (No rules specific to this clause type; review from a general legal risk perspective)",
}
_NO_EVIDENCE_TEXT = {"ko": "- (관련 근거 없음)", "en": "- (No related evidence found)"}
_NO_RELATED_TEXT = {"ko": "- (연결된 조항 없음)", "en": "- (No linked clauses)"}
_RELATED_TEXT_LIMIT = 600


def _format_related_clauses(related_clauses: list[dict] | None, language: str) -> str:
    if not related_clauses:
        return _NO_RELATED_TEXT.get(language, _NO_RELATED_TEXT["ko"])
    lines = []
    for c in related_clauses:
        text = (c.get("translated_text") or c.get("original_text") or "")[:_RELATED_TEXT_LIMIT]
        lines.append(f"- [조항 {c.get('clause_number') or c.get('id')} | {c.get('clause_type', '')}] {c.get('title', '')}: {text}")
    return "\n".join(lines)


def _format_rule_matches(clause_type: str, rule_matches: list, language: str) -> str:
    """Rule Retrieval(Knowledge Graph) 결과를 구조화된 블록으로, 없으면 flat 질문 리스트로 폴백."""
    if rule_matches:
        blocks = []
        for n in rule_matches:
            blocks.append(
                f"- rule_id={n.node_id} | {n.legal_concept}\n"
                f"  위험조건: {n.risk_condition}\n"
                f"  예외조건: {n.exception_condition}\n"
                f"  계약상 효과: {n.contractual_effect}\n"
                f"  실무상 위험: {n.practical_risk} (심각도: {n.risk_severity})\n"
                f"  협상목표: {n.negotiation_goal} | 최소수용조건: {n.minimum_acceptable}\n"
                f"  대체문구: {n.fallback_text}"
            )
        return "\n".join(blocks)
    rules = get_rules_for(clause_type)
    if rules:
        return "\n".join(f"- {r}" for r in rules)
    return _NO_RULES_TEXT.get(language, _NO_RULES_TEXT["ko"])


def analyze_clause(
    clause_type: str,
    translated_text: str,
    doc_summary: str,
    language: str = "ko",
    related_clauses: list[dict] | None = None,
    related_clause_types: list[str] | None = None,
) -> dict:
    """related_clauses: Clause Graph에서 연결된 같은 계약서의 조항들 (프롬프트 근거로 제공).
    related_clause_types: 명시적으로 참조하는 조항의 유형 (규칙 후보 확장용)."""
    # Hybrid Retrieval: Semantic(Vector) + Rule(Knowledge Graph)을 명시적으로 분리 조회.
    # LLM은 이 둘을 각각 다른 성격의 근거로 취급하며, rules_applied는 rule_matches의
    # rule_id 중에서만 선택되도록 강제한다 (결정론적 규칙과 벡터 유사도 참고자료를 혼동하지 않게).
    sac_query = augment_with_summary(clause_type, translated_text, doc_summary)
    retrieval = hybrid_retrieve(
        clause_type,
        sac_query,
        top_k=3,
        clause_text=translated_text,
        related_clause_types=related_clause_types,
    )
    retrieved = retrieval["semantic_matches"]
    rules_text = _format_rule_matches(clause_type, retrieval["rule_matches"], language)

    retrieved_context = "\n".join(
        f"- [{r['doc_id']}] (유사도 {r['score']:.2f}) {r['text']}" for r in retrieved
    ) or _NO_EVIDENCE_TEXT.get(language, _NO_EVIDENCE_TEXT["ko"])

    system_template = _RISK_SYSTEMS.get(language, _RISK_SYSTEM_KO)
    system = system_template.format(
        doc_summary=doc_summary,
        rules=rules_text,
        retrieved_context=retrieved_context,
        related_clauses=_format_related_clauses(related_clauses, language),
    )
    result = chat_json(system, translated_text, temperature=0.2)
    result["risk_score"] = max(1, min(5, int(result.get("risk_score", 1))))
    if result["risk_score"] >= 4:
        result["requires_lawyer_review"] = True
    offered_rule_ids = {n.node_id for n in retrieval["rule_matches"]}
    result["rules_applied"] = [rid for rid in result.get("rules_applied", []) if rid in offered_rule_ids]
    result.setdefault("business_impact", "")
    result.setdefault("negotiation_point", "")
    result.setdefault("alternative_text", "")
    result["retrieval"] = [{"doc_id": r["doc_id"], "score": r["score"]} for r in retrieved]
    return result
