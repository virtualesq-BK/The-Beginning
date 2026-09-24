"""Clause Graph — 업로드된 계약서 조항 간 관계 그래프.

risk_ontology.py가 "법률 개념"의 지식 그래프라면, 이 모듈은 "이 계약서의 실제
조항"을 노드로 하는 그래프다. 엣지 종류:

    hierarchy        8 -> 8.7 같은 상위/하위 조항 관계 (조항 번호에서 결정론적으로 도출)
    cross_reference  "subject to Sub-Clause 20.1" 같은 명시적 참조 (정규식 + 파서)
    sac_similarity   SAC 임베딩상 의미적으로 가까운 조항 (휴리스틱)
    type_dependency  조항유형 간 실무상 의존관계 (예: 변경지시 -> 지체)

조합 위험 판정에서는 hierarchy/cross_reference를 "명시적 연결",
sac_similarity를 "의미적 연결"로 취급한다. type_dependency는 조합 규칙
자체가 조항유형 의존관계로 정의되어 있어 판정 근거로 쓰면 순환논리가 되므로,
규칙 후보를 넓히는 용도로만 쓴다.
"""

from dataclasses import dataclass, field

from .risk_ontology import RISK_COMBINATIONS, canonical_clause_type

EXPLICIT_KINDS = frozenset({"hierarchy", "cross_reference"})
SEMANTIC_KINDS = frozenset({"sac_similarity"})

# 조항유형(온톨로지 표기) 간 실무상 의존관계. 방향은 "앞 조항의 결과가 뒤 조항에 영향".
TYPE_DEPENDENCIES: list[tuple[str, str]] = [
    ("변경명령(Change Order)", "지체(Delay)"),
    ("공사변경", "변경명령(Change Order)"),
    ("불가항력(Force Majeure)", "지체(Delay)"),
    ("불가항력(Force Majeure)", "계약해지(Termination)"),
    ("지체(Delay)", "계약해지(Termination)"),
    ("지체(Delay)", "책임제한(Liability Cap)"),
    ("면책(Indemnity)", "책임제한(Liability Cap)"),
    ("하자담보(DLP)", "성능보증"),
    ("지급·인도", "계약해지(Termination)"),
]


@dataclass
class ClauseEdge:
    source: int
    target: int
    kind: str
    evidence: str

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target, "kind": self.kind, "evidence": self.evidence}


@dataclass
class ClauseGraph:
    nodes: dict[int, dict] = field(default_factory=dict)
    edges: list[ClauseEdge] = field(default_factory=list)

    def add_edge(self, source: int, target: int, kind: str, evidence: str) -> None:
        if source == target or source not in self.nodes or target not in self.nodes:
            return
        for e in self.edges:
            if e.kind == kind and {e.source, e.target} == {source, target}:
                return
        self.edges.append(ClauseEdge(source, target, kind, evidence))

    def neighbors(self, clause_id: int, kinds: frozenset[str] | set[str] | None = None) -> list[int]:
        """kinds 종류의 엣지로 직접 연결된 조항 id (방향 무시, 추가된 순서 유지)."""
        result: list[int] = []
        for e in self.edges:
            if kinds is not None and e.kind not in kinds:
                continue
            other = e.target if e.source == clause_id else e.source if e.target == clause_id else None
            if other is not None and other not in result:
                result.append(other)
        return result

    def components(self, kinds: frozenset[str] | set[str]) -> list[set[int]]:
        parent = {cid: cid for cid in self.nodes}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for e in self.edges:
            if e.kind in kinds:
                parent[find(e.source)] = find(e.target)
        groups: dict[int, set[int]] = {}
        for cid in self.nodes:
            groups.setdefault(find(cid), set()).add(cid)
        return list(groups.values())

    def to_dict(self) -> dict:
        return {
            "nodes": list(self.nodes.values()),
            "edges": [e.to_dict() for e in self.edges],
        }


def _resolve_reference(ref: str, number_to_id: dict[str, int]) -> list[int]:
    """참조 번호를 조항 id로 해석: 정확히 일치 -> 가장 가까운 상위 조항 -> 하위 조항들."""
    if ref in number_to_id:
        return [number_to_id[ref]]
    parts = ref.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        ancestor = ".".join(parts[:cut])
        if ancestor in number_to_id:
            return [number_to_id[ancestor]]
    prefix = ref + "."
    return [cid for number, cid in number_to_id.items() if number.startswith(prefix)]


def build_clause_graph(
    clauses: list[dict],
    similar_pairs: list[tuple[int, int, float]] | None = None,
) -> ClauseGraph:
    graph = ClauseGraph()
    for c in clauses:
        graph.nodes[c["id"]] = {
            "id": c["id"],
            "clause_number": c.get("clause_number", ""),
            "clause_type": c.get("clause_type", ""),
            "title": c.get("title", ""),
        }
    number_to_id = {c["clause_number"]: c["id"] for c in clauses if c.get("clause_number")}

    for c in clauses:
        parent = c.get("parent_number")
        if parent:
            for pid in _resolve_reference(parent, number_to_id):
                graph.add_edge(pid, c["id"], "hierarchy", f"{parent} ⊃ {c.get('clause_number')}")
        for ref in c.get("cross_references", []):
            for target in _resolve_reference(ref, number_to_id):
                graph.add_edge(c["id"], target, "cross_reference", f"{c.get('clause_number') or c['id']} → {ref}")

    for a, b, score in similar_pairs or []:
        graph.add_edge(a, b, "sac_similarity", f"SAC cosine {score:.2f}")

    canonical = {c["id"]: canonical_clause_type(c.get("clause_type", "")) for c in clauses}
    for src_type, dst_type in TYPE_DEPENDENCIES:
        sources = [cid for cid, t in canonical.items() if t == src_type]
        targets = [cid for cid, t in canonical.items() if t == dst_type]
        for s in sources:
            for t in targets:
                graph.add_edge(s, t, "type_dependency", f"{src_type} → {dst_type}")
    return graph


def _component_covering(
    graph: ClauseGraph, kinds: frozenset[str], rule_to_clauses: dict[str, set[int]]
) -> set[int] | None:
    """모든 필수 rule을 가진 조항이 하나씩 포함된 연결 요소를 찾아, 그 안의 근거 조항 id를 반환."""
    for component in graph.components(kinds):
        hits = [component & clause_ids for clause_ids in rule_to_clauses.values()]
        if all(hits):
            return set().union(*hits)
    return None


def evaluate_cross_clause_risks_graph(clause_rules: dict[int, set[str]], graph: ClauseGraph) -> list[dict]:
    """조항별 rules_applied와 Clause Graph로 조합 위험을 판정한다.

    confidence:
      explicit       필수 rule이 한 조항 안에 모두 있거나, 계층/명시적 참조로 연결된 조항들에 있음
      semantic       SAC 의미 유사도까지 포함해야 연결됨
      co_occurrence  같은 계약서에 함께 있지만 조항 간 연결이 확인되지 않음 (전문가 확인 필요)
    clause_ids는 판정 근거가 된 조항 id로, 리포트에서 원문 조항으로 추적할 수 있다.
    """
    matches: list[dict] = []
    for combo in RISK_COMBINATIONS:
        rule_to_clauses = {
            rid: {cid for cid, rules in clause_rules.items() if rid in rules} for rid in combo.required_node_ids
        }
        if not all(rule_to_clauses.values()):
            continue

        evidence = _component_covering(graph, EXPLICIT_KINDS, rule_to_clauses)
        confidence = "explicit"
        if evidence is None:
            evidence = _component_covering(graph, EXPLICIT_KINDS | SEMANTIC_KINDS, rule_to_clauses)
            confidence = "semantic"
        if evidence is None:
            evidence = set().union(*rule_to_clauses.values())
            confidence = "co_occurrence"

        matches.append(
            {
                "combo_id": combo.combo_id,
                "matched_rules": combo.required_node_ids,
                "description": combo.description,
                "combined_severity": combo.combined_severity,
                "business_impact": combo.business_impact,
                "negotiation_priority": combo.negotiation_priority,
                "confidence": confidence,
                "clause_ids": sorted(evidence),
                "requires_expert_review": confidence != "explicit",
            }
        )
    return matches
