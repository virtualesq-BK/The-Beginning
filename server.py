from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline import run_pipeline
from agents.file_extractor import extract_text, SUPPORTED_EXTENSIONS
from agents.mailer import send_expert_request

app = FastAPI(title="The Beginning - Legal Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExpertRequestBody(BaseModel):
    request_type: Literal["translation_review", "legal_expert"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/contracts/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다: {ext} (지원 형식: {allowed})")

    contents = await file.read()

    try:
        raw_text = extract_text(contents, file.filename)
        report = run_pipeline(raw_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"분석 중 오류가 발생했습니다: {e}")

    return report


@app.post("/api/v1/expert-requests")
def create_expert_request(body: ExpertRequestBody):
    try:
        return send_expert_request(body.request_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"전문가 연결 요청 메일 발송에 실패했습니다: {e}")
