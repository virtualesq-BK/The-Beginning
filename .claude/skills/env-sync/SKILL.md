---
name: env-sync
description: 이 프로젝트의 환경변수를 로컬(.env)과 Vercel 간에 확인·동기화할 때 따르는 절차. vercel:env-vars 스킬을 함께 사용한다.
---

# 환경변수 관리 절차

이 프로젝트는 Vercel에 배포되며(`vercel.json`: 프론트 static-build + `api/index.py` Python 함수), 백엔드 환경변수는 루트 `.env`에 있다.

## 필요한 환경변수 (루트 `.env`)

- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`
- `EXPERT_EMAIL` — 전문가 검토 메일 수신자
- `PUBLIC_APP_ORIGIN` — 메일 링크 등에 쓰이는 앱 공개 주소

프론트엔드(Supabase 등) 변수는 `frontend/` 쪽 `.env` 파일을 별도 확인.

## 절차

1. 환경변수 작업(추가/변경/비교/pull)이 필요하면 **항상 `vercel:env-vars` 스킬을 먼저 로드**하고 그 지침을 따른다.
2. Vercel CLI가 없으면 `npm i -g vercel` 후 `vercel link`로 프로젝트 연결.
3. 새 변수를 추가할 때는 세 곳을 함께 갱신:
   - 로컬 `.env`
   - Vercel(Production/Preview) — `vercel env add`
   - 코드에서 읽는 위치(`os.environ` / `os.getenv`)와 이 문서의 변수 목록
4. `.env` 값을 채팅/커밋/로그에 절대 노출하지 않는다. `.env`는 gitignore 상태를 유지.
5. 배포 전 `vercel env ls`로 Production에 필수 키가 모두 있는지 확인. 특히 `PUBLIC_APP_ORIGIN`은 배포 도메인과 일치해야 메일 링크가 깨지지 않는다.
