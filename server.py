from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from anthropic import PermissionDeniedError as AnthropicPermissionDeniedError

from pipeline import run_pipeline
from agents.file_extractor import extract_text, SUPPORTED_EXTENSIONS
from agents.mailer import send_expert_request
from agents.standard_contract_catalog import STANDARD_CONTRACT_RESOURCES

app = FastAPI(title="The Beginning - Legal Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vercel 빌드 시 frontend/dist → api/static 으로 복사됨
STATIC_DIR = Path(__file__).resolve().parent / "api" / "static"
if not STATIC_DIR.is_dir():
    # api/index.py 에서 import 되는 경우 (cwd/api/static)
    STATIC_DIR = Path(__file__).resolve().parent / "static"


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
    except AnthropicPermissionDeniedError as e:
        raise HTTPException(
            status_code=502,
            detail="모델 호출이 차단되었습니다. Anthropic 키, 라우터 권한, 또는 현재 모델 접근 설정을 확인해 주세요.",
        ) from e
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


@app.get("/api/v1/standard-contracts")
def list_standard_contracts():
    return {"items": STANDARD_CONTRACT_RESOURCES}


def _register_frontend_routes() -> None:
    if not STATIC_DIR.is_dir():
        return

    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def serve_index():
        index = STATIC_DIR / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="UI build not found")
        return FileResponse(index)

    @app.get("/{file_path:path}")
    async def serve_static_or_spa(file_path: str):
        candidate = STATIC_DIR / file_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not Found")


_register_frontend_routes()
