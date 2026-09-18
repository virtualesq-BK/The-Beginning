"""해외 건설·인프라 계약 리스크 판단 지식 모델 (Legal Decision Model).

기존 risk_rules.py는 "조항유형 -> 단순 체크리스트 질문" 플랫 구조였다.
이 모듈은 그 대신 다음 계층을 갖는 노드(RiskNode)로 리스크 지식을 표현한다.

    Contract Type -> Clause Type -> Legal Concept -> Risk Condition
        -> Business Context -> Risk Severity -> Recommended Action
        -> Negotiation Position -> Fallback Position

각 노드는 다음 필드를 갖는다 (요청된 10개 항목):
    risk_condition        위험조건
    exception_condition    예외조건
    related_clauses        관련 조항
    contractual_effect     계약상 효과
    practical_risk         실무상 위험
    negotiation_goal       협상 목표
    minimum_acceptable     최소 수용조건
    fallback_text          대체 문구
    precedents             관련 판정례/중재사례
    internal_review_note   내부 검토의견

노드는 parent_id로 서로 연결되어 Contract Knowledge Graph를 구성한다.
예: FIDIC-DELAY (Legal Concept) 아래에
    FIDIC-DELAY-EMPLOYER / CONTRACTOR / CONCURRENT / EOT / LD / NOTICE / TIME-BAR
가 자식 노드로 붙는다.

risk_rules.py의 get_rules_for()는 하위호환을 위해 이 온톨로지에서
risk_condition 문구를 뽑아 flat list로 반환하도록 재구성했다.
"""

from dataclasses import dataclass, field


@dataclass
class RiskNode:
    node_id: str
    contract_type: str
    clause_type: str
    legal_concept: str
    parent_id: str | None
    risk_condition: str
    exception_condition: str
    related_clauses: list[str]
    contractual_effect: str
    practical_risk: str
    risk_severity: str  # "low" | "medium" | "high" | "critical"
    recommended_action: str
    negotiation_goal: str
    minimum_acceptable: str
    fallback_text: str
    precedents: list[str] = field(default_factory=list)
    internal_review_note: str = ""


# ---------------------------------------------------------------------------
# FIDIC Delay 클러스터 (예시로 요청된 구조를 그대로 구현)
# Delay
#  ├─ Employer-caused Delay
#  ├─ Contractor-caused Delay
#  ├─ Concurrent Delay
#  ├─ Extension of Time (EOT)
#  ├─ Liquidated Damages (LD)
#  ├─ Notice Requirement
#  └─ Time Bar
# ---------------------------------------------------------------------------

FIDIC_DELAY_NODES: list[RiskNode] = [
    RiskNode(
        node_id="FIDIC-DELAY",
        contract_type="FIDIC/EPC",
        clause_type="지체(Delay)",
        legal_concept="Delay",
        parent_id=None,
        risk_condition="공기 지연이 발생했거나 발생할 우려가 있음",
        exception_condition="지연이 계약상 인정되는 사유(불가항력, 발주자 귀책 등)에 해당하는 경우",
        related_clauses=["FIDIC Cl.8 (Commencement, Delays and Suspension)", "FIDIC Cl.20 (Claims)"],
        contractual_effect="EOT/LD/해지 트리거 등 하위 조항의 적용 여부가 갈림",
        practical_risk="지연 원인 귀속이 불명확하면 EOT/LD 산정 전체가 분쟁화된다",
        risk_severity="high",
        recommended_action="지연 발생 시 원인(발주자/시공사/공동)을 구분하는 절차를 계약서에 명시",
        negotiation_goal="지연 원인 분류 기준과 절차를 사전에 합의",
        minimum_acceptable="최소한 지연 원인 통지·기록 의무는 상호적으로 규정",
        fallback_text="\"Any delay shall be classified as Employer Delay, Contractor Delay, or Concurrent Delay in accordance with Sub-Clause X, with each party bearing the burden of proof for delay attributed to the other.\"",
        precedents=["ICC Case (concurrent delay allocation, unpublished summary)"],
        internal_review_note="Delay 원인 분류 조항 부재는 EOT/LD 분쟁의 90% 이상 원인 (실무 경험 기반)",
    ),
    RiskNode(
        node_id="FIDIC-DELAY-EMPLOYER",
        contract_type="FIDIC/EPC",
        clause_type="지체(Delay)",
        legal_concept="Employer-caused Delay",
        parent_id="FIDIC-DELAY",
        risk_condition="발주자 귀책 지연(도면 미제공, 부지 미인도 등)에 대한 EOT/비용보전 조항이 없거나 좁음",
        exception_condition="발주자 귀책이라도 시공사가 통지의무(Notice)를 이행하지 않은 경우 구제 제한 가능",
        related_clauses=["FIDIC Cl.8.5 (Extension of Time)", "FIDIC Cl.2.1 (Right of Access to Site)"],
        contractual_effect="발주자 귀책 지연에 대한 EOT+비용 보전이 배제되면 시공사에 리스크가 전가됨",
        practical_risk="부지 인도 지연, 설계 변경 등 발주자 귀책 사유가 실무상 가장 빈번한 분쟁 원인",
        risk_severity="high",
        recommended_action="발주자 귀책 지연 사유를 예시적으로 열거하고 EOT+Cost 보전을 명시",
        negotiation_goal="발주자 귀책 지연 사유 리스트 확대 및 비용보전 포함",
        minimum_acceptable="최소한 EOT는 인정하고 Cost는 별도 협상 대상으로",
        fallback_text="\"In case of Employer Delay, the Contractor shall be entitled to an extension of time and, to the extent such delay causes additional Cost, to reimbursement of such Cost.\"",
        internal_review_note="EOT만 인정하고 Cost 보전이 없는 조항은 발주자 우호적 초안의 전형적 패턴",
    ),
    RiskNode(
        node_id="FIDIC-DELAY-CONTRACTOR",
        contract_type="FIDIC/EPC",
        clause_type="지체(Delay)",
        legal_concept="Contractor-caused Delay",
        parent_id="FIDIC-DELAY",
        risk_condition="시공사 귀책 지연 시 LD 외에 추가 손해배상이 중복 청구 가능한 구조",
        exception_condition="LD가 sole and exclusive remedy로 명시된 경우 중복청구 배제",
        related_clauses=["FIDIC Cl.8.7 (Delay Damages)"],
        contractual_effect="LD와 일반손해배상이 중복되면 시공사 책임이 무제한으로 확대될 위험",
        practical_risk="LD 산정 기준과 별개로 발주자가 추가 클레임을 제기하는 실무 사례 다수",
        risk_severity="high",
        recommended_action="LD를 sole and exclusive remedy로 명시",
        negotiation_goal="LD 외 손해배상 청구 배제 조항 확보",
        minimum_acceptable="최소한 고의/중과실 제외한 통상 지연에 대해서는 LD가 유일한 구제수단",
        fallback_text="\"Delay Damages under this Sub-Clause shall be the Contractor's sole and exclusive liability for delay, save in cases of fraud, gross negligence, deliberate default or reckless misconduct.\"",
        internal_review_note="LD cap과 무관하게 이 조항 부재 시 실질적으로 무제한 책임이 될 수 있음",
    ),
    RiskNode(
        node_id="FIDIC-DELAY-CONCURRENT",
        contract_type="FIDIC/EPC",
        clause_type="지체(Delay)",
        legal_concept="Concurrent Delay",
        parent_id="FIDIC-DELAY",
        risk_condition="동시지연(Concurrent Delay) 처리 기준이 계약서에 없음",
        exception_condition="영미법계 판례(Malmaison 등) 원칙을 참조 조항으로 명시한 경우 예측 가능성 상승",
        related_clauses=["FIDIC Cl.8.5", "FIDIC Cl.20.2"],
        contractual_effect="동시지연 처리 기준 부재 시 EOT/LD 산정이 전적으로 분쟁화됨",
        practical_risk="국제 프로젝트에서 동시지연은 흔하며, 기준 부재는 분쟁 장기화의 핵심 원인",
        risk_severity="medium",
        recommended_action="동시지연 발생 시 EOT는 인정, Cost는 각자 부담하는 원칙(Malmaison 방식) 명시",
        negotiation_goal="예측 가능한 동시지연 처리 원칙 사전 합의",
        minimum_acceptable="최소한 EOT 산정 방식만이라도 명시",
        fallback_text="\"Where Contractor Delay and Employer Delay occur concurrently, the Contractor shall be entitled to an extension of time but not to additional Cost in respect of the period of concurrency.\"",
        precedents=["Malmaison approach (Henry Boot Construction v Malmaison Hotel, 1999)"],
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-DELAY-EOT",
        contract_type="FIDIC/EPC",
        clause_type="지체(Delay)",
        legal_concept="Extension of Time (EOT)",
        parent_id="FIDIC-DELAY",
        risk_condition="EOT 인정조건이 좁게 열거되어 있거나(exhaustive list), 발주자 단독 판단에 맡겨짐",
        exception_condition="Engineer/발주자의 판단에 이의제기(Dispute) 절차가 별도로 보장된 경우 일부 완화",
        related_clauses=["FIDIC Cl.8.5", "FIDIC Cl.20.2 (Claims for EOT)"],
        contractual_effect="EOT 불인정 시 동일 지연에 대해 LD가 즉시 발생 -> 이중 리스크",
        practical_risk="EOT가 좁으면 LD/Time Bar와 결합해 위험도가 기하급수적으로 상승 (본문 예시 참조)",
        risk_severity="critical",
        recommended_action="EOT 인정사유를 비열거적(non-exhaustive)으로 규정하고 판단 절차에 이의제기권 부여",
        negotiation_goal="EOT 인정범위 확대 + 판단 절차의 중립성 확보",
        minimum_acceptable="최소한 대표적 사유(불가항력, 발주자귀책, 변경지시) 포함 + 이의제기 경로",
        fallback_text="\"The Contractor shall be entitled to an extension of time for any cause of delay which is beyond its reasonable control, listed causes being illustrative and not exhaustive.\"",
        internal_review_note="EOT 조항은 단독으로 보면 위험도가 낮아 보이지만 LD/Notice/Time Bar와 결합 시 최우선 검토 대상",
    ),
    RiskNode(
        node_id="FIDIC-DELAY-LD",
        contract_type="FIDIC/EPC",
        clause_type="지체(Delay)",
        legal_concept="Liquidated Damages (LD)",
        parent_id="FIDIC-DELAY",
        risk_condition="LD 상한(cap)이 계약금액의 10%를 초과하거나 상한이 없음",
        exception_condition="Liability Cap 조항에서 LD를 별도 예외(carve-out)로 제외해 실질 상한이 있는 경우",
        related_clauses=["FIDIC Cl.8.7", "Liability Cap 조항"],
        contractual_effect="LD가 Liability Cap의 carve-out(예외)로 빠져 있으면 LD는 실질적으로 무제한",
        practical_risk="LD 10%만 보고 '위험'으로 단정하면 안 됨 - Liability Cap과의 관계를 반드시 함께 검토",
        risk_severity="critical",
        recommended_action="LD를 Liability Cap 내에 포함시키거나, 별도 sub-cap을 명확히 규정",
        negotiation_goal="LD와 Liability Cap의 관계를 명시적으로 정리",
        minimum_acceptable="최소한 LD와 총 책임한도의 합이 계약금액을 초과하지 않도록",
        fallback_text="\"The aggregate liability of the Contractor for Delay Damages under this Sub-Clause shall be included within, and not in addition to, the overall limitation of liability under Sub-Clause Y.\"",
        internal_review_note="LD 단독 %는 진입점일 뿐, 실제 위험도는 EOT+Notice+LiabilityCap+Termination과의 조합에서 결정됨",
    ),
    RiskNode(
        node_id="FIDIC-DELAY-NOTICE",
        contract_type="FIDIC/EPC",
        clause_type="지체(Delay)",
        legal_concept="Notice Requirement",
        parent_id="FIDIC-DELAY",
        risk_condition="지연 통지 기한이 7일 이하로 짧고, 미준수 시 권리 상실(Time Bar) 규정과 연결됨",
        exception_condition="통지기한 미준수에도 발주자가 실질적 불이익을 입지 않았음을 시공사가 증명하면 구제되는 조항이 있는 경우",
        related_clauses=["FIDIC Cl.20.2.1 (Notice of Claim)"],
        contractual_effect="Notice 기한 미준수 -> Time Bar 발동 -> EOT/Cost 청구권 완전 상실",
        practical_risk="Notice 조항은 그 자체로는 위험해 보이지 않지만 Time Bar와 결합되는 순간 치명적",
        risk_severity="critical",
        recommended_action="통지기한을 14~28일로 연장하고, 미준수 시 완전 실권이 아닌 감액/증명책임 전환으로 완화",
        negotiation_goal="Notice 기간 7일 -> 14~21일 확대",
        minimum_acceptable="최소 14일 + 실권이 아닌 구제 경로 확보",
        fallback_text="\"Failure to give notice within the period stated shall not bar the Contractor's entitlement, but may be taken into account in assessing the Employer's actual prejudice.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-DELAY-TIMEBAR",
        contract_type="FIDIC/EPC",
        clause_type="지체(Delay)",
        legal_concept="Time Bar",
        parent_id="FIDIC-DELAY",
        risk_condition="Time Bar 조항이 Notice 기한 미준수 시 청구권을 완전히(absolute) 소멸시킴",
        exception_condition="영국법 등 일부 법역에서는 penalty 원칙 등으로 완전 실권 조항이 무효화될 여지가 있음 (준거법에 따라 다름)",
        related_clauses=["FIDIC Cl.20.2.1", "준거법 조항"],
        contractual_effect="EOT/LD/Notice가 모두 정상이어도 Time Bar 하나로 전체 방어권이 무력화될 수 있음",
        practical_risk="Time Bar는 계약 전체 리스크 구조의 '단일 실패점(single point of failure)'이 되는 경우가 많음",
        risk_severity="critical",
        recommended_action="완전 실권이 아닌 '증명책임 전환' 또는 '통지 지연에 비례한 감액'으로 완화",
        negotiation_goal="Time Bar를 절대적 실권 조항에서 상대적 구제 조항으로 전환",
        minimum_acceptable="최소한 불가항력/발주자 귀책 사유에는 Time Bar 미적용",
        fallback_text="\"The time bar in this Sub-Clause shall not apply to delay caused by Force Majeure or Employer Delay.\"",
        precedents=["Obrascon Huarte Lain v Gibraltar (2014) EWHC — FIDIC time-bar 해석"],
        internal_review_note="Time Bar는 반드시 EOT/Notice와 묶어서(cross-clause) 평가해야 하며 단독 조항 평가는 무의미",
    ),
]

# ---------------------------------------------------------------------------
# 나머지 조항유형 (risk_rules.py의 기존 MVP 시드 세트를 온톨로지로 이전).
# Delay 클러스터처럼 세부 하위노드까지는 아직 필요치 않아 조항유형당 1개
# Legal Concept 노드로 표현한다. 필요 시 Delay 클러스터처럼 세분화한다.
# ---------------------------------------------------------------------------

OTHER_NODES: list[RiskNode] = [
    RiskNode(
        node_id="FIDIC-INDEMNITY",
        contract_type="FIDIC/EPC",
        clause_type="면책(Indemnity)",
        legal_concept="Indemnity",
        parent_id=None,
        risk_condition="발주자 면책 범위가 일방적으로 넓고, 고의/중과실에 대한 면책 배제가 없음",
        exception_condition="면책 조항에 고의·중과실·지적재산권 침해·기밀유지 위반이 명시적으로 제외된 경우",
        related_clauses=["Indemnity 조항", "Liability Cap 조항"],
        contractual_effect="고의·중과실까지 면책되면 다수 법역에서 공서양속 위반으로 무효화될 위험 및 시공사 보호장치 상실",
        practical_risk="면책 범위가 넓을수록 Liability Cap과 결합해 시공사의 실질 방어권이 사라짐",
        risk_severity="high",
        recommended_action="고의·중과실·IP침해·기밀유지 위반을 면책 예외로 명시",
        negotiation_goal="면책 예외 항목 명문화",
        minimum_acceptable="최소한 고의·중과실은 면책 예외로 확보",
        fallback_text="\"The indemnity under this Clause shall not apply to loss or damage caused by the indemnified party's fraud, gross negligence or wilful misconduct.\"",
        internal_review_note="Liability Cap과 반드시 함께 검토 (FIDIC-LD의 carve-out 논리와 동일 구조)",
    ),
    RiskNode(
        node_id="FIDIC-ARBITRATION",
        contract_type="FIDIC/EPC",
        clause_type="중재(Arbitration)",
        legal_concept="Dispute Resolution",
        parent_id=None,
        risk_condition="중재지가 일방 당사자에게 현저히 불리하거나, 중재기관/준거법/언어가 불명확함",
        exception_condition="중립적 제3국(싱가포르/런던/파리 등)과 ICC/SIAC/HKIAC 등 국제기관이 명시된 경우",
        related_clauses=["FIDIC Cl.21 (Disputes and Arbitration)"],
        contractual_effect="중재지·기관·준거법 불명확 시 분쟁 발생 단계에서 절차적 다툼(procedural dispute)부터 시작",
        practical_risk="본안 분쟁 전에 관할 다툼만으로 수개월~수년이 소요될 수 있음",
        risk_severity="high",
        recommended_action="중재기관, 중재지, 준거법, 언어를 명시하고 DAB/조정 절차를 전치 절차로 추가",
        negotiation_goal="제3국 중재지 + 국제 중재기관 확보",
        minimum_acceptable="최소한 준거법과 중재기관만이라도 명확히 특정",
        fallback_text="\"Any dispute shall be finally settled by arbitration under the ICC Rules, seated in Singapore, in the English language, governed by the laws of England and Wales.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-DLP",
        contract_type="FIDIC/EPC",
        clause_type="하자담보(DLP)",
        legal_concept="Defects Liability Period",
        parent_id=None,
        risk_condition="하자담보책임기간(DLP)이 업계 관행(통상 12~24개월) 대비 과도하게 길거나, 통지기한이 지나치게 짧음",
        exception_condition="대형 플랜트 등 특수 프로젝트 특성상 연장에 합리적 근거가 있는 경우",
        related_clauses=["FIDIC Cl.11 (Defects Liability)"],
        contractual_effect="DLP 과도 연장은 시공사의 장기 재무 리스크(보증금 미회수 등)로 직결",
        practical_risk="36개월 이상 DLP는 실무상 비정상적으로 길어 보증금 반환 지연의 주 원인",
        risk_severity="medium",
        recommended_action="DLP를 12~24개월로 조정하고, 통지기한을 합리적 수준(최소 14일)으로 확보",
        negotiation_goal="DLP 단축 및 통지기한 확대",
        minimum_acceptable="최소 12개월 이상은 수용, 24개월 초과는 근거 요구",
        fallback_text="\"The Defects Notification Period shall be twelve (12) months from the date of taking-over, subject to a maximum aggregate extension of twelve (12) additional months.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-CHANGE-ORDER",
        contract_type="FIDIC/EPC",
        clause_type="변경명령(Change Order)",
        legal_concept="Change Order",
        parent_id=None,
        risk_condition="발주자의 일방적 변경 지시권이 대금/공기 조정 없이 인정됨",
        exception_condition="변경 규모가 사전 합의된 경미한(de minimis) 범위인 경우",
        related_clauses=["FIDIC Cl.13 (Variations and Adjustments)"],
        contractual_effect="조정 없는 일방적 변경권은 FIDIC-DELAY-EOT/LD와 결합해 이중 리스크 유발",
        practical_risk="변경지시가 EOT/비용조정과 연결되지 않으면 클레임 제기 시점이 항상 사후적으로 밀림",
        risk_severity="high",
        recommended_action="변경지시-EOT-비용조정-클레임 절차를 하나의 흐름으로 연결",
        negotiation_goal="변경지시 시 EOT/비용조정 자동 연계 확보",
        minimum_acceptable="최소한 일정 규모 이상 변경에 대해서는 조정 절차 보장",
        fallback_text="\"Any Variation instructed by the Employer shall entitle the Contractor to an appropriate adjustment of the Time for Completion and the Contract Price.\"",
        internal_review_note="FIDIC-DELAY-EOT 노드와 cross-reference 필요",
    ),
    RiskNode(
        node_id="FIDIC-FORCE-MAJEURE",
        contract_type="FIDIC/EPC",
        clause_type="불가항력(Force Majeure)",
        legal_concept="Force Majeure",
        parent_id=None,
        risk_condition="불가항력 사유가 지나치게 좁게 열거되어 있고, 발생 시 공기연장만 인정되며 비용 보전은 배제됨",
        exception_condition="비용 보전이 배제되어도 EOT만으로 충분한 소규모 지연인 경우 영향 제한적",
        related_clauses=["FIDIC Cl.18/19 (Force Majeure / Exceptional Events)"],
        contractual_effect="좁은 불가항력 정의는 실제 재난·정부조치 상황에서 구제수단을 무력화",
        practical_risk="팬데믹, 전쟁, 수출제한 등 최근 사례에서 열거식 정의의 공백이 반복적으로 문제됨",
        risk_severity="medium",
        recommended_action="불가항력 사유를 비열거적으로 규정하고 합리적 비용 보전을 포함",
        negotiation_goal="불가항력 범위 확대 + 비용 보전 포함",
        minimum_acceptable="최소한 EOT는 확보, 비용은 일부라도 보전",
        fallback_text="\"An Exceptional Event includes, without limitation, the events listed below, and shall entitle the Contractor to an extension of time and reimbursement of reasonable Cost incurred.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-TERMINATION",
        contract_type="FIDIC/EPC",
        clause_type="계약해지(Termination)",
        legal_concept="Termination",
        parent_id=None,
        risk_condition="발주자 임의해지(termination for convenience) 시 보상범위가 과소하거나, 시공사 귀책 해지사유가 모호함",
        exception_condition="임의해지 보상에 일실이익 일부(5~15%)가 포함된 경우 국제관행에 부합",
        related_clauses=["FIDIC Cl.15/16 (Termination by Employer/Contractor)"],
        contractual_effect="모호한 해지사유는 발주자가 실질적으로 언제든 '귀책해지'를 주장할 수 있는 트리거가 됨",
        practical_risk="해지 트리거가 LD/Liability Cap과 결합하면 해지 직전 지연 하나로 전체 계약이 붕괴 가능",
        risk_severity="critical",
        recommended_action="해지사유를 구체적 수치·기간으로 명시하고 임의해지 보상범위를 국제관행 수준으로 확보",
        negotiation_goal="해지 트리거 명확화 + 임의해지 보상 확대",
        minimum_acceptable="최소한 기시공 대금+자재비는 확보, 일실이익 일부 협상",
        fallback_text="\"Upon termination for the Employer's convenience, the Contractor shall be paid for Works executed, materials ordered, and a sum equal to 10% of the value of the unperformed Works.\"",
        internal_review_note="FIDIC-DELAY-LD, FIDIC-DELAY-TIMEBAR와 반드시 함께 검토 (해지 트리거 조합 위험)",
    ),
    RiskNode(
        node_id="FIDIC-PERFORMANCE-SECURITY",
        contract_type="FIDIC/EPC",
        clause_type="성능보증",
        legal_concept="Performance Security",
        parent_id=None,
        risk_condition="성능보증 기준이 객관적 수치·테스트 절차 없이 추상적으로 규정됨",
        exception_condition="성능시험(Performance Test) 절차와 수치 기준이 별도 부속서로 명시된 경우",
        related_clauses=["FIDIC Cl.4.2 (Performance Security)", "Performance Test 부속서"],
        contractual_effect="추상적 성능보증 기준은 미달 판정 자체가 분쟁화됨",
        practical_risk="테스트 절차 없이는 '성능 미달'의 존재 여부부터 다툼의 대상이 됨",
        risk_severity="medium",
        recommended_action="객관적 수치 기준과 테스트 절차를 부속서로 명시",
        negotiation_goal="측정 가능한 성능 기준 확보",
        minimum_acceptable="최소한 핵심 성능지표(capacity, efficiency 등) 수치화",
        fallback_text="\"Performance shall be verified by the Performance Tests set out in Schedule X, using the acceptance criteria specified therein.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-PAYMENT-ACCEPTANCE",
        contract_type="FIDIC/EPC",
        clause_type="지급·인도",
        legal_concept="Payment and Acceptance",
        parent_id=None,
        risk_condition="중도금 지급 인증이 발주자 단독 판단에 맡겨져 있고, 지급 보류 사유가 과도하게 넓음",
        exception_condition="지급 보류 사유가 구체적으로 열거되고 보류액이 다툼 있는 부분에 한정된 경우",
        related_clauses=["FIDIC Cl.14 (Contract Price and Payment)"],
        contractual_effect="지급 보류 범위가 넓으면 시공사 현금흐름이 발주자의 재량에 종속됨",
        practical_risk="현금흐름 훼손은 실무상 시공사 부도로 이어지는 가장 직접적인 경로",
        risk_severity="high",
        recommended_action="지급 보류 사유를 구체적으로 열거하고 다툼 있는 부분에만 보류 한정",
        negotiation_goal="지급 보류 사유 구체화 + 보류 범위 제한",
        minimum_acceptable="최소한 보류는 다툼 있는 금액에 한정, 통지의무 부과",
        fallback_text="\"The Employer may withhold payment only in respect of the specific disputed amount, and shall notify the Contractor of the grounds within 7 days.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-GUARANTEE-INSURANCE",
        contract_type="FIDIC/EPC",
        clause_type="보증·보험",
        legal_concept="Guarantee and Insurance",
        parent_id=None,
        risk_condition="이행보증·보험 가입범위가 프로젝트 위험을 충분히 커버하지 못하거나, 보증금/보험금/책임한도 관계가 불명확함",
        exception_condition="보증금·보험금·Liability Cap 간 관계가 별도 조항으로 명시적으로 정리된 경우",
        related_clauses=["FIDIC Cl.4.2 (Performance Security)", "FIDIC Cl.19 (Insurance)"],
        contractual_effect="세 항목의 관계가 불명확하면 실제 손해 발생 시 어느 재원에서 우선 충당되는지가 다툼거리가 됨",
        practical_risk="보증/보험/책임한도가 개별적으로는 적정해도 상호관계가 불명확하면 실제 회수 단계에서 공백 발생",
        risk_severity="medium",
        recommended_action="보증금, 보험금, 책임한도 간 우선순위와 상호관계를 명시",
        negotiation_goal="보증·보험·책임한도 관계 명문화",
        minimum_acceptable="최소한 보험 우선 충당 원칙만이라도 명시",
        fallback_text="\"Insurance proceeds shall be applied first, with any shortfall subject to the Performance Security, both within the overall Limitation of Liability under Sub-Clause Y.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-VARIATION-SCOPE",
        contract_type="FIDIC/EPC",
        clause_type="공사변경",
        legal_concept="Variation Scope",
        parent_id=None,
        risk_condition="변경사항 승인절차가 발주자 일방적 판단으로 단순화되어 있고, 추가범위와 기존범위의 경계가 모호함",
        exception_condition="Scope of Work가 부속서로 상세히 정의되어 추가범위 판단 기준이 명확한 경우",
        related_clauses=["FIDIC Cl.13", "Scope of Work 부속서"],
        contractual_effect="범위 경계가 모호하면 모든 추가작업이 '기존범위 내 작업'으로 재해석될 위험",
        practical_risk="Scope 다툼은 Change Order/EOT 클레임의 선결 쟁점이 되어 전체 클레임을 지연시킴",
        risk_severity="medium",
        recommended_action="Scope of Work를 상세 부속서로 정의하고 추가범위 판단기준을 명시",
        negotiation_goal="Scope 경계 명확화",
        minimum_acceptable="최소한 핵심 인도물(deliverables) 기준으로 경계 설정",
        fallback_text="\"Any work not expressly included in the Scope of Work set out in Schedule X shall be deemed a Variation.\"",
        internal_review_note="FIDIC-CHANGE-ORDER와 실질적으로 동일 리스크 계열이므로 함께 검토",
    ),
]

_ALL_NODES: dict[str, RiskNode] = {n.node_id: n for n in FIDIC_DELAY_NODES + OTHER_NODES}

# risk_rules.py / 사용자 입력에서 쓰이는 조항유형 라벨을 온톨로지 clause_type에 매핑.
# 계약서 파서가 "지체상금", "공기 지연" 등 다양한 표현을 뽑아내므로, 실제 온톨로지
# 노드의 clause_type("지체(Delay)")과 다른 표현도 여기서 묶어준다.
_CLAUSE_TYPE_ALIASES: dict[str, str] = {
    "지체상금": "지체(Delay)",
    "지체": "지체(Delay)",
    "공기지연": "지체(Delay)",
    "공기 지연": "지체(Delay)",
    "delay": "지체(Delay)",
    "delay damages": "지체(Delay)",
    "liquidated damages": "지체(Delay)",
    "면책": "면책(Indemnity)",
    "indemnity": "면책(Indemnity)",
    "중재": "중재(Arbitration)",
    "arbitration": "중재(Arbitration)",
    "분쟁해결": "중재(Arbitration)",
    "하자담보": "하자담보(DLP)",
    "dlp": "하자담보(DLP)",
    "defects liability": "하자담보(DLP)",
    "변경명령(change order)": "변경명령(Change Order)",
    "변경명령": "변경명령(Change Order)",
    "change order": "변경명령(Change Order)",
    "불가항력": "불가항력(Force Majeure)",
    "force majeure": "불가항력(Force Majeure)",
    "계약해지": "계약해지(Termination)",
    "termination": "계약해지(Termination)",
    "성능보증": "성능보증",
    "지급·인도": "지급·인도",
    "지급인도": "지급·인도",
    "payment and acceptance": "지급·인도",
    "보증·보험": "보증·보험",
    "보증보험": "보증·보험",
    "guarantee and insurance": "보증·보험",
    "공사변경": "공사변경",
    "variation": "공사변경",
}


def get_node(node_id: str) -> RiskNode | None:
    return _ALL_NODES.get(node_id)


def get_children(node_id: str) -> list[RiskNode]:
    return [n for n in _ALL_NODES.values() if n.parent_id == node_id]


def get_cluster(legal_concept: str) -> list[RiskNode]:
    """조항유형(legal_concept)으로 관련 노드 트리를 찾는다 (본인 + 자식들)."""
    root = next((n for n in _ALL_NODES.values() if n.legal_concept == legal_concept), None)
    if root is None:
        return []
    return [root] + get_children(root.node_id)


def get_nodes_for_clause_type(clause_type: str) -> list[RiskNode]:
    normalized = clause_type.strip().lower()
    normalized = _CLAUSE_TYPE_ALIASES.get(normalized, normalized).lower()
    return [
        n
        for n in _ALL_NODES.values()
        if n.clause_type.lower() == normalized or normalized in n.clause_type.lower()
    ]


def all_nodes() -> list[RiskNode]:
    return list(_ALL_NODES.values())


# ---------------------------------------------------------------------------
# Cross-Clause Risk Combination
#
# 계약의 진짜 위험은 개별 조항이 아니라 조항 간 상호작용에서 발생한다.
# 예: LD가 10%라서 위험한 게 아니라, "EOT 인정조건이 좁음 + Notice 7일
# Time Bar + LD 10% + Liability Cap에 LD 제외 + Termination Trigger 존재"
# 가 동시에 성립할 때 완전히 다른(더 높은) 위험도가 된다.
#
# RiskCombination은 여러 조항(rule_id)이 함께 발견되었을 때만 발동하는
# 상위 판단이다. 개별 조항 분석(risk_analyzer.analyze_clause)이 끝난 뒤,
# 문서 전체 수준에서 rules_applied 합집합을 이 함수에 넣어 평가한다.
# ---------------------------------------------------------------------------


@dataclass
class RiskCombination:
    combo_id: str
    required_node_ids: list[str]
    description: str
    combined_severity: str  # "high" | "critical"
    business_impact: str
    negotiation_priority: str


RISK_COMBINATIONS: list[RiskCombination] = [
    RiskCombination(
        combo_id="COMBO-EOT-NOTICE-LD-CAP-TERMINATION",
        required_node_ids=[
            "FIDIC-DELAY-EOT",
            "FIDIC-DELAY-NOTICE",
            "FIDIC-DELAY-LD",
        ],
        description=(
            "EOT 인정조건이 좁고, Notice 기한이 짧아 Time Bar 위험이 있으며, "
            "LD 상한이 높다는 3가지 조항이 동시에 발견됨. 개별적으로는 "
            "'검토 필요' 수준이라도, 함께 있으면 시공사는 지연 발생 시 "
            "(1) EOT를 인정받지 못하고 (2) Notice 기한을 놓쳐 청구권을 "
            "잃고 (3) 그 결과 LD가 상한까지 그대로 부과되는 연쇄 구조에 놓인다."
        ),
        combined_severity="critical",
        business_impact="지연 1회 발생 시 EOT 불인정 -> Time Bar로 항변권 상실 -> LD 상한 전액 부과까지 단일 사건으로 연결될 수 있음",
        negotiation_priority="EOT 범위 확대와 Notice 기한 연장을 LD 협상보다 먼저 확보해야 함 (LD cap을 낮춰도 이 조합이 남아있으면 리스크가 해소되지 않음)",
    ),
    RiskCombination(
        combo_id="COMBO-LD-INDEMNITY-TERMINATION",
        required_node_ids=[
            "FIDIC-DELAY-LD",
            "FIDIC-INDEMNITY",
            "FIDIC-TERMINATION",
        ],
        description=(
            "LD 상한이 높고, 면책 예외(고의/중과실)가 없으며, 해지 트리거가 "
            "모호한 3개 조항이 동시에 존재. 지연으로 인한 해지 상황에서 "
            "LD와 손해배상이 중첩 청구되고 면책으로도 방어되지 않는 구조."
        ),
        combined_severity="critical",
        business_impact="해지 시점에 LD 미지급분 + 일반손해배상 + 면책 배제로 인한 추가청구가 동시에 발생할 수 있음",
        negotiation_priority="LD를 sole and exclusive remedy로 명시하고, 면책 예외를 좁혀 해지 시나리오에서의 중첩청구를 차단",
    ),
    RiskCombination(
        combo_id="COMBO-CHANGEORDER-VARIATION-EOT",
        required_node_ids=[
            "FIDIC-CHANGE-ORDER",
            "FIDIC-VARIATION-SCOPE",
            "FIDIC-DELAY-EOT",
        ],
        description=(
            "변경지시권이 조정 없이 인정되고, Scope 경계가 모호하며, EOT "
            "인정조건이 좁은 조합. 발주자가 '기존 범위 내 작업'이라고 "
            "주장하며 무상 변경을 요구해도 시공사는 EOT/비용조정을 받기 "
            "어렵다."
        ),
        combined_severity="high",
        business_impact="사실상 무제한적인 무상 변경 요구에 노출되어 공정·비용 관리가 불가능해질 위험",
        negotiation_priority="Scope of Work 상세 부속서 확보를 최우선으로, 이후 변경지시-EOT 연계 조항 확보",
    ),
]


def evaluate_cross_clause_risks(rule_ids_present: set[str] | list[str]) -> list[dict]:
    """문서 전체에서 발견된 rule_id 집합을 받아, 함께 존재할 때만 위험한
    조항 조합(RiskCombination)을 탐지한다.

    개별 조항 분석(analyze_clause)은 조항 하나만 보기 때문에 이 상호작용을
    잡을 수 없다. pipeline.py에서 모든 clause의 risk["rules_applied"]를
    모아 이 함수에 넘기면, 문서 수준의 "조합 위험" 목록을 얻는다.
    """
    present = set(rule_ids_present)
    matches: list[dict] = []
    for combo in RISK_COMBINATIONS:
        if all(rid in present for rid in combo.required_node_ids):
            matches.append(
                {
                    "combo_id": combo.combo_id,
                    "matched_rules": combo.required_node_ids,
                    "description": combo.description,
                    "combined_severity": combo.combined_severity,
                    "business_impact": combo.business_impact,
                    "negotiation_priority": combo.negotiation_priority,
                }
            )
    return matches
