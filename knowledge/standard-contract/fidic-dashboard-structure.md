# Overseas Construction Dashboard Blueprint

- 목적: FIDIC와 사용자 입력 건설계약을 한 화면에서 동시에 비교·검토할 수 있도록 하는 구조 설계
- 활용 사례: 건설계약 초안, EPC 초안, 발주자 문안, 시공사 문안, 하도급 문안 평가

## 1. 대시보드 구성

```json
{
  "dashboard_sections": [
    {
      "section": "Project Snapshot",
      "items": [
        "계약 유형",
        "공사 목적",
        "발주자/시공사/감리 역할",
        "공사 금액",
        "공기",
        "사업국가"
      ]
    },
    {
      "section": "Comparison Lens",
      "items": [
        "Design responsibility",
        "Variation / change order",
        "EOT and LD",
        "Defects liability",
        "Performance security",
        "Dispute resolution"
      ]
    },
    {
      "section": "Risk Signal",
      "items": [
        "Risk score",
        "High-risk clauses",
        "Need for lawyer review",
        "Negotiation priority"
      ]
    },
    {
      "section": "Recommended Action",
      "items": [
        "수정 권장 포인트",
        "협상 문구 예시",
        "보증/책임한도 재조정",
        "분쟁절차 보완"
      ]
    }
  ]
}
```

## 2. 화면 구조 예시

```markdown
### FIDIC vs 사용자 건설계약 비교 대시보드

1. Project Snapshot
   - 계약 유형: EPC / Design-Build / Construction
   - 공사범위: 설계, 시공, 유지보수 포함 여부
   - 발주자/시공사 역할 분담

2. Core Comparison
   - 설계 책임
   - 변경지시/변경수당
   - 공기 연장(EOT)
   - 지체상금(LD)
   - 하자보수(DLP)
   - 보증/보험
   - 중재/준거법

3. Risk Callout
   - 고위험 조항: 지체상금 상한 없음, 일방적 변경권, 과다한 면책, 성능기준 부재
   - 위험 점수: 0~100
   - 전문가 검토 필요 여부

4. Negotiation Recommendation
   - 시공사: 공기 연장, 보상 범위, 책임한도 보완
   - 발주자: 성능 기준, 테스트/인수 기준, DLP 현실화

## 3. 정책 기준

- FIDIC 리스크 패턴을 기준선으로 사용
- 입력 계약서의 문언을 기준점과 비교
- 각 항목에 대해 “유사”, “보완 필요”, “불균형” 상태 표시
- 체크리스트는 프로젝트 유형별로 적용 가능하도록 세분화

## 4. 입력값 예시

```json
{
  "project_type": "EPC",
  "design_responsibility": "contractor",
  "variation_right": "employer",
  "delay_damages": "cap_missing",
  "defects_liability_period": "36 months",
  "governing_law": "Qatar law",
  "dispute_mechanism": "ICC arbitration"
}
```

## 5. 추천 로직

- 설계 책임이 불명확하면 위험 점수 상승
- 지체상금 상한 누락 시 최고 위험으로 분류
- 변경지시와 비용보상 연결이 비정상적이면 협상 우선순위 상승
- 중재/준거법 미기재 시 비용 및 분쟁 기간 증가 가능성 표시

## 6. 사용 목적

- 사전 협상 점검
- 계약 검토 초안 비교
- FIDIC과 실제 계약 문안의 편차 파악
- 법률 전문가 상호 검토용 자료 제공
