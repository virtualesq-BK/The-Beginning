# The Beginning — Legal Intelligence API

계약서 파일을 업로드하면 AI가 분석해 리스크 리포트를 생성하고, 필요 시 전문가 검토를 연결해주는 서비스입니다. FastAPI 백엔드 + React(Vite) 프론트엔드로 구성되어 있으며 Vercel에 배포됩니다.

## 서비스 소개

### 목적

해외 건설·수출입 계약(FIDIC, EPC 등)처럼 국내 실무자들이 다루기 까다로운 영문 계약서를, AI로 1차 검토하여 "번역 → 리스크 파악 → 협상 포인트 정리"까지 걸리는 시간을 대폭 줄이고, 필요할 경우 검증된 전문가(번역/법률) 검토로 자연스럽게 이어주는 것을 목표로 합니다.

### 타겟 사용자

- 해외 건설·플랜트 계약(FIDIC 등)을 다루는 법무·계약 담당자
- 수출입 계약서를 검토해야 하는 중소·스타트업 실무자·대표
- 사내에 해외 법무 인력이 부족해 외부 자문에 의존하는 조직

### 페이지 구성

| 경로 | 페이지 | 설명 |
|---|---|---|
| `/` | 메인 (`App.tsx`) | 서비스 소개(히어로, 가치 제안, 이용 흐름), 계약서 업로드·분석, 리스크 리포트 확인, FIDIC 표준 대조, 계약서 초안 생성(`ContractGenerator`), 표준계약서 카탈로그, 사용자 후기, 전문가 검토 요청 |
| `/fidic-history` | FIDIC 히스토리 (`FIDICHistoryPage.tsx`) | 사용자가 저장한 FIDIC 대조/비교 결과 이력 조회 |
| `/standard-contract-compare` | 표준계약서 비교 (`StandardContractComparePage.tsx`) | 대리점·OEM/ODM·라이선스 계약 초안을 표준 관행과 대조, 결과 저장·PDF/JSON/CSV/Excel 내보내기 |
| `/standard-contract-history` | 표준계약서 비교 히스토리 (`StandardContractHistoryPage.tsx`) | 사용자가 저장한 표준계약서 비교 결과 이력 조회(계약유형별 필터) |

### 핵심 기능

- **계약서 업로드 및 AI 분석**: PDF/DOCX 등 계약서 파일을 업로드하면 번역 요약 → 리스크 검토 → 협상 체크리스트 순으로 리포트를 생성 (`/api/v1/contracts/analyze`)
- **근거 기반 리스크 판정 (Evidence → Reasoning → Conclusion)**: 위험도 숫자만 내지 않고, 어떤 Rule이 적용되었는지(`rules_applied`) · 원문 근거(`evidence_quote`) · 추론 과정(`risk_reason`) · 실무 영향(`business_impact`) · 협상 포인트(`negotiation_point`) · 대체 문구(`alternative_text`)까지 감사 가능한(auditable) 형태로 제시
- **Legal Decision Model / Contract Knowledge Graph**: 리스크 규칙을 "LD 10%면 위험" 같은 단순 프롬프트가 아니라, Contract Type → Clause Type → Legal Concept → Risk Condition → Business Context → Risk Severity → Recommended Action → Negotiation Position → Fallback Position 계층을 갖는 노드(`agents/risk_ontology.py`)로 구조화. FIDIC Delay 클러스터(Employer/Contractor/Concurrent Delay, EOT, LD, Notice, Time Bar) 등 총 18개 노드가 서로 연결되어 있음
- **Clause Graph (계약서 조항 그래프)**: 업로드된 계약서의 조항을 노드로, 상·하위 조항(8 → 8.7), 명시적 상호참조("subject to Sub-Clause 20.1"), SAC 의미 유사도, 조항유형 의존관계를 엣지로 구성 (`agents/clause_graph.py`). 각 조항은 연결된 조항 원문과 함께 분석됨
- **Summary-Augmented Chunking (SAC)**: 계약서 조항마다 "문서 요약 + 조항 번호/유형 + 본문"으로 청크를 만들어 임베딩 인덱싱 (`agents/sac_chunker.py`의 `ContractSACIndex`). 여러 계약이 섞인 인덱스에서도 조항이 어느 계약의 맥락인지 벡터에 남도록 하는 기법
- **조항 간 상호작용(Cross-Clause Risk) 탐지**: 개별 조항은 위험도가 낮아 보여도, 특정 조합(예: "EOT 인정조건 좁음 + Notice 7일 Time Bar + LD 상한 높음")이 함께 발견되면 위험도가 급등하는 패턴을 Clause Graph 위에서 판정. 근거 조항이 명시적 참조로 연결됐는지(`explicit`), 의미적으로만 연결됐는지(`semantic`), 단순히 함께 등장했는지(`co_occurrence`)를 신뢰도로 구분하고, 연결이 확인되지 않은 조합은 전문가 확인 필요로 표시 (리포트 `cross_clause_risks` 필드)
- **Hybrid Retrieval (Vector + Rule Engine)**: Semantic Retrieval(벡터 유사도 검색)과 Rule Retrieval(Knowledge Graph 결정론적 조회)을 분리된 경로로 명시해, LLM이 모든 판단을 떠맡지 않도록 구성 (`agents/knowledge_base.py`의 `hybrid_retrieve()`)
- **FIDIC 계약서 비교**: 사용자 초안을 FIDIC Red/Yellow/Silver 등 표준 기준과 대조해 공기(EOT)·비용(LD)·하자담보(DLP)·변경(Variation) 등 핵심 조항의 불균형 여부 점검, 결과 저장 및 리포트(JSON) 내보내기
- **표준계약서 카탈로그**: 해외 계약 실무에 쓰이는 표준계약서 목록/상세 제공 (`/api/v1/standard-contracts`)
- **전문가 검토 연결**: AI 1차 검토 후 필요 시 번역·법률 전문가 검토 요청 메일 발송 (`/api/v1/expert-requests`)
- **인허가·규제 대응 자동화 (RegTech)**: 화학·제약·인프라 사업의 국가/업종별 필요 인허가를 그래프(`agents/regulatory_ontology.py`)로 매핑해 선행 절차 순서까지 정리하고, 신청서 초안(`dossier_drafter`)과 제출 서류 누락·부실 여부(`gap_analyzer`)를 점검 (`/api/v1/regulatory/analyze`). global-compliance-ai 프로젝트에서 이식했으며, 계약 리스크 분석과 달리 계약서가 아닌 정부 인허가 절차를 다룸
- **전문가 Feedback Loop / 자체 Benchmark**: 변호사가 AI 판단을 수정한 이력을 "AI 판단 → 수정 내용 → 수정 이유"까지 구조화 저장(`agents/feedback_loop.py`)하고, 검증된 케이스를 Ground Truth로 승격해 Clause Detection·Risk Detection Recall·False Positive·Rule Accuracy·Evidence Accuracy·Cross-Clause Reasoning Recall을 자체 채점(`agents/benchmark.py`)
- **회원 인증**: Supabase 기반 로그인/회원가입, 로그인 사용자별 업로드·분석 이력 저장

## 기술 스택

### 백엔드

- **FastAPI** — REST API 서버 (`server.py`), Vercel Python 함수로 배포 (`api/index.py`)
- **LLM 연동** — OpenAI / Anthropic / Universal(monorouter) 클라이언트를 선택적으로 구성 (`agents/llm_client.py`)
- **문서 처리** — PDF/DOCX 등에서 텍스트 추출(`agents/file_extractor.py`) 및 계약서 파싱(`agents/document_parser.py`: 조항 번호·상위 조항·상호참조 추출, 상호참조는 정규식으로도 교차 추출)
- **RAG / 지식베이스** — `agents/knowledge_base.py`(Semantic + Rule Hybrid Retrieval), `agents/vector_store.py`로 표준 실무 문서 검색, `agents/sac_chunker.py`로 계약서 조항 SAC 인덱싱
- **Clause Graph** — `agents/clause_graph.py`: 계약서 조항 간 관계 그래프 및 그래프 기반 조합 위험 판정
- **Legal Decision Model** — `agents/risk_ontology.py`: 조항유형별 Contract Knowledge Graph(RiskNode)와 조항 간 조합위험(RiskCombination) 정의
- **리스크 분석** — 규칙 기반(Knowledge Graph) + LLM 기반 하이브리드 분석, Evidence→Reasoning→Conclusion 구조 출력 (`agents/risk_analyzer.py`, `agents/risk_rules.py`)
- **전문가 Feedback Loop / Benchmark** — `agents/feedback_loop.py`(AI-변호사 판단 차이 구조화), `agents/benchmark.py`(자체 평가지표 채점)
- **메일 발송** — 전문가 검토 요청 메일 (`agents/mailer.py`)
- **인증/DB** — Supabase (회원 인증, 프로필, 이력 저장, 계약 Lifecycle/Feedback/Benchmark 데이터)

### 프론트엔드

- **React 19** + **TypeScript** + **Vite** — SPA 빌드
- **React Router 7** — 클라이언트 라우팅 (`/`, `/fidic-history`)
- **Tailwind CSS 4** — 스타일링
- **Supabase JS SDK** — 클라이언트 인증 연동

### 인프라 / 배포

- **Vercel** — 프론트엔드 정적 빌드 + 백엔드 Python 서버리스 함수를 하나의 프로젝트로 배포 (`vercel.json`)
- **Supabase** — 인증 및 데이터 저장

## 프로젝트 구조

```
.
├── agents/                 # LLM 클라이언트, 문서 파서, 표준계약서 카탈로그 등 핵심 로직
│   ├── llm_client.py       # OpenAI / Anthropic / Universal(monorouter) 클라이언트
│   ├── document_parser.py  # 조항 분해 + 조항 번호/계층/상호참조 추출
│   ├── file_extractor.py   # pdf/docx 등에서 텍스트 추출
│   ├── risk_ontology.py    # Legal Decision Model: RiskNode 계층 + RiskCombination(조항 간 상호작용)
│   ├── clause_graph.py     # 계약서 Clause Graph + 그래프 기반 조합 위험 판정
│   ├── sac_chunker.py      # Summary-Augmented Chunking: 계약서 조항 SAC 인덱스
│   ├── knowledge_base.py / vector_store.py                    # Hybrid Retrieval (Semantic + Rule)
│   ├── risk_analyzer.py / risk_rules.py                       # Evidence→Reasoning→Conclusion 리스크 분석
│   ├── feedback_loop.py    # 전문가(변호사) 판단 수정 이력 구조화
│   ├── benchmark.py        # 자체 Contract Intelligence Benchmark 채점기
│   ├── standard_contract_catalog.py
│   ├── mailer.py           # 전문가 검토 요청 메일 발송
│   └── translator.py
├── api/index.py            # Vercel Python 함수 엔트리포인트 (server.py의 app을 감쌈)
├── frontend/                # React + Vite 프론트엔드
├── pipeline.py              # 계약서 분석 파이프라인 (parse → translate → SAC index → clause graph → analyze → cross-clause → report)
├── server.py                 # FastAPI 앱 정의 (로컬 실행 시 uvicorn으로 구동)
├── supabase/                  # Supabase 스키마/마이그레이션
│   ├── schema.sql                              # profiles / contract_analyses / fidic_comparisons / expert_requests
│   ├── migrate_contract_uploads.sql            # 업로드 Storage 연동
│   ├── migrate_lifecycle_and_feedback.sql      # 계약 Lifecycle(contracts/contract_versions/negotiation_events) + expert_feedback/benchmark_cases
│   └── migrate_standard_contract_comparisons.sql # 표준계약서(대리점/OEM·ODM/라이선스) 비교 결과 저장 테이블
├── knowledge/                # 지식 문서 (표준계약서 등)
├── tests/
├── requirements.txt
└── vercel.json                # 정적 빌드(frontend) + Python 함수(api) 배포 설정
```

## 주요 API

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| POST | `/api/v1/contracts/analyze` | 계약서 파일 업로드 → 분석 리포트 반환 (`rules_applied`/`cross_clause_risks` 포함) |
| POST | `/api/v1/expert-requests` | 전문가 검토(번역/법률) 요청 메일 발송 |
| GET | `/api/v1/standard-contracts` | 표준계약서 카탈로그 조회 |
| POST | `/api/v1/standard-contracts/compare` | 대리점(`distributor`)/OEM·ODM(`oem_odm`)/라이선스(`license`) 계약 초안을 표준 관행과 대조 분석 |
| POST | `/api/v1/standard-contracts/compare/save` | 표준계약서 비교 결과 저장 |
| GET | `/api/v1/standard-contracts/compare/history` | 저장된 표준계약서 비교 이력 목록 조회 (`contract_type` 쿼리로 필터 가능) |
| GET | `/api/v1/standard-contracts/compare/history/{comparison_id}` | 저장된 표준계약서 비교 결과 단건 조회 |
| DELETE | `/api/v1/standard-contracts/compare/history/{comparison_id}` | 저장된 표준계약서 비교 결과 삭제 |
| DELETE | `/api/v1/standard-contracts/compare/history/batch-delete` | 저장된 표준계약서 비교 결과 일괄 삭제 |
| POST | `/api/v1/standard-contracts/compare/export`, `export-json`, `export-csv`, `export-excel` | 표준계약서 비교표 내보내기 (PDF/JSON/CSV/Excel) |
| GET | `/api/v1/contract-templates` | 계약서 템플릿 목록 조회 |
| POST | `/api/v1/contract-templates/{template_id}/generate` | 템플릿 기반 계약서 초안 생성 |
| POST | `/api/v1/fidic/compare` | 사용자 초안을 FIDIC 표준과 대조 분석 |
| POST | `/api/v1/fidic/compare/save` | FIDIC 비교 결과 저장 |
| GET | `/api/v1/fidic/compare/history` | 저장된 FIDIC 비교 이력 목록 조회 |
| GET | `/api/v1/fidic/compare/history/{comparison_id}` | 저장된 FIDIC 비교 결과 단건 조회 |
| DELETE | `/api/v1/fidic/compare/history/{comparison_id}` | 저장된 FIDIC 비교 결과 삭제 |
| DELETE | `/api/v1/fidic/compare/history/batch-delete` | 저장된 FIDIC 비교 결과 일괄 삭제 |
| POST | `/api/v1/fidic/compare/export`, `export-json`, `export-csv`, `export-excel` | FIDIC 비교표 내보내기 (PDF/JSON/CSV/Excel) |

## Contract Intelligence 아키텍처

이 프로젝트는 "LLM + Prompt + RAG"만으로는 만들 수 없는 데이터·워크플로우·평가체계를 목표로, 다음 구조를 실제 코드로 구현했습니다.

```
                Contract
                   ↓
          Document Parser (agents/document_parser.py)
      (조항 번호 · 상위 조항 · 상호참조 추출)
                   ↓
     SAC Index (sac_chunker.py: 문서 요약 + 조항 임베딩)
                   ↓
     Clause Graph (clause_graph.py)
   (계층 · 상호참조 · SAC 유사도 · 유형 의존 엣지)
                   ↓
       ┌───────────┴───────────┐
       ↓                       ↓
Semantic Retrieval      Rule Retrieval
(vector_store.py)       (risk_ontology.py — 조항유형 + 키워드 + 참조 조항 유형)
       └───────────┬───────────┘
        agents/knowledge_base.py: hybrid_retrieve()
                   ↓
         risk_analyzer.analyze_clause()
   (연결 조항 원문과 함께 Evidence → Reasoning → Conclusion)
                   ↓
    clause_graph.evaluate_cross_clause_risks_graph()
   (조합 위험 + 근거 조항 + 신뢰도 explicit/semantic/co_occurrence)
                   ↓
         전문가 검토 (변호사 수정)
                   ↓
      feedback_loop.py → benchmark.py
   (AI 판단 vs 수정 이유 → Ground Truth 승격 → 자체 벤치마크 채점)
```

**완료된 항목**

| 항목 | 구현 위치 | 내용 |
|---|---|---|
| Legal Decision Model | `agents/risk_ontology.py` | Contract Type → Clause Type → Legal Concept → Risk Condition → ... → Fallback Position 계층의 `RiskNode`. FIDIC Delay 클러스터(8개 노드), 면책(4개: 고의/중과실·IP침해·기밀유지 세분화), 불가항력(4개: 정의범위·제재/수출통제·장기화 세분화), 계약해지(3개: 귀책해지 치유기간·해지후 정산 세분화) + 아직 단일 노드인 7개 조항유형(중재·하자담보·변경명령·성능보증·지급인도·보증보험·공사변경) + 책임제한(Liability Cap), 총 27개 노드. 파서의 모든 조항유형(기타 제외)이 온톨로지 노드에 연결되며, 조항 원문 키워드로도 클러스터를 결정론적으로 조회 |
| Evidence 기반 출력 | `agents/risk_analyzer.py` | `risk_score` 단일값이 아니라 `rules_applied` / `evidence_quote` / `risk_reason` / `business_impact` / `recommendation` / `negotiation_point` / `alternative_text`까지 감사 가능한 구조로 응답 |
| 조항 간 상호작용 탐지 | `agents/risk_ontology.py`(`RiskCombination`), `agents/clause_graph.py` | 개별 조항은 낮아 보여도 특정 조합이 함께 있으면 위험도가 급등하는 패턴을 Clause Graph 위에서 판정, 리포트의 `cross_clause_risks` 필드로 근거 조항 id·신뢰도와 함께 노출. 총 7개 조합: EOT+Notice+LD, LD+면책+해지, 변경명령+공사변경+EOT, 불가항력정의+제재+비용미보전, 불가항력장기화+해지후정산, 귀책해지+LD+고의중과실면책, LD+책임한도 carve-out |
| Clause Graph | `agents/clause_graph.py`, `agents/document_parser.py` | 계약서 조항을 노드로, 계층(hierarchy)·명시적 상호참조(cross_reference)·SAC 유사도(sac_similarity)·조항유형 의존(type_dependency)을 엣지로 구성. 참조 번호가 정확히 없으면 가장 가까운 상위 조항으로 해석. 리포트 `clause_graph` 필드와 조항별 `related_clause_ids`로 노출 |
| Summary-Augmented Chunking | `agents/sac_chunker.py`(`ContractSACIndex`) | 계약서 조항을 "문서 요약 + 조항" 청크로 임베딩 인덱싱. 같은 문서 청크는 요약을 공유해 유사도가 전반적으로 높게 나오므로 절대 임계값 대신 상위 k개 + 문서 내 중앙값 초과 기준으로 연관 조항 선택. 임베딩 API 실패 시 명시적 참조 그래프만으로 분석 계속(`clause_graph.sac_status`) |
| FIDIC 외 표준계약서 비교 엔진 | `agents/standard_contract_comparison.py`, `/api/v1/standard-contracts/compare*` | FIDIC 전용이던 조항 대조 기능을 대리점(distributor)·OEM/ODM·라이선스(license) 계약까지 확장. 계약유형별 키워드 기반 조항 점검(준거법/관할, 손해배상 상한 carve-out, 해지·보상, IP 귀속 등)과 근거 문장(sentence_evidence) 반환. FIDIC 비교와 동일하게 저장(`/save`)·이력 조회·삭제(단건/배치)·PDF/JSON/CSV/Excel 내보내기까지 백엔드·프론트엔드(`/standard-contract-compare`, `/standard-contract-history` 페이지) 모두 구현 완료. Supabase `standard_contract_comparisons` 테이블(`supabase/migrate_standard_contract_comparisons.sql`)에 `fidic_comparisons`와 동일한 패턴(로그인 시 Supabase 직접 저장, 실패 시 백엔드 REST 폴백)으로 연동 |
| Hybrid Retrieval | `agents/knowledge_base.py`(`hybrid_retrieve`) | Semantic Retrieval(Vector)과 Rule Retrieval(Knowledge Graph)을 분리된 경로로 명시, LLM에게 결정론적 규칙과 참고자료를 구분해서 제공 |
| 계약 Lifecycle 데이터 | `supabase/migrate_lifecycle_and_feedback.sql` | `contracts`(딜 단위 그룹) / `contract_versions`(Draft→Negotiation→Final 버전 이력) / `negotiation_events`(AI 위험탐지→협상포인트→상대방반응→최종합의) |
| 전문가 Feedback Loop | `agents/feedback_loop.py`, `expert_feedback` 테이블 | AI 판단과 변호사 수정 내용을 "왜 다른가"(`correction_reason`)까지 구조화 저장, `disagreement_type` 자동 1차 분류 |
| 자체 Benchmark | `agents/benchmark.py`, `benchmark_cases` 테이블 | Clause Detection / Risk Detection Recall / False Positive / Rule Accuracy(F1) / Evidence Accuracy / Cross-Clause Reasoning Recall 채점 |

## 다음 단계 (로드맵 — 아직 미착수)

아래는 지금 구현체보다 한 단계 위의 제품 설계 영역으로, 우선순위가 정해지면 이어서 진행할 항목입니다.

| 항목 | 내용 | 비고 |
|---|---|---|
| 온톨로지 확장 (진행 중) | 면책·불가항력·계약해지는 세분화 완료(총 26개 노드). 남은 7개 조항유형(중재·하자담보·변경명령·성능보증·지급인도·보증보험·공사변경)은 아직 조항유형당 1개 노드(단일 레벨) | `agents/risk_ontology.py`의 `OTHER_NODES`를 확장 |
| 표준계약서 카탈로그 실제 조문 fixture | `standard_contract_catalog.py`는 설명 텍스트만 있고 CISG/NDA 등은 아직 비교 엔진이 없음 (대리점/OEM/라이선스만 우선 구현) | 실제 표준 조문 원문(저작권 이슈 없는 요약본)을 구할 수 있으면 비교 정확도가 올라감 — 자료 확보 시 알려주면 반영 |
| LLM-independent Abstraction Layer | 현재 `agents/llm_client.py`가 OpenAI/Anthropic/Universal을 다루지만, Application Layer — Contract Intelligence Layer — Rule/Knowledge/Evaluation Layer — LLM Abstraction Layer로 명시적 계층 분리는 아직 안 되어 있음 | 모델 교체 시 Rule/Knowledge Graph/Benchmark 자산이 영향받지 않도록 하는 것이 목표 |
| 협상 시나리오 엔진 | 위험도 분석 → 수정 권고 → 상대방 예상 반론 → 대응 논리 → 양보 가능 조건 → 대체조건 → 협상 우선순위 → 최종 협상 시나리오까지 엔드투엔드로 이어주는 기능 | `negotiation_events` 테이블은 준비됐으나, 시나리오 생성 로직은 미구현 |
| Contract OS 상위 워크플로우 | Contract Review → Negotiation → Approval → Execution → Obligation Tracking → Claim Detection → Renewal/Termination → Compliance | 지금은 "계약 리뷰"까지만 구현. Approval/Obligation Tracking/Compliance 모듈 없음 |
| 계약 간 SAC 코퍼스 | 현재 SAC 인덱스는 분석 1회(계약서 1건) 동안만 메모리에 존재. 여러 계약의 SAC 청크 임베딩을 Supabase(pgvector 등)에 누적하면 "유사 EPC 계약 N건에서 같은 유형 조항이 어떻게 수정됐는가" 검색이 가능해짐 | `ContractSACIndex.search()`와 `contract_versions`/`negotiation_events` 테이블을 연결 |
| 그래프 기반 조합 판정 튜닝 | 조합 규칙 7개의 판정 품질은 파서의 조항 번호·상호참조 추출 정확도에 좌우됨. 실제 계약서로 `explicit`/`co_occurrence` 비율과 오탐을 측정해야 함 | `benchmark.py`에 조합 판정 신뢰도별 지표 추가 |
| 온톨로지 → Benchmark 자동 연동 | `feedback_loop.promote_to_benchmark_case()`는 구조는 있지만, 실제 운영에서 검증 절차를 거쳐 자동으로 승격시키는 배치/워크플로우는 아직 없음 | 현재는 수동 호출 전제 |

## 로컬 실행

### 백엔드 (FastAPI)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # 값 채우기
uvicorn server:app --reload
```

### 프론트엔드 (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

## 환경변수 (`.env`)

`.env.example`을 참고해 루트 `.env`를 채웁니다. `.env`는 절대 커밋하지 않습니다 (`.gitignore`에 포함되어 있어야 함).

| 변수 | 설명 |
|---|---|
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | 기본 LLM 클라이언트 (monorouter의 `/openai/v1` 경로 경유) |
| `OPENAI_EMBED_MODEL` | 임베딩 모델 |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` / `ANTHROPIC_ENABLE=1` | Anthropic 클라이언트 (선택, `ANTHROPIC_ENABLE=1`일 때만 활성화) |
| `EXPERT_EMAIL` | 전문가 검토 요청 메일 수신 주소 |
| `PUBLIC_APP_ORIGIN` | 메일 링크 등에 쓰이는 앱 공개 도메인. 배포 도메인과 반드시 일치해야 함 |
| `Universal_API` / `Universal_URL` / `Universal_MODEL` (선택) | monorouter Universal 게이트웨이 전용 클라이언트. `gpt-5.6-sol` / `gpt-5.6-terra` / `gpt-5.6-luna` 등 별도 모델 호출용 |

### Universal 게이트웨이 (`Universal_API` / `Universal_URL`)

`https://monogpt.kr/api/monorouter/v1/`을 base URL로 하는 OpenAI 호환 게이트웨이입니다. 기존 `OPENAI_*` 클라이언트와 별개로, [`agents/llm_client.py`](agents/llm_client.py)에 전용 클라이언트가 구성되어 있습니다.

```python
from agents.llm_client import chat_universal

chat_universal(
    system="You are terse.",
    user="say hi in one word",
    model="gpt-5.6-sol",   # 생략 시 Universal_MODEL(기본 gpt-5-nano-chat) 사용
)
```

- `Universal_API`가 설정되어 있으면 모듈 로드 시 자동으로 클라이언트가 초기화됩니다.
- `Universal_MODEL` 환경변수로 기본 모델을 지정하거나, 호출 시 `model=` 인자로 직접 지정할 수 있습니다.
- `models`, `chat/completions` 엔드포인트 모두 정상 동작 확인됨 (200 OK, OpenAI 호환 응답 포맷).

## 배포 (Vercel)

`vercel.json`이 `frontend/`를 정적 빌드로, `api/index.py`를 Python 함수로 배포합니다. 환경변수는 로컬 `.env`뿐 아니라 Vercel 프로젝트(Production/Preview)에도 동일하게 등록해야 합니다 (`vercel env add`). 배포 전 `vercel env ls`로 필수 키가 모두 있는지 확인하세요.
