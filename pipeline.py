import json
import sys
from datetime import datetime, timezone

from agents.document_parser import parse_contract
from agents.translator import translate_clause
from agents.risk_analyzer import summarize_document, analyze_clause

DISCLAIMER = "본 분석은 참고용입니다. 법적 효력이 없으며, 위험도 4점 이상 조항은 반드시 변호사 검토가 필요합니다."


def run_pipeline(contract_path: str) -> dict:
    with open(contract_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    print("[Agent 1] 문서 파싱 및 조항 분류 중...")
    parsed = parse_contract(raw_text)
    clauses = parsed["clauses"]

    print(f"[Agent 1] {len(clauses)}개 조항 식별 완료")
    print("[Agent 2] 조항별 번역 중...")
    for clause in clauses:
        translation = translate_clause(clause["original_text"])
        clause["translated_text"] = translation["translated_text"]
        clause["translation_confidence"] = translation["confidence"]
        clause["translation_notes"] = translation["notes"]

    print("[Agent 3] 문서 요약(SAC) 생성 중...")
    doc_summary = summarize_document([c["translated_text"] for c in clauses])

    print("[Agent 3] 조항별 리스크 분석 중...")
    for clause in clauses:
        risk = analyze_clause(clause["clause_type"], clause["translated_text"], doc_summary)
        clause["risk"] = risk

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
        "document_summary": doc_summary,
        "clause_count": len(clauses),
        "high_risk_count": sum(1 for c in clauses if c["risk"]["risk_score"] >= 4),
        "clauses": clauses,
    }
    return report


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_contract.txt"
    report = run_pipeline(path)

    out_path = "output_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {out_path} 생성됨")
    print(f"총 조항: {report['clause_count']}건, 고위험(4점 이상) 조항: {report['high_risk_count']}건")
    print(f"\n{DISCLAIMER}")
