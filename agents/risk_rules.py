"""해외 건설 계약 리스크 탐지 규칙.

FIDIC Delay 클러스터(지체상금 등 지체 관련 조항)는 risk_ontology.py의
Legal Decision Model(계층형 Knowledge Graph)에서 파생된다. 나머지
조항유형은 아직 온톨로지로 이전되지 않은 MVP 시드 세트이며, 정식
버전에서는 risk_ontology.py 구조로 전체를 이전할 예정이다.

get_rules_for()는 하위호환을 위해 계속 flat list[str]을 반환하지만,
risk_analyzer.py는 가능한 경우 get_nodes_for() 를 통해 온톨로지
노드(RiskNode) 전체 - 위험조건/예외조건/관련조항/협상목표/대체문구 등 -
를 직접 사용해 Evidence 기반 근거를 구성한다.
"""

from . import risk_ontology

# 조항유형별 질문은 이제 전부 risk_ontology.py의 Legal Decision Model에서
# 파생된다 (단일 소스 유지). 각 조항유형의 risk_condition을 flat list로
# 뽑아내며, 온톨로지 노드가 아직 없는 조항유형(건설계약/FIDIC 총괄)만
# 예전처럼 직접 정의한다.
_DELAY_RULES = [node.risk_condition for node in risk_ontology.get_cluster("Delay")]
_INDEMNITY_RULES = [node.risk_condition for node in risk_ontology.get_cluster("Indemnity")]
_FORCE_MAJEURE_RULES = [node.risk_condition for node in risk_ontology.get_cluster("Force Majeure")]
_TERMINATION_RULES = [node.risk_condition for node in risk_ontology.get_cluster("Termination")]


def _rules_from_node(node_id: str) -> list[str]:
    node = risk_ontology.get_node(node_id)
    return [node.risk_condition] if node else []


RISK_RULES = {
    "지체상금": _DELAY_RULES,
    "면책": _INDEMNITY_RULES,
    "중재": _rules_from_node("FIDIC-ARBITRATION"),
    "하자담보": _rules_from_node("FIDIC-DLP"),
    "변경명령(Change Order)": _rules_from_node("FIDIC-CHANGE-ORDER"),
    "불가항력": _FORCE_MAJEURE_RULES,
    "계약해지": _TERMINATION_RULES,
    "성능보증": _rules_from_node("FIDIC-PERFORMANCE-SECURITY"),
    "지급·인도": _rules_from_node("FIDIC-PAYMENT-ACCEPTANCE"),
    "보증·보험": _rules_from_node("FIDIC-GUARANTEE-INSURANCE"),
    "공사변경": _rules_from_node("FIDIC-VARIATION-SCOPE"),
    "건설계약": [
        "설계 책임과 시공 책임이 명확히 분리되어 있는가",
        "공기 연장(EOT), 지체상금(LD), 변경명령, 테스트/인수 절차가 일관되게 연결되는가",
        "책임한도와 면책 범위가 프로젝트 위험에 비해 과도하게 불균형한가",
    ],
    "FIDIC": [
        "FIDIC 패밀리 구분(Red/Yellow/Silver)이 계약서상 명확히 반영되는가",
        "변경지시, 공기연장, 지체상금, 하자보수 기간이 서로 상충하지 않는가",
        "DAB/중재 절차와 법적 구제수단이 실무적으로 실행 가능한가",
    ],
}


def get_rules_for(clause_type: str) -> list[str]:
    if clause_type in RISK_RULES:
        return RISK_RULES[clause_type]
    normalized = clause_type.strip().lower()
    for key, rules in RISK_RULES.items():
        if key.lower() == normalized:
            return rules
    fallback = RISK_RULES.get("건설계약", [])
    return fallback if fallback else []


def get_nodes_for(clause_type: str) -> list[risk_ontology.RiskNode]:
    """조항유형에 대응하는 온톨로지 노드(RiskNode) 전체를 반환한다.

    risk_analyzer.py에서 Evidence/Rule Applied/Negotiation Point 등을
    구성할 때 사용한다. 아직 온톨로지로 이전되지 않은 조항유형은 빈
    리스트를 반환하며, 이 경우 risk_analyzer.py는 get_rules_for()의
    flat 질문 리스트로 폴백한다.
    """
    return risk_ontology.get_nodes_for_clause_type(clause_type)
