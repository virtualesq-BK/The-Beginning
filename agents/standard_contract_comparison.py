"""FIDIC 외 표준계약서(대리점·OEM/ODM·라이선스) 조항 비교 엔진.

fidic_comparison.py는 FIDIC 건설계약 전용 ISSUE_TEMPLATES/키워드로
하드코딩되어 있어, 표준계약서 카탈로그(agents/standard_contract_catalog.py)에
등록된 다른 계약유형(대리점, OEM/ODM, 라이선스)은 "설명 텍스트"만 있고
사용자 초안과 조항 단위로 대조할 방법이 없었다.

이 모듈은 fidic_comparison.py의 정규화/키워드탐지/문장근거추출 로직을
재사용하면서, 계약유형별 ISSUE_TEMPLATES를 딕셔너리로 등록해 동일한
구조(overall_score/issues/balance/bias_scores)의 리포트를 생성한다.
"""

from typing import Any

from .fidic_comparison import detect_keywords, extract_sentence_evidence, normalize_text

_BALANCE_LABELS = {
    "ko": {"principal": "본사(Principal) 유리", "counterparty": "상대방(현지 파트너) 유리", "neutral": "균형형"},
    "en": {"principal": "Principal-favorable", "counterparty": "Counterparty-favorable", "neutral": "Balanced"},
}

_EMPTY_SUMMARY = {
    "ko": "계약서 내용이 비어 있습니다. 비교표를 만들려면 계약 원문이나 초안을 붙여 넣어 주세요.",
    "en": "The contract content is empty. Paste the original contract text or draft to generate a comparison table.",
}

# ---------------------------------------------------------------------------
# 계약유형별 조항 비교 템플릿.
# "principal_keywords"  = 본사(발주 측/브랜드사/라이선서 등 우위 당사자)에게 유리하게
#                          작동하는 것으로 통상 해석되는 표현
# "counterparty_keywords" = 상대방(대리점/제조사/라이선시)을 보호하는 균형 장치
# ---------------------------------------------------------------------------

ISSUE_TEMPLATES_BY_CONTRACT_TYPE: dict[str, list[dict[str, Any]]] = {
    "distributor": [
        {
            "id": "governing-law-jurisdiction",
            "label": "준거법·전속관할",
            "benchmark": "본사(Principal) 소재국법·전속관할이 일방적으로 지정되면 상대방의 방어비용이 급증함",
            "positive_keywords": ["governing law", "exclusive jurisdiction", "arbitration", "neutral forum"],
            "warning_keywords": ["sole discretion of principal", "courts of [principal's state] only"],
            "recommendation": "준거법·관할을 중립적 제3국(중재)으로 조정하거나, 최소한 상호 선택 가능한 구조로 협상하세요.",
        },
        {
            "id": "exclusivity-territory",
            "label": "독점권·구역",
            "benchmark": "독점 판매권의 구역·기간과 최소구매수량(MQ) 미달 시 해제 조건이 명확해야 함",
            "positive_keywords": ["exclusive territory", "minimum purchase quantity", "sales target", "territory"],
            "warning_keywords": ["principal may appoint other distributors at any time", "no defined territory"],
            "recommendation": "독점 구역과 최소구매수량(MQ) 기준, MQ 미달 시 유예·해제 절차를 명확히 규정하세요.",
        },
        {
            "id": "termination-compensation",
            "label": "해지·해지보상금",
            "benchmark": "해지 사유와 해지 후 재고 매입·보상금(고객基盤 형성 기여분) 처리가 규정되어야 함",
            "positive_keywords": ["termination for convenience", "termination compensation", "repurchase of inventory", "notice period"],
            "warning_keywords": ["terminate without compensation", "immediate termination without notice"],
            "recommendation": "해지 통지기간, 재고 매입 의무, 주(state)별 딜러보호법 적용 여부를 확인하고 해지보상 기준을 명시하세요.",
        },
        {
            "id": "liability-cap-indemnity",
            "label": "손해배상 상한·인뎀니티",
            "benchmark": "손해배상 상한이 제조물책임·IP침해 인뎀니티에도 기본 적용되면 상대방 보호가 사실상 무력화됨",
            "positive_keywords": ["limitation of liability", "carve-out", "indemnification", "consequential damages excluded"],
            "warning_keywords": ["unlimited indemnity", "no cap on indemnity", "distributor indemnifies principal for any claim"],
            "recommendation": "제조물책임·지재권 침해 인뎀니티는 손해배상 상한의 예외(carve-out)가 되도록 협상하세요.",
        },
    ],
    "oem_odm": [
        {
            "id": "ip-ownership-tooling",
            "label": "금형·설계자산(IP) 귀속",
            "benchmark": "Buyer 비용으로 제작한 금형·설계자산의 소유권과 반환·폐기 조건이 명확해야 함",
            "positive_keywords": ["tooling ownership", "intellectual property ownership", "design ownership", "return of tooling"],
            "warning_keywords": ["all ip vests in buyer automatically", "manufacturer waives all rights"],
            "recommendation": "Buyer 지급 금형의 소유권 귀속 시점과 계약 종료 시 반환/폐기/보관비용 부담을 명시하세요.",
        },
        {
            "id": "indemnity-mutuality",
            "label": "인뎀니티의 쌍방향성",
            "benchmark": "제조상 결함은 Manufacturer가, Buyer 제공 사양·브랜드 자료로 인한 청구는 Buyer가 각각 배상하는 쌍방향 구조가 되어야 함",
            "positive_keywords": ["mutual indemnification", "buyer-supplied specifications", "design defect", "manufacturing defect"],
            "warning_keywords": ["manufacturer indemnifies buyer for all claims", "regardless of specifications provided by buyer"],
            "recommendation": "Buyer가 제공한 사양·브랜드 자료로 인한 청구는 Buyer 책임으로 명시해 인뎀니티를 쌍방향화하세요.",
        },
        {
            "id": "liability-cap-defense-consent",
            "label": "손해배상 상한·방어권 통제",
            "benchmark": "방어비용 통제권과 화해동의(consent to settle) 조항 없이는 상한이 있어도 실효성이 낮음",
            "positive_keywords": ["limitation of liability", "consent to settle", "control of defense"],
            "warning_keywords": ["buyer may settle without manufacturer's consent", "no cap on liability"],
            "recommendation": "방어비용 통제권과 화해동의권을 확보하고, 손해배상 상한과의 관계를 명시하세요.",
        },
        {
            "id": "quality-inspection-recall",
            "label": "품질검사·리콜 비용 분담",
            "benchmark": "출하 전 검사 기준과 리콜 발생 시 비용 분담 원칙이 사전에 합의되어야 함",
            "positive_keywords": ["quality inspection", "acceptance criteria", "recall cost sharing", "root cause analysis"],
            "warning_keywords": ["manufacturer bears all recall costs regardless of cause"],
            "recommendation": "원인(설계/제조/사양) 규명 절차와 그에 따른 리콜 비용 분담 기준을 명시하세요.",
        },
    ],
    "license": [
        {
            "id": "governing-law-jurisdiction",
            "label": "준거법·전속관할",
            "benchmark": "라이선서(Licensor) 소재국법·전속관할이 일방적으로 지정되는 경우가 많으므로 균형 확인 필요",
            "positive_keywords": ["governing law", "exclusive jurisdiction", "arbitration"],
            "warning_keywords": ["sole discretion of licensor", "courts of licensor's state only"],
            "recommendation": "준거법·관할이 일방적이면 중립적 중재 조항으로 조정을 시도하세요.",
        },
        {
            "id": "liability-cap-carveout",
            "label": "손해배상 상한 예외(carve-out)",
            "benchmark": "기밀유지 위반·지재권 침해·인적손해는 통상 손해배상 상한에서 제외(carve-out)됨",
            "positive_keywords": ["limitation of liability", "carve-out", "confidentiality breach excluded", "ip infringement excluded"],
            "warning_keywords": ["cap applies to all claims without exception"],
            "recommendation": "기밀유지 위반·IP침해·인적손해가 손해배상 상한의 예외가 되도록 확인하세요.",
        },
        {
            "id": "ip-warranty-indemnity-defense",
            "label": "지재권 비침해 보증·인뎀니티 방어권",
            "benchmark": "지재권 비침해 보증과 연계된 인뎀니티에서 방어권 통제·화해동의 요건이 확보되어야 함",
            "positive_keywords": ["non-infringement warranty", "control of defense", "consent to settle"],
            "warning_keywords": ["licensee may settle without licensor's consent", "no non-infringement warranty"],
            "recommendation": "방어권 통제와 화해동의 조항을 확보하고, 비침해 보증 범위를 명확히 하세요.",
        },
        {
            "id": "royalty-audit-mfn",
            "label": "로열티 감사권·최혜조건",
            "benchmark": "로열티 정산의 감사권(audit right)과 최혜조건(MFN)이 라이선서에게 유리하게만 규정되면 라이선시 리스크 증가",
            "positive_keywords": ["audit right", "most favored", "royalty statement", "reporting period"],
            "warning_keywords": ["licensor may audit at any time without notice", "one-sided most favored clause"],
            "recommendation": "감사 통지기간·빈도 제한과, MFN 조항의 상호성 여부를 확인하세요.",
        },
    ],
}

CONTRACT_TYPE_LABELS = {
    "distributor": {"ko": "대리점·유통계약", "en": "Distributor Agreement"},
    "oem_odm": {"ko": "OEM/ODM 위탁제조계약", "en": "OEM/ODM Agreement"},
    "license": {"ko": "라이선스계약", "en": "License Agreement"},
}


def supported_contract_types() -> list[str]:
    return list(ISSUE_TEMPLATES_BY_CONTRACT_TYPE.keys())


def compare_contract_to_standard(contract_text: str, contract_type: str, language: str = "ko") -> dict[str, Any]:
    labels = _BALANCE_LABELS.get(language, _BALANCE_LABELS["ko"])
    templates = ISSUE_TEMPLATES_BY_CONTRACT_TYPE.get(contract_type)
    if templates is None:
        raise ValueError(f"unsupported contract_type: {contract_type}")

    text = contract_text or ""
    if not text.strip():
        empty_issues = [
            {
                "id": issue["id"],
                "label": issue["label"],
                "score": 0,
                "status": "risk",
                "benchmark": issue["benchmark"],
                "evidence": [],
                "sentence_evidence": [],
                "recommendation": issue["recommendation"],
            }
            for issue in templates
        ]
        return {
            "contract_type": contract_type,
            "overall_score": 0,
            "summary": _EMPTY_SUMMARY.get(language, _EMPTY_SUMMARY["ko"]),
            "issues": empty_issues,
            "focus_areas": [issue["label"] for issue in empty_issues],
            "balance": labels["neutral"],
        }

    issues: list[dict[str, Any]] = []
    for issue in templates:
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

        issues.append(
            {
                "id": issue["id"],
                "label": issue["label"],
                "score": score,
                "status": status,
                "benchmark": issue["benchmark"],
                "evidence": positive_matches + warning_matches,
                "sentence_evidence": sentence_evidence,
                "recommendation": issue["recommendation"],
            }
        )

    overall_score = round(sum(i["score"] for i in issues) / max(len(issues), 1))
    focus_areas = [issue["label"] for issue in issues if issue["score"] < 60][:5]

    contract_type_label = CONTRACT_TYPE_LABELS.get(contract_type, {}).get(language, contract_type)
    if not focus_areas:
        summary = (
            f"The current draft is well aligned with standard {contract_type_label} practice."
            if language == "en"
            else f"현재 문안은 {contract_type_label} 표준 관행에 근접하게 정리되어 있습니다."
        )
    else:
        summary = (
            f"The current draft deviates most from standard practice in: {', '.join(focus_areas)}."
            if language == "en"
            else f"현재 문안은 {', '.join(focus_areas)} 항목에서 표준 관행과의 편차가 가장 큽니다."
        )

    return {
        "contract_type": contract_type,
        "overall_score": overall_score,
        "summary": summary,
        "issues": issues,
        "focus_areas": focus_areas,
        "balance": labels["neutral"],
    }


_PDF_LABELS = {
    "ko": {
        "title_suffix": " 표준계약서 비교 리포트",
        "summary_heading": "요약",
        "table_heading": "표 1. 항목별 점수",
        "table_columns": "항목 | 점수 | 상태",
        "detail_heading": "상세 항목 분석",
        "benchmark": "Benchmark",
        "evidence": "Evidence",
        "recommendation": "Recommendation",
    },
    "en": {
        "title_suffix": " Standard Contract Comparison Report",
        "summary_heading": "Summary",
        "table_heading": "Table 1. Scores by Item",
        "table_columns": "Item | Score | Status",
        "detail_heading": "Detailed Item Analysis",
        "benchmark": "Benchmark",
        "evidence": "Evidence",
        "recommendation": "Recommendation",
    },
}


def generate_standard_pdf_bytes(report: dict[str, Any], language: str = "ko") -> bytes:
    """FIDIC 비교(fidic_comparison.generate_fidic_pdf_bytes)와 동일한 최소 PDF 생성
    방식을 재사용해, 대리점/OEM/라이선스 비교 리포트를 PDF 바이트로 직렬화한다."""
    labels = _PDF_LABELS.get(language, _PDF_LABELS["ko"])
    contract_type = report.get("contract_type", "")
    contract_type_label = CONTRACT_TYPE_LABELS.get(contract_type, {}).get(language, contract_type)
    issues = report.get("issues", []) or []

    summary_lines: list[str] = [
        f"{contract_type_label}{labels['title_suffix']}",
        "=" * 42,
        f"Overall Score: {report.get('overall_score', 0)} / 100",
        f"Balance: {report.get('balance', '')}",
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
        summary_lines.append(f"{labels['benchmark']}: {issue.get('benchmark', '')}")
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
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
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
