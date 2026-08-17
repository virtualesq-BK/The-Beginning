from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

COMPARISON_RESULTS: dict[str, dict] = {}

from anthropic import PermissionDeniedError as AnthropicPermissionDeniedError

from pipeline import run_pipeline
from agents.file_extractor import extract_text, SUPPORTED_EXTENSIONS
from agents.mailer import send_expert_request
from agents.standard_contract_catalog import STANDARD_CONTRACT_RESOURCES
from agents.contract_templates import list_templates
from agents.contract_generator import generate_contract
from agents.fidic_comparison import compare_contract_to_fidic, generate_fidic_pdf_bytes

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


class ContractGenerateBody(BaseModel):
    answers: dict[str, str] = {}


class FIDICComparisonBody(BaseModel):
    contract_text: str


class FIDICComparisonSaveBody(FIDICComparisonBody):
    comparison_id: str | None = None


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


@app.get("/api/v1/contract-templates")
def list_contract_templates():
    return {"items": list_templates()}


@app.post("/api/v1/contract-templates/{template_id}/generate")
def create_contract_draft(template_id: str, body: ContractGenerateBody):
    try:
        return generate_contract(template_id, body.answers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnthropicPermissionDeniedError as e:
        raise HTTPException(
            status_code=502,
            detail="모델 호출이 차단되었습니다. Anthropic 키, 라우터 권한, 또는 현재 모델 접근 설정을 확인해 주세요.",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"계약서 초안 생성 중 오류가 발생했습니다: {e}")


@app.post("/api/v1/fidic/compare")
def compare_contract_with_fidic(body: FIDICComparisonBody):
    try:
        result = compare_contract_to_fidic(body.contract_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FIDIC 비교 분석 중 오류가 발생했습니다: {e}")


@app.post("/api/v1/fidic/compare/save")
def save_fidic_comparison(body: FIDICComparisonSaveBody):
    try:
        result = compare_contract_to_fidic(body.contract_text)
        comparison_id = body.comparison_id or f"fidic-{len(COMPARISON_RESULTS) + 1}"
        COMPARISON_RESULTS[comparison_id] = {"id": comparison_id, **result}
        return {"comparison_id": comparison_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FIDIC 비교 결과 저장 중 오류가 발생했습니다: {e}")


@app.get("/api/v1/fidic/compare/history")
def list_fidic_comparison_history():
    return {"items": list(COMPARISON_RESULTS.values())}


@app.get("/api/v1/fidic/compare/history/{comparison_id}")
def get_fidic_comparison_history_item(comparison_id: str):
    item = COMPARISON_RESULTS.get(comparison_id)
    if not item:
        raise HTTPException(status_code=404, detail="저장된 비교 결과를 찾을 수 없습니다.")
    return item


@app.post("/api/v1/fidic/compare/export")
def export_fidic_comparison(body: FIDICComparisonBody):
    try:
        comparison = compare_contract_to_fidic(body.contract_text)
        pdf_bytes = generate_fidic_pdf_bytes(comparison)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=fidic-comparison-report.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FIDIC 비교표 내보내기 중 오류가 발생했습니다: {e}")


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
