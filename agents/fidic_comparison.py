import re
from typing import Any

ISSUE_LABELS_EN = {
    "design-responsibility": "Design Responsibility",
    "variation": "Variation / Change Orders",
    "delay-damages": "Delay Damages / LD",
    "defects-liability": "Defects Liability / DLP",
    "performance-security": "Performance Security / Guarantees",
    "dispute-resolution": "Dispute Resolution / Arbitration",
    "payment-and-acceptance": "Payment & Acceptance / Testing",
}

ISSUE_BENCHMARKS_EN = {
    "design-responsibility": "Red Book is employer-centric; Yellow/Silver place greater design responsibility on the contractor",
    "variation": "Variations must be linked to EOT and cost-adjustment procedures",
    "delay-damages": "Delay damages should generally be reviewed together with a cap and any exceptions",
    "defects-liability": "The defects liability period is typically 1-2 years; excessively long periods are risky",
    "performance-security": "Guarantee amount, eligibility, and effect upon termination are key to performance stability",
    "dispute-resolution": "DAB, arbitration institution, seat, governing law, and language must be clear to limit dispute cost and duration",
    "payment-and-acceptance": "Interim payments, acceptance criteria, testing, and exemption conditions govern cash flow and project completion",
}

ISSUE_RECOMMENDATIONS_EN = {
    "design-responsibility": "Clearly separate the design scope and responsibility in the document. If the contractor bears design responsibility, specify the review/approval process and scope of responsibility.",
    "variation": "Add language linking variations to extension of time, cost adjustment, and claim procedures.",
    "delay-damages": "Clarify the LD cap, exceptions, and any restriction on duplicate damages claims to avoid excessive liability.",
    "defects-liability": "Set realistic notification periods, rectification periods, notice timing, and performance criteria, and specify the basis for any remedial work.",
    "performance-security": "Clarify the performance security, guarantee amount, and conditions for calling the guarantee upon termination to secure project stability.",
    "dispute-resolution": "Specify the arbitration institution, seat, governing law, and language, and consider adding a DAB or mediation procedure.",
    "payment-and-acceptance": "Clarify acceptance criteria, testing procedures, and payment withholding grounds/notice periods to reduce cash-flow disputes.",
}

_EMPTY_SUMMARY = {
    "ko": "계약서 내용이 비어 있습니다. 비교표를 만들려면 건설계약 원문이나 초안을 붙여 넣어 주세요.",
    "en": "The contract content is empty. Paste the original construction contract text or draft to generate a comparison table.",
}

_BALANCE_LABELS = {
    "ko": {"employer": "발주자 유리", "contractor": "시공사 유리", "neutral": "균형형"},
    "en": {"employer": "Employer-favorable", "contractor": "Contractor-favorable", "neutral": "Balanced"},
}


def _issue_label(issue: dict, language: str) -> str:
    return ISSUE_LABELS_EN.get(issue["id"], issue["label"]) if language == "en" else issue["label"]


def _issue_benchmark(issue: dict, language: str) -> str:
    return ISSUE_BENCHMARKS_EN.get(issue["id"], issue["fidic_benchmark"]) if language == "en" else issue["fidic_benchmark"]


def _issue_recommendation(issue: dict, language: str) -> str:
    return (
        ISSUE_RECOMMENDATIONS_EN.get(issue["id"], issue["recommended_action"])
        if language == "en"
        else issue["recommended_action"]
    )


ISSUE_TEMPLATES = [
    {
        "id": "design-responsibility",
        "label": "설계 책임",
        "fidic_benchmark": "Red Book은 발주자 중심, Yellow/Silver는 시공사 설계 책임이 더 큼",
        "positive_keywords": [
            "design responsibility",
            "design risk",
            "design-build",
            "engineer review",
            "design documents",
        ],
        "warning_keywords": [
            "design scope unclear",
            "unidentified design responsibility",
            "no design responsibility",
        ],
        "recommended_action": "설계 범위와 책임 소재를 문서 상에서 명확히 분리하세요. 시공사 설계책임이 있다면 검토·승인 절차와 책임 범위를 구체화해야 합니다.",
    },
    {
        "id": "variation",
        "label": "변경지시 / 공사 변경",
        "fidic_benchmark": "변경지시(Variation)는 EOT와 비용 조정 절차와 연계되어야 함",
        "positive_keywords": [
            "variation",
            "change order",
            "change order procedure",
            "extension of time",
            "eot",
            "cost adjustment",
        ],
        "warning_keywords": [
            "employer may vary without compensation",
            "unilateral change without adjustment",
        ],
        "recommended_action": "변경지시 시 공기 연장, 비용 조정, 클레임 절차를 연결하는 문구를 추가하세요.",
    },
    {
        "id": "delay-damages",
        "label": "지체상금 / LD",
        "fidic_benchmark": "지체상금은 보통 상한(cap)과 예외사유를 함께 검토해야 함",
        "positive_keywords": [
            "liquidated damages",
            "delay damages",
            "ld",
            "cap",
            "delay penalty",
            "daily delay damages",
        ],
        "warning_keywords": [
            "without cap",
            "unlimited liability",
            "no limitation of ld",
        ],
        "recommended_action": "지체상금 상한, 예외사유, 손해배상 중복 제한 여부를 정리해 과도한 책임을 막는 것이 좋습니다.",
    },
    {
        "id": "defects-liability",
        "label": "하자보수 / DLP",
        "fidic_benchmark": "하자담보기간은 통상 1~2년 수준이 일반적이며 과도한 장기 보수는 위험",
        "positive_keywords": [
            "defects liability",
            "defects notification",
            "warranty period",
            "rectification",
            "defect rectification",
        ],
        "warning_keywords": [
            "36 months defects liability",
            "lifetime warranty",
            "indefinite warranty",
        ],
        "recommended_action": "하자 통지 기간, 보수기간, 통지 시점, 성능 기준을 현실적으로 정리하고, 보완 사유에 대한 기준을 명시하세요.",
    },
    {
        "id": "performance-security",
        "label": "이행보증 / 보증",
        "fidic_benchmark": "보증액, 적격성, 해지 시 효력은 성과 안정성의 핵심 요소",
        "positive_keywords": [
            "performance bond",
            "bank guarantee",
            "guarantee",
            "security",
            "advance payment guarantee",
        ],
        "warning_keywords": [
            "no guarantee",
            "no performance security",
            "guarantee omitted",
        ],
        "recommended_action": "이행보증, 보증액, 해지 시 보증 실행 조건을 명확히 하여 프로젝트 안정성을 확보하세요.",
    },
    {
        "id": "dispute-resolution",
        "label": "분쟁해결 / 중재",
        "fidic_benchmark": "DAB, 중재기관, 중재지, 준거법, 언어가 명확해야 분쟁 비용과 기간을 줄일 수 있음",
        "positive_keywords": [
            "arbitration",
            "dispute adjudication board",
            "dab",
            "governing law",
            "icc arbitration",
            "siac",
        ],
        "warning_keywords": [
            "no arbitration clause",
            "unclear governing law",
            "no dispute mechanism",
        ],
        "recommended_action": "중재기관, 중재지, 준거법, 언어를 명시하고, DAB 또는 조정 절차를 함께 두는 것이 바람직합니다.",
    },
    {
        "id": "payment-and-acceptance",
        "label": "지급 및 인도 / 시험인수",
        "fidic_benchmark": "중도금 지급, 인도 기준, 시험인수, 면제 조건은 현금흐름과 프로젝트 완료 기준을 좌우함",
        "positive_keywords": [
            "payment certificate",
            "interim payment",
            "milestone payment",
            "testing",
            "takeover",
            "acceptance",
        ],
        "warning_keywords": [
            "payment withheld without reason",
            "acceptance without test",
            "unclear acceptance criteria",
        ],
        "recommended_action": "인도 기준, 테스트 절차, 지급보류 사유와 통지기한을 명확히 하여 현금흐름 분쟁을 줄이세요.",
    },
]


def normalize_text(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9가-힣\s]", " ", value.lower()).replace("\s+", " ").strip()


def detect_keywords(text: str, keywords: list[str]) -> list[str]:
    norm_text = normalize_text(text)
    matches: list[str] = []
    for keyword in keywords:
        k = normalize_text(keyword)
        if k and k in norm_text and keyword not in matches:
            matches.append(keyword)
    return matches[:3]


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    segments = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [segment.strip() for segment in segments if segment and segment.strip()]


def extract_sentence_evidence(text: str, keywords: list[str]) -> list[str]:
    if not text or not keywords:
        return []
    raw_sentences = split_sentences(text)
    matches: list[str] = []
    normalized_keywords = [normalize_text(k) for k in keywords]
    for sentence in raw_sentences:
        norm_sentence = normalize_text(sentence)
        if any(keyword in norm_sentence for keyword in normalized_keywords):
            matches.append(sentence.strip())
    return matches[:3]


def _calculate_bias_scores(text: str) -> dict[str, int]:
    norm = normalize_text(text)
    employer_keywords = [
        "employer may vary",
        "may vary without compensation",
        "without cap",
        "no limitation of ld",
        "acceptance at employer discretion",
        "without reason",
        "payment withheld",
        "indefinite warranty",
        "one-sided indemnity",
        "no guarantee",
        "without compensation",
        "no cap",
        "withhold payment",
    ]
    contractor_keywords = [
        "cost adjustment",
        "extension of time",
        "eot",
        "liquidated damages cap",
        "cap on liquidated damages",
        "performance security",
        "bank guarantee",
        "arbitration",
        "dispute adjudication board",
        "testing and acceptance criteria",
        "defects notification period",
        "delay damages cap",
        "variation procedure",
    ]

    employer_score = sum(1 for kw in employer_keywords if normalize_text(kw) in norm) * 12
    contractor_score = sum(1 for kw in contractor_keywords if normalize_text(kw) in norm) * 12

    return {"employer": employer_score, "contractor": contractor_score}


def _classify_contract_balance(text: str, language: str = "ko") -> str:
    labels = _BALANCE_LABELS.get(language, _BALANCE_LABELS["ko"])
    bias_scores = _calculate_bias_scores(text)
    employer_score = bias_scores["employer"]
    contractor_score = bias_scores["contractor"]

    if employer_score - contractor_score >= 12:
        return labels["employer"]
    if contractor_score - employer_score >= 12:
        return labels["contractor"]
    return labels["neutral"]


def compare_contract_to_fidic(contract_text: str, language: str = "ko") -> dict[str, Any]:
    labels = _BALANCE_LABELS.get(language, _BALANCE_LABELS["ko"])
    text = contract_text or ""
    if not text.strip():
        empty_issues = []
        for issue in ISSUE_TEMPLATES:
            evidence = []
            empty_issues.append(
                {
                    "id": issue["id"],
                    "label": _issue_label(issue, language),
                    "score": 0,
                    "status": "risk",
                    "fidic_benchmark": _issue_benchmark(issue, language),
                    "evidence": evidence,
                    "sentence_evidence": evidence,
                    "recommendation": _issue_recommendation(issue, language),
                }
            )
        return {
            "overall_score": 0,
            "summary": _EMPTY_SUMMARY.get(language, _EMPTY_SUMMARY["ko"]),
            "issues": empty_issues,
            "focus_areas": [issue["label"] for issue in empty_issues],
            "balance": labels["neutral"],
            "bias_scores": {"employer": 0, "contractor": 0},
        }

    issues: list[dict[str, Any]] = []
    for issue in ISSUE_TEMPLATES:
        positive_matches = detect_keywords(text, issue["positive_keywords"])
        warning_matches = detect_keywords(text, issue["warning_keywords"])
        sentence_evidence = extract_sentence_evidence(text, positive_matches + warning_matches)

        score = 35
        if len(positive_matches) >= 2:
            score += 30
        elif len(positive_matches) == 1:
            score += 18
        if len(warning_matches) > 0:
            score -= len(warning_matches) * 20
        if len(positive_matches) >= 3:
            score += 10

        score = max(0, min(100, score))
        if score >= 75:
            status = "good"
        elif score >= 50:
            status = "watch"
        else:
            status = "risk"

        issue_evidence = positive_matches + warning_matches
        issues.append(
            {
                "id": issue["id"],
                "label": _issue_label(issue, language),
                "score": score,
                "status": status,
                "fidic_benchmark": _issue_benchmark(issue, language),
                "evidence": issue_evidence,
                "sentence_evidence": sentence_evidence,
                "recommendation": _issue_recommendation(issue, language),
            }
        )

    overall_score = round(sum(i["score"] for i in issues) / max(len(issues), 1))
    focus_areas = [issue["label"] for issue in issues if issue["score"] < 60][:5]
    if not focus_areas:
        if language == "en":
            summary = (
                "The current draft is well aligned with FIDIC standards. Still, reviewing the finer "
                "wording could further improve stability."
            )
        else:
            summary = "현재 문안은 FIDIC 기준에 근접하게 정리되어 있습니다. 다만 세부 문구를 점검해 안정성을 더 높이면 좋습니다."
    else:
        if language == "en":
            summary = (
                f"The current draft deviates most from FIDIC standards in: {', '.join(focus_areas)}. "
                "These should be prioritized for revision."
            )
        else:
            summary = f"현재 문안은 {', '.join(focus_areas)} 항목에서 FIDIC 기준과의 편차가 가장 큽니다. 우선순위 조정이 필요합니다."

    bias_scores = _calculate_bias_scores(text)
    balance = _classify_contract_balance(text, language=language)
    if balance == labels["employer"] and bias_scores["contractor"] > bias_scores["employer"]:
        bias_scores["contractor"] = max(0, bias_scores["contractor"] - 8)
    if balance == labels["contractor"] and bias_scores["employer"] > bias_scores["contractor"]:
        bias_scores["employer"] = max(0, bias_scores["employer"] - 8)

    return {
        "overall_score": overall_score,
        "summary": summary,
        "issues": issues,
        "focus_areas": focus_areas,
        "balance": balance,
        "bias_scores": bias_scores,
    }


_PDF_LABELS = {
    "ko": {
        "title": "FIDIC vs 사용자 계약서 비교표",
        "bias_line": "발주자 편향: {employer} | 시공사 편향: {contractor}",
        "summary_heading": "요약",
        "table_heading": "표 1. 항목별 점수",
        "table_columns": "항목 | 점수 | 상태",
        "detail_heading": "상세 항목 분석",
        "benchmark": "Benchmark",
        "evidence": "Evidence",
        "recommendation": "Recommendation",
        "default_balance": "균형형",
    },
    "en": {
        "title": "FIDIC vs User Contract Comparison Report",
        "bias_line": "Employer bias: {employer} | Contractor bias: {contractor}",
        "summary_heading": "Summary",
        "table_heading": "Table 1. Scores by Item",
        "table_columns": "Item | Score | Status",
        "detail_heading": "Detailed Item Analysis",
        "benchmark": "Benchmark",
        "evidence": "Evidence",
        "recommendation": "Recommendation",
        "default_balance": "Balanced",
    },
}


def generate_fidic_pdf_bytes(report: dict[str, Any], language: str = "ko") -> bytes:
    labels = _PDF_LABELS.get(language, _PDF_LABELS["ko"])
    issues = report.get("issues", []) or []
    bias_scores = report.get("bias_scores", {"employer": 0, "contractor": 0})
    summary_lines: list[str] = [
        labels["title"],
        "=" * 42,
        f"Overall Score: {report.get('overall_score', 0)} / 100",
        f"Balance: {report.get('balance', labels['default_balance'])}",
        labels["bias_line"].format(employer=bias_scores.get("employer", 0), contractor=bias_scores.get("contractor", 0)),
        "",
        labels["summary_heading"],
        "-" * 20,
        report.get("summary", ""),
        "",
        labels["table_heading"],
        labels["table_columns"],
        "-" * 24,
    ]

    for issue in issues:
        summary_lines.append(
            f"{issue.get('label', '')} | {issue.get('score', 0)} | {issue.get('status', 'risk')}"
        )

    summary_lines.extend(["", labels["detail_heading"], "-" * 20])
    for issue in issues:
        summary_lines.append(f"[{issue.get('label', '')}]")
        summary_lines.append(f"{labels['benchmark']}: {issue.get('fidic_benchmark', '')}")
        evidence = issue.get("sentence_evidence") or issue.get("evidence") or []
        if evidence:
            summary_lines.append(f"{labels['evidence']}: {'; '.join(evidence[:2])}")
        summary_lines.append(f"{labels['recommendation']}: {issue.get('recommendation', '')}")
        summary_lines.append("")

    content_lines = []
    page_height = 760
    y = page_height
    for line in summary_lines:
        if not line:
            y -= 18
            continue
        escaped_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"BT /F1 12 Tf 50 {y} Td ({escaped_line}) Tj ET")
        y -= 18

    content_stream = "\n".join(content_lines)
    content_stream_bytes = content_stream.encode("utf-8")

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content_stream_bytes)} >>\nstream\n{content_stream}\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n{obj}\nendobj\n".encode("utf-8"))

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("utf-8"))
    return bytes(pdf)
