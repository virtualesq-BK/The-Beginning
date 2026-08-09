# The Beginning — Legal Intelligence API

계약서 파일을 업로드하면 AI가 분석해 리스크 리포트를 생성하고, 필요 시 전문가 검토를 연결해주는 서비스입니다. FastAPI 백엔드 + React(Vite) 프론트엔드로 구성되어 있으며 Vercel에 배포됩니다.

## 프로젝트 구조

```
.
├── agents/                 # LLM 클라이언트, 문서 파서, 표준계약서 카탈로그 등 핵심 로직
│   ├── llm_client.py       # OpenAI / Anthropic / Universal(monorouter) 클라이언트
│   ├── document_parser.py
│   ├── file_extractor.py   # pdf/docx 등에서 텍스트 추출
│   ├── knowledge_base.py / vector_store.py / sac_chunker.py
│   ├── risk_analyzer.py / risk_rules.py
│   ├── standard_contract_catalog.py
│   ├── mailer.py           # 전문가 검토 요청 메일 발송
│   └── translator.py
├── api/index.py            # Vercel Python 함수 엔트리포인트 (server.py의 app을 감쌈)
├── frontend/                # React + Vite 프론트엔드
├── pipeline.py              # 계약서 분석 파이프라인 (extract → analyze → report)
├── server.py                 # FastAPI 앱 정의 (로컬 실행 시 uvicorn으로 구동)
├── supabase/                 # Supabase 관련 설정 (인증/회원 프로필)
├── knowledge/                # 지식 문서 (표준계약서 등)
├── tests/
├── requirements.txt
└── vercel.json                # 정적 빌드(frontend) + Python 함수(api) 배포 설정
```

## 주요 API

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| POST | `/api/v1/contracts/analyze` | 계약서 파일 업로드 → 분석 리포트 반환 |
| POST | `/api/v1/expert-requests` | 전문가 검토(번역/법률) 요청 메일 발송 |
| GET | `/api/v1/standard-contracts` | 표준계약서 카탈로그 조회 |

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
