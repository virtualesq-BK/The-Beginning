"""전문가(변호사) Feedback Loop.

AI 판단 -> 변호사 수정 -> 수정 이유 선택 -> (검증되면) Benchmark 업데이트
로 이어지는 흐름을 구조화한다. supabase/migrate_lifecycle_and_feedback.sql의
expert_feedback / benchmark_cases 테이블과 1:1로 대응하는 스키마다.

이 모듈은 DB 접근을 하지 않는다 (프론트엔드가 frontend/src/lib/contracts.ts
방식으로 Supabase에 직접 쓰는 것과 동일하게, 여기서는 그 페이로드를
구성/검증하는 순수 함수만 제공한다). 백엔드에서 배치 처리가 필요해지면
이 모듈의 결과를 그대로 insert 페이로드로 사용할 수 있다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


_DISAGREEMENT_TYPES = {"score_only", "rule_missing", "rule_wrong", "evidence_wrong"}


@dataclass
class ExpertFeedback:
    analysis_id: str | None
    reviewer_user_id: str | None
    clause_type: str
    clause_text: str
    ai_risk_score: int
    ai_rules_applied: list[str]
    human_risk_score: int
    human_rules_applied: list[str]
    correction_reason: str
    disagreement_type: str
    promoted_to_benchmark: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_row(self) -> dict:
        """expert_feedback 테이블 insert에 그대로 쓸 수 있는 dict."""
        return {
            "analysis_id": self.analysis_id,
            "reviewer_user_id": self.reviewer_user_id,
            "clause_type": self.clause_type,
            "clause_text": self.clause_text,
            "ai_risk_score": self.ai_risk_score,
            "ai_rules_applied": self.ai_rules_applied,
            "human_risk_score": self.human_risk_score,
            "human_rules_applied": self.human_rules_applied,
            "correction_reason": self.correction_reason,
            "disagreement_type": self.disagreement_type,
            "promoted_to_benchmark": self.promoted_to_benchmark,
            "created_at": self.created_at,
        }


def _infer_disagreement_type(ai_result: dict, human_risk_score: int, human_rules_applied: list[str]) -> str:
    """수정 이유를 사람이 매번 분류하지 않아도, 결과 차이로부터 1차 분류를 시도한다.
    최종 라벨은 변호사가 correction_reason과 함께 확정하는 것을 권장한다."""
    ai_rules = set(ai_result.get("rules_applied", []))
    human_rules = set(human_rules_applied)

    if ai_rules == human_rules:
        return "score_only"
    if human_rules - ai_rules:
        return "rule_missing"  # AI가 놓친 rule을 변호사가 추가함
    if ai_rules - human_rules:
        return "rule_wrong"  # AI가 잘못 적용한 rule을 변호사가 제거함
    return "score_only"


def record_feedback(
    *,
    ai_result: dict,
    clause_type: str,
    clause_text: str,
    human_risk_score: int,
    human_rules_applied: list[str],
    correction_reason: str,
    analysis_id: str | None = None,
    reviewer_user_id: str | None = None,
    disagreement_type: str | None = None,
) -> ExpertFeedback:
    """risk_analyzer.analyze_clause()의 결과(ai_result)와 변호사의 수정
    내용을 받아 ExpertFeedback 레코드를 만든다.

    단순히 "Risk = High로 바뀜"만 저장하지 않고, "왜 High인가"를
    correction_reason에 반드시 채우도록 강제한다 (빈 문자열 거부).
    이 한 줄이 나중에 Domain-specific Evaluation Dataset을 만드는
    핵심 데이터가 된다.
    """
    if not correction_reason or not correction_reason.strip():
        raise ValueError("correction_reason은 비워둘 수 없습니다 - '왜 다른가'가 핵심 데이터입니다.")

    resolved_type = disagreement_type or _infer_disagreement_type(
        ai_result, human_risk_score, human_rules_applied
    )
    if resolved_type not in _DISAGREEMENT_TYPES:
        raise ValueError(f"disagreement_type은 {_DISAGREEMENT_TYPES} 중 하나여야 합니다: {resolved_type}")

    return ExpertFeedback(
        analysis_id=analysis_id,
        reviewer_user_id=reviewer_user_id,
        clause_type=clause_type,
        clause_text=clause_text,
        ai_risk_score=int(ai_result.get("risk_score", 0)),
        ai_rules_applied=list(ai_result.get("rules_applied", [])),
        human_risk_score=human_risk_score,
        human_rules_applied=human_rules_applied,
        correction_reason=correction_reason.strip(),
        disagreement_type=resolved_type,
    )


def promote_to_benchmark_case(feedback: ExpertFeedback, *, reviewed_by: str | None = None) -> dict:
    """검증된 expert_feedback을 benchmark_cases row로 변환한다.

    AI가 명백히 틀렸고 변호사 판단이 확정된(promoted) 케이스만 승격 대상이다.
    호출부(운영 프로세스)가 검증 절차를 거친 뒤 이 함수를 호출해야 한다.
    """
    feedback.promoted_to_benchmark = True
    return {
        "source_feedback_id": None,  # DB insert 후 실제 expert_feedback.id로 채워짐
        "clause_type": feedback.clause_type,
        "clause_text": feedback.clause_text,
        "expected_risk_score": feedback.human_risk_score,
        "expected_rules_applied": feedback.human_rules_applied,
        "expected_evidence_quote": None,
        "expected_negotiation_point": None,
        "reviewed_by": reviewed_by,
    }
