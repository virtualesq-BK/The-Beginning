"""Regulatory & Permitting Knowledge Graph.

Ported from global-compliance-ai (app/rag/graph.py, app/rag/store.py). Maps (country, sector) to
the permits/licenses required and their dependency order using networkx, mirroring how
risk_ontology.py structures contract-clause risk as a graph rather than flat rules.

Nodes: one per permit, keyed "<COUNTRY>:<sector>:<index>". Edge A -> B means "B depends on A"
(A must be satisfied before B), e.g. a K-REACH chemical registration feeding an environmental
impact assessment.
"""
import networkx as nx

_SEED: dict[tuple[str, str], list[dict]] = {
    ("KR", "chemical"): [
        {
            "permit": "화학물질 등록 (K-REACH)",
            "authority": "환경부",
            "documents": ["물질 안전성 정보", "노출 시나리오", "등록 신청서"],
            "legal_basis": ["화학물질의 등록 및 평가 등에 관한 법률"],
        },
        {
            "permit": "환경영향평가",
            "authority": "환경부",
            "documents": ["환경영향평가서 초안", "주민 의견 수렴 결과"],
            "legal_basis": ["환경영향평가법"],
        },
    ],
    ("KR", "infrastructure"): [
        {
            "permit": "건축허가",
            "authority": "관할 지방자치단체",
            "documents": ["건축계획서", "구조안전 확인서", "부지 소유·사용 증빙"],
            "legal_basis": ["건축법"],
        },
        {
            "permit": "환경영향평가",
            "authority": "환경부",
            "documents": ["환경영향평가서 초안", "주민 의견 수렴 결과"],
            "legal_basis": ["환경영향평가법"],
        },
    ],
    ("US", "pharma"): [
        {
            "permit": "NDA (New Drug Application)",
            "authority": "FDA",
            "documents": ["CMC 문서", "임상시험 결과", "라벨링"],
            "legal_basis": ["21 CFR Part 314"],
        }
    ],
}


class RegulatoryGraph:
    def __init__(self) -> None:
        self.g = nx.DiGraph()

    def add_permit(self, key: str, country: str, sector: str, permit: str, authority: str,
                   documents: list[str], legal_basis: list[str]) -> None:
        self.g.add_node(key, country=country.upper(), sector=sector.lower(), permit=permit,
                        authority=authority, documents=documents, legal_basis=legal_basis)

    def add_dependency(self, prerequisite: str, dependent: str) -> None:
        self.g.add_edge(prerequisite, dependent)

    def requirements(self, country: str, sector: str) -> list[dict]:
        keys = [k for k, d in self.g.nodes(data=True)
                if d["country"] == country.upper() and d["sector"] == sector.lower()]
        order = [k for k in nx.topological_sort(self.g) if k in keys]  # prerequisites first
        return [{f: self.g.nodes[k][f] for f in ("permit", "authority", "documents", "legal_basis")}
                for k in order]

    def prerequisites(self, key: str) -> list[str]:
        return sorted(nx.ancestors(self.g, key))

    def impacted_by(self, key: str) -> list[str]:
        """Permits affected if `key`'s requirements change (e.g. a rule change cascades downstream)."""
        return sorted(nx.descendants(self.g, key))

    def supported_sectors(self) -> list[dict]:
        pairs = sorted({(d["country"], d["sector"]) for _, d in self.g.nodes(data=True)})
        return [{"country": c, "sector": s} for c, s in pairs]


def build_default_graph() -> RegulatoryGraph:
    g = RegulatoryGraph()
    for (country, sector), reqs in _SEED.items():
        for i, r in enumerate(reqs):
            g.add_permit(f"{country}:{sector}:{i}", country, sector, r["permit"], r["authority"],
                         r["documents"], r["legal_basis"])
    g.add_dependency("KR:chemical:0", "KR:chemical:1")  # K-REACH registration feeds the EIA
    g.add_dependency("KR:infrastructure:0", "KR:infrastructure:1")  # 건축허가 feeds the EIA
    return g
