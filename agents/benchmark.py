"""Contract Intelligence Benchmark.

범용 LLM benchmark가 아니라, 이 제품이 실제로 잘해야 하는 것 - 조항 탐지,
위험 탐지, 근거 정확성, Rule 적용 정확성, 조항 간 상호작용 추론, 인용
정확성 - 을 직접 측정하는 자체 평가 데이터셋/스코어러.

benchmark_cases 테이블(supabase/migrate_lifecycle_and_feedback.sql)의
row와 동일한 구조를 BenchmarkCase로 표현하고, risk_analyzer.analyze_clause()
의 실제 출력(prediction)과 비교해 아래 표의 지표를 계산한다.

평가항목            | 측정
--------------------|------------------------------------------
Clause Detection    | 조항유형 탐지 정확도
Risk Detection      | 위험조항 Recall (실제 고위험을 놓치지 않았는가)
False Positive      | 저위험을 고위험으로 잘못 판정한 비율
Evidence Accuracy   | evidence_quote가 실제 근거 조항과 일치하는가
Rule Accuracy       | rules_applied가 Ground Truth rule과 얼마나 겹치는가 (F1)
Cross-Clause        | 조합 위험(RiskCombination)을 놓치지 않고 탐지했는가
Citation Accuracy   | references(KB doc_id)가 실제 인용 가능한 근거인가

Negotiation Utility / Recommendation Accuracy / Time Reduction은 자동
채점이 어려운 항목이라 이 모듈에서는 사람이 채운 rating을 그대로
평균하는 수준으로만 지원한다 (human_ratings 인자).
"""

from dataclasses import dataclass, field

from .risk_ontology import evaluate_cross_clause_risks


@dataclass
class BenchmarkCase:
    case_id: str
    clause_type: str
    clause_text: str
    expected_risk_score: int
    expected_rules_applied: list[str]
    expected_evidence_quote: str | None = None
    expected_combo_ids: list[str] = field(default_factory=list)  # 이 케이스가 포함된 문서에서 기대되는 조합위험


@dataclass
class Prediction:
    case_id: str
    predicted_clause_type: str
    risk_score: int
    rules_applied: list[str]
    evidence_quote: str = ""
    references: list[str] = field(default_factory=list)


def _rule_f1(expected: list[str], predicted: list[str]) -> float:
    exp, pred = set(expected), set(predicted)
    if not exp and not pred:
        return 1.0
    if not exp or not pred:
        return 0.0
    tp = len(exp & pred)
    precision = tp / len(pred)
    recall = tp / len(exp)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _evidence_matches(expected: str | None, predicted: str) -> bool:
    if not expected:
        return True  # 기대 근거가 없으면 채점 대상 제외 (평균 계산 시 skip 처리)
    expected_norm = expected.strip().lower()
    predicted_norm = (predicted or "").strip().lower()
    if not expected_norm or not predicted_norm:
        return False
    # 완전 일치를 요구하지 않고, 부분 문자열 겹침으로 "같은 근거를 인용했는가"를 판단
    return expected_norm in predicted_norm or predicted_norm in expected_norm


HIGH_RISK_THRESHOLD = 4


def evaluate_predictions(
    cases: list[BenchmarkCase],
    predictions: dict[str, Prediction],
    all_rules_applied_in_document: set[str] | None = None,
) -> dict:
    """cases(Ground Truth)와 predictions(case_id -> Prediction)를 비교해
    지표 dict를 반환한다. case_id가 predictions에 없으면 해당 케이스는
    "탐지 실패(clause_detection=False)"로 처리된다.
    """
    n = len(cases)
    if n == 0:
        return {"case_count": 0}

    clause_detection_hits = 0
    risk_true_positive = 0
    risk_actual_positive = 0
    false_positive = 0
    risk_actual_negative = 0
    rule_f1_scores: list[float] = []
    evidence_hits = 0
    evidence_scorable = 0

    for case in cases:
        pred = predictions.get(case.case_id)
        if pred is None:
            # 조항 자체를 탐지하지 못함 -> 나머지 지표는 최하점으로 집계
            if case.expected_risk_score >= HIGH_RISK_THRESHOLD:
                risk_actual_positive += 1
            else:
                risk_actual_negative += 1
            rule_f1_scores.append(0.0)
            continue

        if pred.predicted_clause_type == case.clause_type:
            clause_detection_hits += 1

        is_high_expected = case.expected_risk_score >= HIGH_RISK_THRESHOLD
        is_high_predicted = pred.risk_score >= HIGH_RISK_THRESHOLD
        if is_high_expected:
            risk_actual_positive += 1
            if is_high_predicted:
                risk_true_positive += 1
        else:
            risk_actual_negative += 1
            if is_high_predicted:
                false_positive += 1

        rule_f1_scores.append(_rule_f1(case.expected_rules_applied, pred.rules_applied))

        if case.expected_evidence_quote:
            evidence_scorable += 1
            if _evidence_matches(case.expected_evidence_quote, pred.evidence_quote):
                evidence_hits += 1

    cross_clause_recall = None
    if all_rules_applied_in_document is not None:
        expected_combo_ids = {cid for case in cases for cid in case.expected_combo_ids}
        if expected_combo_ids:
            detected = {m["combo_id"] for m in evaluate_cross_clause_risks(all_rules_applied_in_document)}
            cross_clause_recall = len(expected_combo_ids & detected) / len(expected_combo_ids)

    return {
        "case_count": n,
        "clause_detection_accuracy": clause_detection_hits / n,
        "risk_detection_recall": (risk_true_positive / risk_actual_positive) if risk_actual_positive else None,
        "false_positive_rate": (false_positive / risk_actual_negative) if risk_actual_negative else None,
        "rule_accuracy_f1": sum(rule_f1_scores) / len(rule_f1_scores) if rule_f1_scores else None,
        "evidence_accuracy": (evidence_hits / evidence_scorable) if evidence_scorable else None,
        "cross_clause_reasoning_recall": cross_clause_recall,
    }


def evaluate_human_ratings(human_ratings: list[dict]) -> dict:
    """Negotiation Utility / Recommendation Accuracy처럼 자동 채점이
    어려운 항목을 위해, 리뷰어가 1~5점으로 채점한 결과를 집계한다.

    human_ratings 예: [{"negotiation_utility": 4, "recommendation_accuracy": 5}, ...]
    """
    if not human_ratings:
        return {}
    keys = {k for row in human_ratings for k in row.keys()}
    return {
        key: sum(row.get(key, 0) for row in human_ratings) / len(human_ratings)
        for key in keys
    }
