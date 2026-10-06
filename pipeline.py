import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
_MAX_CLAUSES = 30          # 이 이상이면 위험도 높은 유형 우선 선별
_PARALLEL_WORKERS = 8      # 번역·분석 병렬 스레드 수

# 우선순위 높은 조항 유형 (많을 경우 이 타입 먼저 포함)
_HIGH_PRIORITY_TYPES = {
    "지체상금", "면책", "손해배상", "불가항력", "계약해지",
    "중재", "분쟁해결", "이행보증", "하자담보", "지급조건",
}

DISCLAIMER_KO = "본 분석은 참고용입니다. 법적 효력이 없으며, 위험도 4점 이상 조항은 반드시 변호사 검토가 필요합니다."
DISCLAIMER_EN = (
    "This analysis is for reference purposes only. It has no legal effect, and clauses with a risk "
    "score of 4 or higher must be reviewed by a lawyer."
)
DISCLAIMERS = {"ko": DISCLAIMER_KO, "en": DISCLAIMER_EN}
DISCLAIMER = DISCLAIMER_KO


def _select_clauses(clauses: list[dict], max_count: int) -> list[dict]:
    """조항이 max_count를 초과하면 고위험 유형을 우선 선별하고 나머지를 균등 샘플링."""
    if len(clauses) <= max_count:
        return clauses
    priority = [c for c in clauses if c.get("clause_type") in _HIGH_PRIORITY_TYPES]
    rest = [c for c in clauses if c.get("clause_type") not in _HIGH_PRIORITY_TYPES]
    remaining = max_count - len(priority)
    if remaining <= 0:
        selected = priority[:max_count]
    else:
        # rest에서 균등 간격으로 샘플링
        step = max(1, len(rest) // remaining)
        sampled = rest[::step][:remaining]
        selected = priority + sampled
    # 원래 순서 유지
    ids = {id(c) for c in selected}
    return [c for c in clauses if id(c) in ids]


def _translate_one(args):
    clause, language = args
    translation = translate_clause(clause["original_text"], language=language)
    return clause["id"], translation


def _analyze_one(args):
    clause, doc_summary, language, related_clauses, related_clause_types = args
    risk = analyze_clause(
        clause["clause_type"],
        clause["translated_text"],
        doc_summary,
        language=language,
        related_clauses=related_clauses,
        related_clause_types=related_clause_types,
    )
    return clause["id"], risk


def run_pipeline(raw_text: str, language: str = "ko") -> dict:
    disclaimer = DISCLAIMERS.get(language, DISCLAIMER_KO)

    print("[Agent 1] 문서 파싱 및 조항 분류 중...")
    parsed = parse_contract(raw_text)
    all_clauses = parsed["clauses"]
    total_parsed = len(all_clauses)

    clauses = _select_clauses(all_clauses, _MAX_CLAUSES)
    if len(clauses) < total_parsed:
        print(f"[Agent 1] {total_parsed}개 조항 중 {len(clauses)}개 선별 (고위험 유형 우선)")
    else:
        print(f"[Agent 1] {len(clauses)}개 조항 식별 완료")

    by_id = {c["id"]: c for c in clauses}

    print(f"[Agent 2] 조항별 번역 병렬 처리 중... ({_PARALLEL_WORKERS} workers)")
    with ThreadPoolExecutor(max_workers=_PARALLEL_WORKERS) as executor:
        futures = {
            executor.submit(_translate_one, (clause, language)): clause["id"]
            for clause in clauses
        }
        for future in as_completed(futures):
            cid, translation = future.result()
            c = by_id[cid]
            c["translated_text"] = translation["translated_text"]
            c["translation_confidence"] = translation["confidence"]
            c["translation_notes"] = translation["notes"]

    print("[Agent 3] 문서 요약 생성 중...")
    doc_summary = summarize_document([c["translated_text"] for c in clauses], language=language)

    print("[Agent 3] SAC 인덱스(문서 요약 + 조항) 임베딩 중...")
    similar_pairs: list[tuple[int, int, float]] = []
    sac_status = "ok"
    try:
        similar_pairs = ContractSACIndex(clauses, doc_summary).similar_clause_pairs(top_k=2)
    except Exception as e:
        sac_status = f"unavailable: {type(e).__name__}"
        print(f"[Agent 3] SAC 인덱스 생략 ({sac_status})")

    print("[Agent 3] Clause Graph 구성 중...")
    graph = build_clause_graph(clauses, similar_pairs)

    print(f"[Agent 3] 조항별 리스크 분석 병렬 처리 중... ({_PARALLEL_WORKERS} workers)")
    # Graph 탐색은 GIL 안에서 빠르게 완료되므로 먼저 수행
    analyze_args = []
    for clause in clauses:
        explicit = graph.neighbors(clause["id"], EXPLICIT_KINDS)
        semantic = [cid for cid in graph.neighbors(clause["id"], SEMANTIC_KINDS) if cid not in explicit]
        related_ids = (explicit + semantic)[:_MAX_RELATED_CLAUSES]
        clause["related_clause_ids"] = related_ids
        analyze_args.append((
            clause,
            doc_summary,
            language,
            [by_id[cid] for cid in related_ids],
            [by_id[cid]["clause_type"] for cid in explicit],
        ))

    with ThreadPoolExecutor(max_workers=_PARALLEL_WORKERS) as executor:
        futures = {executor.submit(_analyze_one, args): args[0]["id"] for args in analyze_args}
        for future in as_completed(futures):
            cid, risk = future.result()
            by_id[cid]["risk"] = risk

    print("[Agent 4] 조항 간 상호작용(Cross-Clause Risk) 분석 중...")
    clause_rules = {c["id"]: set(c["risk"].get("rules_applied", [])) for c in clauses}
    cross_clause_risks = evaluate_cross_clause_risks_graph(clause_rules, graph)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": disclaimer,
        "document_summary": doc_summary,
        "clause_count": len(clauses),
        "total_parsed_count": total_parsed,
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
    print(f"총 조항: {report['clause_count']}건 (파싱: {report['total_parsed_count']}건), 고위험(4점 이상) 조항: {report['high_risk_count']}건")
    print(f"\n{DISCLAIMER}")
