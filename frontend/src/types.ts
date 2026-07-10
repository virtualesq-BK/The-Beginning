export interface RiskAssessment {
  risk_score: number;
  risk_reason: string;
  evidence_quote: string;
  recommendation: string;
  references?: string[];
  requires_lawyer_review: boolean;
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
}

export interface ContractReport {
  generated_at: string;
  disclaimer: string;
  document_summary: string;
  clause_count: number;
  high_risk_count: number;
  clauses: Clause[];
}
