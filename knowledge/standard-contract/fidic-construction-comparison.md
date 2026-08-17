# FIDIC vs User Construction Contract Comparison

- 목적: 해외 건설 계약서와 FIDIC 표준계약을 비교하여 핵심 리스크를 한눈에 확인하기 위한 표준 비교표
- 사용 방식: 실제 분쟁, 공사계약, EPC, 발주자 초안, 시공사 초안, 하도급, 설계/시공 역할 분담 문서를 비교할 때 사용
- 주의: 본 문서는 원문 계약서 전문을 복제하는 것이 아니라, 표준 비교 용도로 만든 구조적 요약이다.

## 1. 핵심 비교 표

```json
{
  "contract_profile": {
    "project_type": "Construction / EPC / Plant / Design-Build / Infrastructure",
    "party_role": {
      "employer": "발주자",
      "contractor": "시공사",
      "engineer": "감리/엔지니어"
    },
    "design_responsibility": {
      "fidic_red": "Employer design dominant",
      "fidic_yellow": "Shared or contractor design responsibility",
      "fidic_silver": "Contractor performance and design responsibility dominant"
    }
  },
  "comparison_matrix": [
    {
      "issue": "Design responsibility",
      "fidic_reference": "Red / Yellow / Silver Book",
      "fidic_practice": "설계 책임이 각 패밀리별로 달라짐",
      "user_contract": "사용자 입력 초안의 설계 범위",
      "risk_flag": "설계범위 불명확 시 공기·비용·책임 전가 위험"
    },
    {
      "issue": "Time for completion",
      "fidic_reference": "EOT / Completion / Delay Damages",
      "fidic_practice": "공기연장과 지체상금은 분리 구조로 해석",
      "user_contract": "사용자 문안의 완료시점·지체상금 계산식",
      "risk_flag": "완료시점과 LD 산정 기준 혼재 시 분쟁 risk 증가"
    },
    {
      "issue": "Variation / change order",
      "fidic_reference": "Variation + EOT + Cost adjustment",
      "fidic_practice": "변경지시와 보상 조정이 연결되어야 함",
      "user_contract": "일방적 변경권 범위",
      "risk_flag": "변경지시 단독으로 비용/기간 보상 없이 처리 시 불공정"
    },
    {
      "issue": "Liquidated damages",
      "fidic_reference": "Delay Damages / Cap / Exclusive Remedy",
      "fidic_practice": "통상 상한(cap)과 예외 구제수단을 함께 검토",
      "user_contract": "LD 상한, 예외사유, 손해배상 중복 여부",
      "risk_flag": "상한 없음·배상 중복 허용 시 사업리스크 극대화"
    },
    {
      "issue": "Defects liability",
      "fidic_reference": "Defects Notification Period",
      "fidic_practice": "통상 1~2년 수준이 일반적",
      "user_contract": "하자보수기간·통지기한",
      "risk_flag": "과도한 장기 보수책임은 시공사 재무 리스크 축적"
    },
    {
      "issue": "Performance security",
      "fidic_reference": "Performance Bond / Guarantee",
      "fidic_practice": "이행보증과 조건 조정이 핵심",
      "user_contract": "보증금, 해지 시 연동 조항",
      "risk_flag": "보증이 과소하거나 해지 시점 불명확 시 리스크"
    },
    {
      "issue": "Dispute resolution",
      "fidic_reference": "DAB / Arbitration / Governing Law",
      "fidic_practice": "중재기관·중재지·언어·준거법 명확화 필요",
      "user_contract": "분쟁절차와 국내법 적용 여부",
      "risk_flag": "절차 불명확 시 비용과 기간 증가"
    }
  ],
  "comparison_summary": {
    "contractor_favorable_signals": [
      "설계 책임 명확화",
      "EOT와 비용 조정의 연계",
      "LD 상한과 예외 조항",
      "DLP 적절성",
      "보증 및 책임한도 균형"
    ],
    "employer_favorable_signals": [
      "성능 기준 명확화",
      "변경지시 통제권",
      "완료시점 관리",
      "하자보수와 테스트 인수 기준",
      "디자인 및 서류 소유권 명시"
    ]
  }
}
```

## 2. 요약 표(마크다운)

| 항목 | FIDIC 기준 | 사용자 계약서 기준 | 리스크 포인트 |
|---|---|---|---|
| 설계 책임 | Red/Yellow/Silver로 책임 분배가 명확 | 설계 범위가 모호한지 | 책임전가/공사변경 분쟁 |
| 공기 연장 | EOT 절차와 LD 연계 | 연장 기준이 불명확한지 | 지연 책임 과대 |
| 변경지시 | Variation + 비용/공기 보정 | 일방적 변경권 여부 | 추가비용·지연 인정 누락 |
| 지체상금 | 상한/예외/배제 원칙 검토 | 과도한 LD 유무 | 사업성 저하 |
| 하자보수 | DLP 1~2년이 일반적 | 장기 DLP 여부 | 장기 책임 부담 |
| 중재 | DAB/중재기관/중재지 명시 | 분쟁절차 불분명 | 분쟁 지연 및 비용 증가 |
| 보증/보험 | 이행보증·보험 구조 검토 | 보증금 누락 여부 | 신용 리스크 |

## 3. 대시보드용 주의 포인트

- 설계범위 미정리: 시공사와 발주자 모두 책임 회피 가능
- 변경지시와 비용 보상 불일치: 공사비 증액과 지연 분쟁 발생
- 지체상금 상한이 없는 경우: 시공사가 재무상 불균형 부담
- 성능기준이 추상적: 인수·하자 시 다툼 가능성 높음
- 보증 및 책임한도 불균형: 프로젝트 성사 전 리스크 누적

## 4. 사용 지침

- 본 표는 초안 비교와 협상 포인트 도출용
- 실제 계약 체결 전에는 정확한 법률 자문과 원문 검토가 필요
- FIDIC 공식 원문은 저작권 주의가 있으므로, 전체 문장 복제가 아니라 구조·비교·리스크 요약으로만 활용
