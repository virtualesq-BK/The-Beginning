export interface RiskAssessment {
  risk_score: number;
  risk_reason: string;
  evidence_quote: string;
  recommendation: string;
  references?: string[];
  requires_lawyer_review: boolean;
  /** Legal Decision Model(risk_ontology.py) 노드 ID 목록. 예: ["FIDIC-DELAY-LD"] */
  rules_applied?: string[];
  /** 실무상 어떤 결과로 이어지는지 (예: 지연 발생 시 LD+추가 손해배상 중복 가능) */
  business_impact?: string;
  /** 협상 시 요구할 구체적 지점 (예: Notice 기간 7 -> 14일) */
  negotiation_point?: string;
  /** 대체 문구 초안 */
  alternative_text?: string;
}

export interface Clause {
  id: number;
  clause_type: string;
  title: string;
  original_text: string;
  translated_text: string;
  translation_confidence: number;
  translation_notes: string;
  risk: RiskAssessment;
  /** 계약서에 표기된 조항 번호 (예: "8.7") */
  clause_number?: string;
  parent_number?: string;
  /** 본문이 참조하는 다른 조항 번호 (예: ["20.1"]) */
  cross_references?: string[];
  /** Clause Graph에서 연결되어 분석 근거로 함께 제공된 조항 id */
  related_clause_ids?: number[];
}

/** 개별 조항은 낮아 보여도 특정 조합이 함께 있으면 위험도가 급등하는
 * 패턴(agents/risk_ontology.py의 RiskCombination)을 문서 단위에서 탐지한 결과. */
export interface CrossClauseRisk {
  combo_id: string;
  matched_rules: string[];
  description: string;
  combined_severity: "high" | "critical";
  business_impact: string;
  negotiation_priority: string;
  /** explicit: 한 조항 내 또는 계층/명시적 참조로 연결 · semantic: SAC 의미유사도로만 연결 ·
   * co_occurrence: 같은 계약서에 함께 있으나 연결 미확인 */
  confidence?: "explicit" | "semantic" | "co_occurrence";
  /** 판정 근거가 된 조항 id */
  clause_ids?: number[];
  requires_expert_review?: boolean;
}

export interface ContractReport {
  generated_at: string;
  disclaimer: string;
  document_summary: string;
  clause_count: number;
  high_risk_count: number;
  cross_clause_risks?: CrossClauseRisk[];
  clauses: Clause[];
}
