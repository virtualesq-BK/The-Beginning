"""해외 건설 계약 리스크 판단 근거 지식베이스 (MVP 시드 세트).

공개 자료(FIDIC 표준계약 해설, 업계 관행)를 바탕으로 직접 작성한 요약이며,
전 직장 기밀 데이터는 포함하지 않는다. 정식 버전에서는 판례·규정 원문을
doc_id 단위로 확장하여 Pinecone에 적재한다.
"""

from .vector_store import LocalVectorStore
from .standard_contract_catalog import build_standard_contract_seed_docs
from . import risk_ontology

SEED_DOCS = [
    {
        "doc_id": "KB-LD-001",
        "clause_type": "지체상금",
        "text": "FIDIC Red/Yellow Book 실무상 지체상금(Delay Damages)은 통상 계약금액의 5~10% 수준에서 상한(cap)을 두며, 상한 초과 시 발주자는 해지 등 별도 구제수단으로 이행한다. 상한이 없는 지체상금 조항은 시공사에 비정상적으로 큰 리스크를 전가한다.",
    },
    {
        "doc_id": "KB-LD-002",
        "clause_type": "지체상금",
        "text": "지체상금은 통상 '유일하고 배타적인 구제수단(sole and exclusive remedy)'으로 규정되어, 발주자가 지체상금 외에 추가로 일반 손해배상을 중복 청구하지 못하도록 하는 것이 국제 관행이다.",
    },
    {
        "doc_id": "KB-IND-001",
        "clause_type": "면책",
        "text": "발주자 면책(Employer's indemnity) 조항은 통상 발주자 자신의 고의 또는 중과실로 인한 손해까지 면책하지 않는다. 고의·중과실을 포함한 포괄적 면책 조항은 다수 법域에서 공서양속 위반으로 무효화될 위험이 있다.",
    },
    {
        "doc_id": "KB-ARB-001",
        "clause_type": "중재",
        "text": "국제건설계약에서는 중립성을 위해 ICC, SIAC, HKIAC 등 국제 중재기관을 지정하고, 중재지를 계약 당사자 어느 일방의 본국이 아닌 제3국(예: 싱가포르, 런던, 파리)으로 정하는 것이 표준 관행이다.",
    },
    {
        "doc_id": "KB-ARB-002",
        "clause_type": "중재",
        "text": "중재 언어와 준거법이 명시되지 않은 조항은 분쟁 발생 시 관할·해석 다툼(procedural dispute)을 유발하여 분쟁 해결 비용과 기간을 크게 늘린다.",
    },
    {
        "doc_id": "KB-DLP-001",
        "clause_type": "하자담보",
        "text": "FIDIC 표준 하자담보책임기간(Defects Notification Period)은 통상 12개월이며, 대형 플랜트/인프라 프로젝트에서도 24개월을 넘는 경우는 드물다. 36개월 이상의 DLP는 비정상적으로 길어 시공사의 장기 재무 리스크를 유발한다.",
    },
    {
        "doc_id": "KB-CO-001",
        "clause_type": "변경명령(Change Order)",
        "text": "FIDIC 체계에서 발주자의 일방적 변경지시(Variation)는 반드시 공기 연장(EOT) 및 계약금액 조정(Clause 13) 절차와 연계되어야 하며, 조정 없는 일방적 변경권은 시공사에 불공정하다.",
    },
    {
        "doc_id": "KB-FM-001",
        "clause_type": "불가항력",
        "text": "국제 표준 불가항력(Force Majeure) 조항은 자연재해, 전쟁, 정부조치 등을 포괄적으로 열거하고, 불가항력 발생 시 공기 연장뿐 아니라 합리적 범위의 비용 보전도 함께 인정하는 것이 일반적이다.",
    },
    {
        "doc_id": "KB-TERM-001",
        "clause_type": "계약해지",
        "text": "발주자의 임의해지(Termination for Convenience) 시 시공사는 통상 기시공 부분 대금, 이미 발주한 자재비, 일실이익의 일부(예: 미시공 부분의 5~15%)를 보상받는 것이 국제 관행이다.",
    },
]


def build_knowledge_store() -> LocalVectorStore:
    store = LocalVectorStore()
    docs = SEED_DOCS + build_standard_contract_seed_docs()
    texts = [f"[{d['clause_type']}] {d['text']}" for d in docs]
    metadatas = [{"doc_id": d["doc_id"], "clause_type": d["clause_type"], "text": d["text"]} for d in docs]
    store.add(texts, metadatas)
    return store


# ---------------------------------------------------------------------------
# Hybrid Retrieval (Vector DB + Rule Engine)
#
# 순수 Vector RAG는 "비슷한 문장을 찾아서 보여주는" 수준에 머문다. 이 제품은
# 두 개의 독립된 검색 경로를 명시적으로 분리해서 LLM에 넘긴다.
#
#   1) Semantic Retrieval  : LocalVectorStore -> SEED_DOCS/표준계약서 -
#                            "관련 있어 보이는 실무 기준 문서" 검색
#   2) Rule Retrieval      : risk_ontology    -> Legal Decision Model -
#                            "이 조항유형에 실제로 적용되는 확정 규칙" 조회
#
# risk_analyzer.analyze_clause()는 이미 이 두 경로를 각각 호출하고 있었지만
# (retrieved = knowledge_store.query(...), rules = get_nodes_for(...)),
# 이 함수는 그 관계를 하나의 진입점으로 명시해 "Vector DB + Knowledge Graph
# + Rule Engine + LLM" 하이브리드 아키텍처임을 코드 구조 자체로 드러낸다.
# ---------------------------------------------------------------------------


_shared_store: LocalVectorStore | None = None


def _get_shared_store() -> LocalVectorStore:
    global _shared_store
    if _shared_store is None:
        _shared_store = build_knowledge_store()
    return _shared_store


def hybrid_retrieve(
    clause_type: str,
    semantic_query: str,
    top_k: int = 3,
    clause_text: str = "",
    related_clause_types: list[str] | None = None,
) -> dict:
    """Semantic Retrieval(Vector)과 Rule Retrieval(Knowledge Graph)을
    각각 수행해 두 결과를 분리된 채로 반환한다.

    LLM에게 "모든 판단을 맡기지 않는다"는 원칙에 따라, rule_matches는
    LLM 추론 없이 결정론적으로(deterministic) 조회되며 semantic_matches는
    벡터 유사도 기반 참고자료로만 취급된다. 호출부(risk_analyzer)는 이
    둘을 프롬프트에서 별도 섹션으로 분리해 LLM이 혼동하지 않도록 한다.
    임베딩 재계산을 피하기 위해 벡터스토어는 프로세스당 한 번만 빌드된다.

    rule_matches는 (1) 조항 자신의 유형, (2) 원문 키워드 트리거, (3) Clause
    Graph에서 명시적으로 연결된 조항의 유형 순으로 합쳐진다. 조항유형 분류가
    틀려도 Notice/Time Bar처럼 다른 클러스터에 속한 규칙을 놓치지 않기 위함이다.
    """
    store = _get_shared_store()
    semantic_matches = store.query(semantic_query, top_k=top_k)
    candidates = risk_ontology.get_nodes_for_clause_type(clause_type)
    candidates += risk_ontology.get_nodes_by_keywords(clause_text)
    for related_type in related_clause_types or []:
        candidates += risk_ontology.get_nodes_for_clause_type(related_type)
    rule_matches = list({n.node_id: n for n in candidates}.values())
    return {
        "semantic_matches": semantic_matches,
        "rule_matches": rule_matches,
    }
