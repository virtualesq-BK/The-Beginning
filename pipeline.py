import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents.document_parser import parse_contract
from agents.translator import translate_clause
from agents.risk_analyzer import summarize_document, analyze_clause
from agents.file_extractor import extract_text
from agents.sac_chunker import ContractSACIndex
from agents.clause_graph import (
    EXPLICIT_KINDS,
    SEMANTIC_KINDS,
    build_clause_graph,
    evaluate_cross_clause_risks_graph,
)

_MAX_RELATED_CLAUSES = 4

DISCLAIMER_KO = "본 분석은 참고용입니다. 법적 효력이 없으며, 위험도 4점 이상 조항은 반드시 변호사 검토가 필요합니다."
DISCLAIMER_EN = (
    "This analysis is for reference purposes only. It has no legal effect, and clauses with a risk "
    "score of 4 or higher must be reviewed by a lawyer."
)
DISCLAIMERS = {"ko": DISCLAIMER_KO, "en": DISCLAIMER_EN}
DISCLAIMER = DISCLAIMER_KO  # 하위 호환용 (기본값 한국어)


def run_pipeline(raw_text: str, language: str = "ko") -> dict:
    disclaimer = DISCLAIMERS.get(language, DISCLAIMER_KO)

    print("[Agent 1] 문서 파싱 및 조항 분류 중...")
    parsed = parse_contract(raw_text)
    clauses = parsed["clauses"]

    print(f"[Agent 1] {len(clauses)}개 조항 식별 완료")
    print("[Agent 2] 조항별 번역 중...")
    for clause in clauses:
        translation = translate_clause(clause["original_text"], language=language)
        clause["translated_text"] = translation["translated_text"]
        clause["translation_confidence"] = translation["confidence"]
        clause["translation_notes"] = translation["notes"]

    print("[Agent 3] 문서 요약 생성 중...")
    doc_summary = summarize_document([c["translated_text"] for c in clauses], language=language)

    print("[Agent 3] SAC 인덱스(문서 요약 + 조항) 임베딩 중...")
    similar_pairs: list[tuple[int, int, float]] = []
    sac_status = "ok"
    try:
        similar_pairs = ContractSACIndex(clauses, doc_summary).similar_clause_pairs(top_k=2)
    except Exception as e:  # 임베딩 API 실패 시 명시적 참조 그래프만으로 계속 진행
        sac_status = f"unavailable: {type(e).__name__}"
        print(f"[Agent 3] SAC 인덱스 생략 ({sac_status})")

    print("[Agent 3] Clause Graph 구성 중...")
    graph = build_clause_graph(clauses, similar_pairs)
    by_id = {c["id"]: c for c in clauses}

    print("[Agent 3] 조항별 리스크 분석 중...")
    for clause in clauses:
        explicit = graph.neighbors(clause["id"], EXPLICIT_KINDS)
        semantic = [cid for cid in graph.neighbors(clause["id"], SEMANTIC_KINDS) if cid not in explicit]
        related_ids = (explicit + semantic)[:_MAX_RELATED_CLAUSES]
        clause["related_clause_ids"] = related_ids
        clause["risk"] = analyze_clause(
            clause["clause_type"],
            clause["translated_text"],
            doc_summary,
            language=language,
            related_clauses=[by_id[cid] for cid in related_ids],
            related_clause_types=[by_id[cid]["clause_type"] for cid in explicit],
        )

    print("[Agent 4] 조항 간 상호작용(Cross-Clause Risk) 분석 중...")
    clause_rules = {c["id"]: set(c["risk"].get("rules_applied", [])) for c in clauses}
    cross_clause_risks = evaluate_cross_clause_risks_graph(clause_rules, graph)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": disclaimer,
        "document_summary": doc_summary,
        "clause_count": len(clauses),
        "high_risk_count": sum(1 for c in clauses if c["risk"]["risk_score"] >= 4),
        "cross_clause_risks": cross_clause_risks,
        "clause_graph": {**graph.to_dict(), "sac_status": sac_status},
        "clauses": clauses,
    }
    return report


if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "sample_contract.txt")
    raw_text = extract_text(path.read_bytes(), path.name)
    report = run_pipeline(raw_text)

    out_path = "output_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {out_path} 생성됨")
    print(f"총 조항: {report['clause_count']}건, 고위험(4점 이상) 조항: {report['high_risk_count']}건")
    print(f"\n{DISCLAIMER}")
