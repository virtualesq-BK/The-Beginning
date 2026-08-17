export type ComparisonStatus = "good" | "watch" | "risk";

export type FIDICIssueTemplate = {
  id: string;
  label: string;
  fidicBenchmark: string;
  positiveKeywords: string[];
  warningKeywords: string[];
  recommendedAction: string;
};

export type ConstructionComparisonIssue = {
  id: string;
  label: string;
  score: number;
  status: ComparisonStatus;
  fidicBenchmark: string;
  evidence: string[];
  recommendation: string;
};

export type ConstructionComparisonResult = {
  overallScore: number;
  summary: string;
  issues: ConstructionComparisonIssue[];
  focusAreas: string[];
};

const FIDIC_ISSUES: FIDICIssueTemplate[] = [
  {
    id: "design-responsibility",
    label: "설계 책임",
    fidicBenchmark: "Red Book은 발주자 중심, Yellow/Silver는 시공사 설계 책임이 더 큼",
    positiveKeywords: ["design responsibility", "design risk", "design-build", "engineer review", "design documents"],
    warningKeywords: ["design scope unclear", "unidentified design responsibility", "no design responsibility"],
    recommendedAction: "설계 범위와 책임 소재를 문서 상에서 명확히 분리하세요. 시공사 설계책임이 있다면 검토·승인 절차와 책임 범위를 구체화해야 합니다.",
  },
  {
    id: "variation",
    label: "변경지시 / 공사 변경",
    fidicBenchmark: "변경지시(Variation)는 EOT와 비용 조정 절차와 연계되어야 함",
    positiveKeywords: ["variation", "change order", "change order procedure", "extension of time", "eot", "cost adjustment"],
    warningKeywords: ["employer may vary without compensation", "unilateral change without adjustment"],
    recommendedAction: "변경지시 시 공기 연장, 비용 조정, 클레임 절차를 연결하는 문구를 추가하세요.",
  },
  {
    id: "delay-damages",
    label: "지체상금 / LD",
    fidicBenchmark: "지체상금은 보통 상한(cap)과 예외사유를 함께 검토해야 함",
    positiveKeywords: ["liquidated damages", "delay damages", "ld", "cap", "delay penalty", "daily delay damages"],
    warningKeywords: ["without cap", "unlimited liability", "no limitation of ld"],
    recommendedAction: "지체상금 상한, 예외사유, 손해배상 중복 제한 여부를 정리해 과도한 책임을 막는 것이 좋습니다.",
  },
  {
    id: "defects-liability",
    label: "하자보수 / DLP",
    fidicBenchmark: "하자담보기간은 통상 1~2년 수준이 일반적이며 과도한 장기 보수는 위험",
    positiveKeywords: ["defects liability", "defects notification", "warranty period", "rectification", "defect rectification"],
    warningKeywords: ["36 months defects liability", "lifetime warranty", "indefinite warranty"],
    recommendedAction: "하자 통지 기간, 보수기간, 통지 시점, 성능 기준을 현실적으로 정리하고, 보완 사유에 대한 기준을 명시하세요.",
  },
  {
    id: "performance-security",
    label: "이행보증 / 보증",
    fidicBenchmark: "보증액, 적격성, 해지 시 효력은 성과 안정성의 핵심 요소",
    positiveKeywords: ["performance bond", "bank guarantee", "guarantee", "security", "advance payment guarantee"],
    warningKeywords: ["no guarantee", "no performance security", "guarantee omitted"],
    recommendedAction: "이행보증, 보증액, 해지 시 보증 실행 조건을 명확히 하여 프로젝트 안정성을 확보하세요.",
  },
  {
    id: "dispute-resolution",
    label: "분쟁해결 / 중재",
    fidicBenchmark: "DAB, 중재기관, 중재지, 준거법, 언어가 명확해야 분쟁 비용과 기간을 줄일 수 있음",
    positiveKeywords: ["arbitration", "dispute adjudication board", "dab", "governing law", "icc arbitration", "siac"],
    warningKeywords: ["no arbitration clause", "unclear governing law", "no dispute mechanism"],
    recommendedAction: "중재기관, 중재지, 준거법, 언어를 명시하고, DAB 또는 조정 절차를 함께 두는 것이 바람직합니다.",
  },
  {
    id: "payment-and-acceptance",
    label: "지급 및 인도 / 시험인수",
    fidicBenchmark: "중도금 지급, 인도 기준, 시험인수, 면제 조건은 현금흐름과 프로젝트 완료 기준을 좌우함",
    positiveKeywords: ["payment certificate", "interim payment", "milestone payment", "testing", "takeover", "acceptance"],
    warningKeywords: ["payment withheld without reason", "acceptance without test", "unclear acceptance criteria"],
    recommendedAction: "인도 기준, 테스트 절차, 지급보류 사유와 통지기한을 명확히 하여 현금흐름 분쟁을 줄이세요.",
  },
];

function normalize(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9가-힣\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractMatches(keywords: string[], text: string): string[] {
  const normalizedText = normalize(text);
  const matches = keywords
    .map((keyword) => keyword.trim())
    .filter((keyword) => keyword && normalizedText.includes(normalize(keyword)))
    .slice(0, 3);
  return matches;
}

export function compareDraftToFIDIC(contractText: string): ConstructionComparisonResult {
  const text = contractText ?? "";
  if (!text.trim()) {
    return {
      overallScore: 0,
      summary: "계약서 내용이 비어 있습니다. 비교표를 만들려면 건설계약 원문이나 초안을 붙여 넣어 주세요.",
      issues: FIDIC_ISSUES.map((issue) => ({
        id: issue.id,
        label: issue.label,
        score: 0,
        status: "risk",
        fidicBenchmark: issue.fidicBenchmark,
        evidence: [],
        recommendation: issue.recommendedAction,
      })),
      focusAreas: FIDIC_ISSUES.map((issue) => issue.label),
    };
  }

  const issues = FIDIC_ISSUES.map((issue) => {
    const positiveMatches = extractMatches(issue.positiveKeywords, text);
    const warningMatches = extractMatches(issue.warningKeywords, text);

    let score = 35;
    if (positiveMatches.length >= 2) score += 30;
    else if (positiveMatches.length === 1) score += 18;

    if (warningMatches.length > 0) score -= warningMatches.length * 20;
    if (positiveMatches.length >= 3) score += 10;

    score = Math.max(0, Math.min(100, score));

    const status: ComparisonStatus = score >= 75 ? "good" : score >= 50 ? "watch" : "risk";

    return {
      id: issue.id,
      label: issue.label,
      score,
      status,
      fidicBenchmark: issue.fidicBenchmark,
      evidence: [...positiveMatches, ...warningMatches],
      recommendation:
        score >= 60
          ? `${issue.label} 항목은 FIDIC 기준 대비 ${score}% 수준으로 반영되어 있습니다. 문구를 조금 더 명확하게 다듬으면 보완 효과가 큽니다.`
          : issue.recommendedAction,
    };
  });

  const overallScore = Math.round(
    issues.reduce((sum, issue) => sum + issue.score, 0) / Math.max(issues.length, 1),
  );

  const focusAreas = issues
    .filter((issue) => issue.score < 60)
    .map((issue) => issue.label)
    .slice(0, 5);

  const summary =
    focusAreas.length === 0
      ? "현재 문안은 FIDIC 기준에 근접하게 정리되어 있습니다. 다만 세부 문구를 점검해 안정성을 더 높이면 좋습니다."
      : `현재 문안은 ${focusAreas.join(", ")} 항목에서 FIDIC 기준과의 편차가 가장 큽니다. 우선순위 조정이 필요합니다.`;

  return {
    overallScore,
    summary,
    issues,
    focusAreas,
  };
}
