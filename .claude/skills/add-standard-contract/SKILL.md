---
name: add-standard-contract
description: 새 표준계약서(템플릿/서식)를 프로젝트에 추가할 때 따르는 절차. 지식 문서 저장, 카탈로그 등록, 벡터스토어 시드 반영까지 한 번에 처리한다.
---

# 새 표준계약서 추가 절차

새 표준계약서 자료를 추가할 때 아래 3곳을 함께 갱신해야 한다. 하나라도 빠지면 UI 카탈로그와 RAG 검색 결과가 어긋난다.

## 1. 지식 문서 저장 (`knowledge/`)

- 문서 성격에 따라 폴더 선택:
  - `knowledge/standard-contract/` — 일반 표준계약 템플릿 (NDA, EPC, 공급, 라이선스 등)
  - `knowledge/standard-contract-forms/` — 투자/금융 서식 (NVCA, PIPE, SAFE, UNDP, KR-VC 계열)
- 파일명은 kebab-case 영문 (예: `mutual-nda.md`)
- 해당 폴더의 `index.md`에 카테고리(NDA/CONSTRUCTION/LICENSE/SUPPLY/CDA/PURCHASE/SERVICE/EPC 등) 아래 링크와 한 줄 설명을 추가
- 기존 두 폴더에 이미 있는 문서와 중복인지 먼저 확인 (`index.md` 참조)

## 2. 카탈로그 등록 (`agents/standard_contract_catalog.py`)

프론트엔드 카탈로그 화면(`server.py`의 `/api/v1/standard-contracts` → `STANDARD_CONTRACT_RESOURCES`)에 노출하려면 `STANDARD_CONTRACT_RESOURCES` 리스트에 항목 추가:

```python
{
    "id": "kebab-case-id",
    "title": "표시 제목",
    "category": "분류 (예: 무료·영문 표준계약)",
    "group": "그룹 (예: 무역·구매)",
    "description": "한 문장 요약 (한국어, ~습니다체)",
    "detail": "실무 관점 상세 설명 (한국어)",
    "url": "https://...",
    "tags": ["태그1", "태그2"],
}
```

## 3. RAG 시드 문서 반영 (같은 파일의 `build_standard_contract_seed_docs`)

리스크 분석 시 검색되게 하려면 시드 문서 추가:

```python
{
    "doc_id": "STD-<약칭>-001",   # 기존: STD-ITC/STD-ICC/STD-KR/STD-CAUTION
    "clause_type": "표준계약서",
    "text": "2~3문장 한국어 요약. 무엇이고, 어떤 거래에 쓰이며, 사용 시 주의점.",
}
```

- `doc_id`는 기존과 중복되지 않게
- 벡터스토어는 `agents/knowledge_base.py`의 `build_knowledge_store()`가 앱 기동 시 시드를 재적재하므로 별도 마이그레이션은 불필요. 서버 재시작으로 반영
- 임베딩 시 `agents/sac_chunker.py`의 SAC(요약 증강 청킹)가 문서 요약을 덧붙이므로, `text`에 문서 수준 맥락(어떤 계약 유형·거래에 쓰이는지)을 반드시 포함할 것

## 4. 검증

- `python -c "from agents.knowledge_base import build_knowledge_store; s=build_knowledge_store(); print('ok')"` 로 시드 적재 확인
- 서버 기동 후 `/api/v1/standard-contracts` 응답에 새 항목이 보이는지 확인
- `tests/`에 관련 테스트가 있으면 실행
