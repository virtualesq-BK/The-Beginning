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

import re
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
        node_id="FIDIC-INDEMNITY-WILLFUL",
        contract_type="FIDIC/EPC",
        clause_type="면책(Indemnity)",
        legal_concept="Wilful Misconduct / Gross Negligence Carve-out",
        parent_id="FIDIC-INDEMNITY",
        risk_condition="고의 또는 중과실로 인한 손해까지 면책 대상에 포함되어 있음",
        exception_condition="고의·중과실이 면책 예외(carve-out)로 명시되고, Liability Cap의 예외로도 연결된 경우",
        related_clauses=["Indemnity 조항", "Liability Cap 조항"],
        contractual_effect="고의·중과실 면책은 다수 법역(영미법·대륙법 공통)에서 공서양속 위반으로 무효 소지가 있으나, 무효 여부를 다투는 것 자체가 분쟁 비용",
        practical_risk="상대방이 실제로 고의·중과실 항변을 방어 논리로 활용해도 조항상 면책 범위가 넓으면 협상력이 약화됨",
        risk_severity="high",
        recommended_action="고의·중과실을 면책 및 책임한도 모두에서 carve-out으로 명시",
        negotiation_goal="고의·중과실 carve-out을 면책과 Liability Cap에 동시 반영",
        minimum_acceptable="최소한 면책 조항에서만이라도 고의·중과실 제외",
        fallback_text="\"Nothing in this Agreement shall exclude or limit either party's liability for its own fraud, gross negligence or wilful misconduct.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-INDEMNITY-IP",
        contract_type="FIDIC/EPC",
        clause_type="면책(Indemnity)",
        legal_concept="Third-Party IP Infringement Indemnity",
        parent_id="FIDIC-INDEMNITY",
        risk_condition="제3자 지식재산권 침해에 대한 면책 의무가 일방(주로 시공사/공급자)에게만 부과되고, 방어권 통제·화해동의(consent to settle) 조항이 없음",
        exception_condition="발주자가 제공한 사양·설계·자재로 인한 침해는 발주자 책임으로 명시된 경우",
        related_clauses=["IP Indemnity 조항", "설계책임 조항"],
        contractual_effect="방어권 통제 조항이 없으면 피면책자가 임의로 화해해도 면책의무자가 그 금액을 그대로 부담해야 할 위험",
        practical_risk="발주자 지정 사양을 그대로 구현했는데도 침해책임 전부를 시공사가 지는 사례가 실무상 빈번",
        risk_severity="high",
        recommended_action="발주자 제공 사양으로 인한 침해는 발주자 책임으로 분리하고, 방어권 통제·화해동의 절차를 명시",
        negotiation_goal="IP 침해 인덤니티의 쌍방향화 및 방어권 통제 확보",
        minimum_acceptable="최소한 방어비용 통제권과 화해동의권만이라도 확보",
        fallback_text="\"The indemnifying party shall have the right to control the defense and settlement of any claim, and shall not settle without the indemnified party's consent where such settlement imposes any obligation on the indemnified party.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-INDEMNITY-CONFIDENTIALITY",
        contract_type="FIDIC/EPC",
        clause_type="면책(Indemnity)",
        legal_concept="Confidentiality Breach Indemnity",
        parent_id="FIDIC-INDEMNITY",
        risk_condition="기밀유지 위반에 대한 손해배상이 일반 Liability Cap 안에 포함되어 실효성이 없음",
        exception_condition="기밀유지 위반이 Liability Cap의 예외(carve-out)로 명시된 경우",
        related_clauses=["Confidentiality 조항", "Liability Cap 조항"],
        contractual_effect="영업비밀·기술정보 유출은 금전배상만으로 회복 불가능한 손해인데, 낮은 Cap 안에 갇히면 억지력이 없음",
        practical_risk="설계도면·공정기술 등 핵심 영업비밀이 걸린 계약에서 특히 치명적",
        risk_severity="medium",
        recommended_action="기밀유지 위반을 Liability Cap의 예외로 하고, 금지명령(injunctive relief) 구제수단을 별도로 명시",
        negotiation_goal="기밀유지 위반 손해배상의 Cap 예외화 + 금지명령 구제 확보",
        minimum_acceptable="최소한 금지명령 구제만이라도 명시",
        fallback_text="\"Each party acknowledges that breach of confidentiality may cause irreparable harm and that the other party shall be entitled to seek injunctive relief in addition to damages, which shall not be subject to the Limitation of Liability under Sub-Clause Y.\"",
        internal_review_note="",
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
        node_id="FIDIC-FM-DEFINITION",
        contract_type="FIDIC/EPC",
        clause_type="불가항력(Force Majeure)",
        legal_concept="Force Majeure Definition Scope",
        parent_id="FIDIC-FORCE-MAJEURE",
        risk_condition="불가항력 사유가 열거식(exhaustive list)으로 한정되어 있어 목록에 없는 신종 사유는 원천적으로 배제됨",
        exception_condition="열거된 사유 뒤에 \"or any other event beyond the reasonable control of the affected party\" 등 포괄 문구가 있는 경우",
        related_clauses=["FIDIC Cl.18/19", "정의(Definitions) 조항"],
        contractual_effect="열거식 정의는 계약 체결 당시 예견하지 못한 사유(신종 감염병, 신규 제재 등)에 대해 구제수단 자체가 없음",
        practical_risk="최근 수년간 팬데믹·전쟁·공급망 제재처럼 계약서 작성 시점에 없던 사유가 반복적으로 발생",
        risk_severity="medium",
        recommended_action="열거된 사유는 예시(illustrative)로 규정하고 포괄적 정의(비열거)를 함께 둠",
        negotiation_goal="열거식 -> 비열거식(non-exhaustive) 정의 전환",
        minimum_acceptable="최소한 열거 목록에 감염병·수출통제·제재를 추가",
        fallback_text="\"'Force Majeure Event' means any event or circumstance beyond the reasonable control of a party, including but not limited to the events listed in this Sub-Clause.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-FM-SANCTIONS",
        contract_type="FIDIC/EPC",
        clause_type="불가항력(Force Majeure)",
        legal_concept="Pandemic / War / Export-Control & Sanctions Events",
        parent_id="FIDIC-FORCE-MAJEURE",
        risk_condition="팬데믹, 전쟁·내란, 수출통제·경제제재로 인한 이행불능·지연이 불가항력 사유에 명시적으로 포함되어 있지 않음",
        exception_condition="별도의 제재(Sanctions) 조항이나 법령변경(Change in Law) 조항이 동일 효과를 커버하는 경우",
        related_clauses=["FIDIC Cl.18/19", "Sanctions 조항", "Change in Law 조항"],
        contractual_effect="제재로 인한 원자재·부품 조달 불능이 불가항력으로 인정되지 않으면 시공사 귀책 지연으로 처리되어 LD 부과 대상이 됨",
        practical_risk="특정 국가산 자재·기술 수출통제로 공급망이 막히는 사례가 실무상 빈번하며, 계약서에 명시가 없으면 분쟁화됨",
        risk_severity="high",
        recommended_action="팬데믹·전쟁·수출통제·제재를 불가항력 사유로 명시적으로 열거",
        negotiation_goal="제재·수출통제 관련 이행불능을 불가항력 범위에 포함",
        minimum_acceptable="최소한 EOT라도 인정되도록 열거",
        fallback_text="\"Force Majeure Event includes epidemic or pandemic, war or civil unrest, and the imposition of export control or economic sanctions measures preventing performance.\"",
        internal_review_note="COMBO 후보: FM 정의 협소 + 제재 미포함 + 비용 미보전이 동시에 있으면 공급망 리스크가 전액 시공사에게 전가됨",
    ),
    RiskNode(
        node_id="FIDIC-FM-PROLONGED",
        contract_type="FIDIC/EPC",
        clause_type="불가항력(Force Majeure)",
        legal_concept="Prolonged Force Majeure / Termination Link",
        parent_id="FIDIC-FORCE-MAJEURE",
        risk_condition="불가항력 상태가 장기화될 경우 해지권(termination right)으로 연결되는 규정이 없어 무기한 계약 유보 상태에 놓임",
        exception_condition="불가항력 지속기간(예: 84일 이상)이 지나면 어느 당사자든 해지할 수 있는 규정이 있는 경우",
        related_clauses=["FIDIC Cl.19.6 (Optional Termination)", "계약해지 조항"],
        contractual_effect="장기화 시 해지 경로가 없으면 당사자 모두 자원을 무기한 묶인 채 손실을 지속 부담",
        practical_risk="장기 분쟁·팬데믹형 불가항력에서 해지권 부재가 프로젝트 전체를 좌초시키는 원인이 됨",
        risk_severity="medium",
        recommended_action="일정 기간(예: 84~180일) 지속 시 상호 해지권을 부여하고 해지 시 정산 방식을 명시",
        negotiation_goal="장기 불가항력 해지권 확보 + 정산 조건 명확화",
        minimum_acceptable="최소한 해지권만이라도 확보(정산조건은 별도 협상)",
        fallback_text="\"If a Force Majeure Event continues for more than 84 consecutive days, either party may terminate this Agreement upon notice, in which case Sub-Clause Z (Termination Payment) shall apply.\"",
        internal_review_note="FIDIC-TERMINATION 노드와 cross-reference 필요",
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
        node_id="FIDIC-TERM-CAUSE",
        contract_type="FIDIC/EPC",
        clause_type="계약해지(Termination)",
        legal_concept="Termination for Cause / Cure Period",
        parent_id="FIDIC-TERMINATION",
        risk_condition="시공사 귀책 해지사유(중대한 위반 등)가 추상적으로 규정되어 있고, 치유기간(cure period) 없이 즉시 해지가 가능함",
        exception_condition="위반 통지 후 합리적 치유기간(통상 14~28일)이 부여되고, 치유 시 해지권이 소멸하는 경우",
        related_clauses=["FIDIC Cl.15.2 (Termination by Employer)"],
        contractual_effect="치유기간 없는 즉시해지권은 경미한 위반에도 발주자가 해지 카드를 협상 지렛대로 남용할 위험",
        practical_risk="해지사유가 모호하고 치유기간이 없으면, LD 미지급 등 사소한 사유로도 해지 통지가 이루어지는 사례가 있음",
        risk_severity="high",
        recommended_action="귀책해지 사유를 구체적으로 열거하고 최소 14~28일의 치유기간을 부여",
        negotiation_goal="해지사유 구체화 + 치유기간 확보",
        minimum_acceptable="최소한 중대한(material) 위반에 한정 + 치유기간 14일",
        fallback_text="\"The Employer may terminate only for a material breach that remains uncured for 14 days after written notice specifying the breach.\"",
        internal_review_note="",
    ),
    RiskNode(
        node_id="FIDIC-TERM-PAYMENT",
        contract_type="FIDIC/EPC",
        clause_type="계약해지(Termination)",
        legal_concept="Post-Termination Payment / Settlement",
        parent_id="FIDIC-TERMINATION",
        risk_condition="해지 후 정산 절차(기시공 대금, 자재비, 철수비용, 보증금 반환 시기)가 규정되어 있지 않거나 발주자 재량에 맡겨짐",
        exception_condition="해지 후 정산 항목과 기한(예: 해지 후 28일 내 지급)이 구체적으로 명시된 경우",
        related_clauses=["FIDIC Cl.15/16", "해지 후 정산(Final Statement) 조항"],
        contractual_effect="정산 절차 부재 시 해지 이후에도 별도 소송·중재 없이는 대금 회수가 불가능",
        practical_risk="해지는 계약의 끝이 아니라 정산 분쟁의 시작인 경우가 많아, 정산 절차 부재가 실무상 가장 큰 후속 리스크",
        risk_severity="high",
        recommended_action="해지 후 정산 항목(기시공 대금, 자재비, 철수비용, 보증금 반환)과 지급기한을 명시",
        negotiation_goal="해지 후 정산 절차·기한의 구체화",
        minimum_acceptable="최소한 기시공 대금 지급기한만이라도 확보",
        fallback_text="\"Within 28 days after termination, the Employer shall pay the Contractor for Works executed, Plant and Materials delivered, and demobilization costs reasonably incurred.\"",
        internal_review_note="FIDIC-FM-PROLONGED와 cross-reference (불가항력 장기화로 인한 해지 시에도 동일 정산절차 적용 여부 확인 필요)",
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

LIABILITY_NODES: list[RiskNode] = [
    RiskNode(
        node_id="FIDIC-LIABILITY-CAP",
        contract_type="FIDIC/EPC",
        clause_type="책임제한(Liability Cap)",
        legal_concept="Limitation of Liability",
        parent_id=None,
        risk_condition="총 책임한도(Liability Cap)가 없거나, LD·면책·IP침해 등이 한도의 예외(carve-out)로 광범위하게 빠져 있음",
        exception_condition="carve-out이 사기·고의·중과실 등 국제 관행상 불가피한 항목으로 한정된 경우",
        related_clauses=["FIDIC 2017 Cl.1.14 (Limitation of Liability)", "FIDIC 1999 Cl.17.6", "Delay Damages 조항", "Indemnity 조항"],
        contractual_effect="carve-out이 넓을수록 명목상 한도와 무관하게 실질 책임이 무제한이 됨",
        practical_risk="LD 상한·면책 범위를 개별 협상해도 Liability Cap에서 빠져 있으면 전체 방어가 무너짐",
        risk_severity="critical",
        recommended_action="총 책임한도를 계약금액 100% 이내로 두고, LD/면책을 한도 안에 포함시키며 carve-out은 사기·고의·중과실로 한정",
        negotiation_goal="Liability Cap 명시 + carve-out 최소화",
        minimum_acceptable="최소한 LD는 한도 내 포함, 간접손해(consequential loss) 배제 확보",
        fallback_text="\"The total liability of the Contractor under or in connection with the Contract shall not exceed the Accepted Contract Amount, save in cases of fraud, gross negligence, deliberate default or reckless misconduct.\"",
        internal_review_note="FIDIC-DELAY-LD, FIDIC-INDEMNITY와 반드시 함께 검토 (carve-out 구조가 동일)",
    ),
]

_ALL_NODES: dict[str, RiskNode] = {n.node_id: n for n in FIDIC_DELAY_NODES + OTHER_NODES + LIABILITY_NODES}

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
    # document_parser.CLAUSE_TYPES 라벨 중 온톨로지 표기와 달랐던 것들
    "지급조건": "지급·인도",
    "이행보증": "성능보증",
    "performance security": "성능보증",
    "보험": "보증·보험",
    "준거법": "중재(Arbitration)",  # FIDIC-ARBITRATION 노드가 준거법 특정 여부까지 다룸
    "governing law": "중재(Arbitration)",
    "지식재산권": "면책(Indemnity)",  # IP 침해 면책은 면책 클러스터의 하위 노드
    "손해배상": "책임제한(Liability Cap)",
    "책임제한": "책임제한(Liability Cap)",
    "책임한도": "책임제한(Liability Cap)",
    "limitation of liability": "책임제한(Liability Cap)",
    "liability cap": "책임제한(Liability Cap)",
}

# 조항유형 분류가 틀려도 핵심 규칙을 놓치지 않도록, 조항 원문의 키워드로
# 클러스터를 결정론적으로 추가 조회한다. 예: Notice/Time Bar 조항이 파서에서
# "분쟁해결"로 분류돼도 Delay 클러스터 규칙이 후보로 제공된다.
_KEYWORD_TRIGGERS: dict[str, list[str]] = {
    "FIDIC-DELAY": [
        r"extension of time", r"\bEOT\b", r"delay damages", r"liquidated damages",
        r"time[- ]?bar", r"notice of claim", r"지체상금", r"공기\s*연장", r"지연\s*통지",
    ],
    "FIDIC-LIABILITY-CAP": [
        r"limitation of liability", r"aggregate liability", r"total liability",
        r"consequential (?:loss|damage)", r"책임\s*한도", r"책임\s*제한",
    ],
    "FIDIC-TERMINATION": [r"terminat(?:e|ion)", r"계약\s*해지"],
    "FIDIC-FORCE-MAJEURE": [r"force majeure", r"exceptional event", r"불가항력"],
    "FIDIC-INDEMNITY": [r"indemnif", r"hold harmless", r"면책"],
    "FIDIC-CHANGE-ORDER": [r"\bvariations?\b", r"change order", r"변경\s*지시"],
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


def canonical_clause_type(clause_type: str) -> str:
    """파서/사용자 라벨을 온톨로지의 clause_type 표기로 정규화한다 (매핑 없으면 원문 유지)."""
    normalized = clause_type.strip().lower()
    return _CLAUSE_TYPE_ALIASES.get(normalized, clause_type.strip())


def get_nodes_for_clause_type(clause_type: str) -> list[RiskNode]:
    normalized = canonical_clause_type(clause_type).lower()
    if not normalized:
        return []
    return [
        n
        for n in _ALL_NODES.values()
        if n.clause_type.lower() == normalized or normalized in n.clause_type.lower()
    ]


def _cluster_of(root_id: str) -> list[RiskNode]:
    root = _ALL_NODES.get(root_id)
    return [root] + get_children(root_id) if root else []


def get_nodes_by_keywords(text: str) -> list[RiskNode]:
    """조항 원문에 특정 키워드가 있으면 해당 클러스터 노드를 반환한다 (LLM 없이 결정론적)."""
    if not text:
        return []
    found: list[RiskNode] = []
    for root_id, patterns in _KEYWORD_TRIGGERS.items():
        if any(re.search(p, text, flags=re.IGNORECASE) for p in patterns):
            found.extend(_cluster_of(root_id))
    return found


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
    RiskCombination(
        combo_id="COMBO-FM-SANCTIONS-COST-TERMINATION",
        required_node_ids=[
            "FIDIC-FM-DEFINITION",
            "FIDIC-FM-SANCTIONS",
            "FIDIC-FORCE-MAJEURE",
        ],
        description=(
            "불가항력 정의가 열거식으로 좁고, 팬데믹·전쟁·수출통제/제재 사유가 "
            "불가항력에 포함되어 있지 않으며, 비용 보전도 배제된 3가지가 동시에 "
            "발견됨. 최근 반복되는 공급망 차단·제재 상황에서 시공사가 EOT조차 "
            "인정받지 못하고 지연 원인 전액을 부담하는 구조가 된다."
        ),
        combined_severity="critical",
        business_impact="제재·공급망 차단으로 인한 이행불능이 통상 지연으로 재해석되어 LD 부과 및 계약해지 트리거로 이어질 수 있음",
        negotiation_priority="불가항력 정의의 비열거화와 제재·수출통제 사유 포함을 최우선 확보 (비용보전은 차선)",
    ),
    RiskCombination(
        combo_id="COMBO-FM-PROLONGED-TERMINATION-PAYMENT",
        required_node_ids=[
            "FIDIC-FM-PROLONGED",
            "FIDIC-TERM-PAYMENT",
        ],
        description=(
            "불가항력 장기화 시 해지권 연계 규정이 없는 상태에서, 해지 후 정산 "
            "절차까지 불명확한 조합. 불가항력이 장기화되어도 계약을 벗어날 "
            "방법이 없고, 설령 다른 사유로 해지되더라도 대금 회수 경로가 없다."
        ),
        combined_severity="high",
        business_impact="장기 불가항력 상황에서 인력·자원이 무기한 묶이고, 이후 해지되어도 정산 지연으로 이중 손실 발생",
        negotiation_priority="장기 불가항력 해지권 확보와 해지 후 정산 기한 명시를 함께 협상 (둘 중 하나만으로는 리스크 해소 안 됨)",
    ),
    RiskCombination(
        combo_id="COMBO-TERMCAUSE-LD-INDEMNITY-WILLFUL",
        required_node_ids=[
            "FIDIC-TERM-CAUSE",
            "FIDIC-DELAY-LD",
            "FIDIC-INDEMNITY-WILLFUL",
        ],
        description=(
            "귀책해지 사유가 치유기간 없이 추상적으로 규정되어 있고, LD 상한이 "
            "높으며, 고의/중과실 면책 배제가 없는 조합. 사소한 지연을 "
            "'중대한 위반'으로 해석해 즉시 해지 -> LD 전액 부과 -> 고의/중과실 "
            "주장을 통한 추가 청구까지 단일 사건에서 연쇄적으로 발생할 수 있다."
        ),
        combined_severity="critical",
        business_impact="치유기간 없는 즉시해지권이 사실상 발주자의 협상 지렛대로 남용되어 시공사가 방어할 시간적 여유 없이 손해배상에 노출됨",
        negotiation_priority="치유기간(cure period) 확보를 최우선으로, 이후 LD sole remedy 조항과 고의/중과실 carve-out을 함께 확보",
    ),
    RiskCombination(
        combo_id="COMBO-LD-CAP-CARVEOUT",
        required_node_ids=[
            "FIDIC-DELAY-LD",
            "FIDIC-LIABILITY-CAP",
        ],
        description=(
            "LD 상한이 높거나 없고, 총 책임한도(Liability Cap)에서 LD가 예외로 "
            "빠져 있는 조합. LD 조항만 보면 '상한 10%' 같은 수치가 있어도, "
            "Liability Cap 조항과 함께 읽으면 LD가 총 한도 밖에서 별도로 "
            "누적되어 실질적으로 무제한 책임이 될 수 있다."
        ),
        combined_severity="critical",
        business_impact="LD와 일반 손해배상이 각각 별도 한도로 누적되어 계약금액을 초과하는 책임에 노출될 수 있음",
        negotiation_priority="LD를 총 책임한도 안에 포함시키는 문구를 LD 요율 협상보다 먼저 확보",
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
