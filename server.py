import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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


_ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "unsupported_file_type": {
        "ko": "지원하지 않는 파일 형식입니다: {ext} (지원 형식: {allowed})",
        "en": "Unsupported file type: {ext} (supported types: {allowed})",
    },
    "model_blocked": {
        "ko": "모델 호출이 차단되었습니다. Anthropic 키, 라우터 권한, 또는 현재 모델 접근 설정을 확인해 주세요.",
        "en": "The model call was blocked. Please check your Anthropic key, router permissions, or current model access settings.",
    },
    "analyze_error": {
        "ko": "분석 중 오류가 발생했습니다: {err}",
        "en": "An error occurred during analysis: {err}",
    },
    "expert_request_error": {
        "ko": "전문가 연결 요청 메일 발송에 실패했습니다: {err}",
        "en": "Failed to send the expert-connection request email: {err}",
    },
    "contract_draft_error": {
        "ko": "계약서 초안 생성 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while generating the contract draft: {err}",
    },
    "fidic_compare_error": {
        "ko": "FIDIC 비교 분석 중 오류가 발생했습니다: {err}",
        "en": "An error occurred during the FIDIC comparison analysis: {err}",
    },
    "fidic_save_error": {
        "ko": "FIDIC 비교 결과 저장 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while saving the FIDIC comparison result: {err}",
    },
    "fidic_not_found": {
        "ko": "저장된 비교 결과를 찾을 수 없습니다.",
        "en": "The saved comparison result could not be found.",
    },
    "fidic_delete_not_found": {
        "ko": "삭제할 저장 내역이 없습니다.",
        "en": "There is no saved item to delete.",
    },
    "fidic_export_pdf_error": {
        "ko": "FIDIC 비교표 내보내기 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while exporting the FIDIC comparison report: {err}",
    },
    "fidic_export_json_error": {
        "ko": "FIDIC 비교 JSON 내보내기 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while exporting the FIDIC comparison JSON: {err}",
    },
    "fidic_export_csv_error": {
        "ko": "FIDIC CSV 내보내기 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while exporting the FIDIC comparison CSV: {err}",
    },
    "fidic_export_excel_error": {
        "ko": "FIDIC Excel 내보내기 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while exporting the FIDIC comparison Excel file: {err}",
    },
}


def _msg(key: str, language: str, **kwargs) -> str:
    entry = _ERROR_MESSAGES.get(key, {})
    template = entry.get(language, entry.get("ko", ""))
    return template.format(**kwargs)


_CSV_HEADERS = {
    "ko": "항목,점수,상태,FIDIC 기준,권장사항",
    "en": "Item,Score,Status,FIDIC Benchmark,Recommendation",
}

_EXCEL_LABELS = {
    "ko": {
        "sheet_result": "비교 결과",
        "headers": ["항목", "점수", "상태", "FIDIC 기준", "권장사항"],
        "sheet_summary": "요약",
        "summary_headers": ["항목", "값"],
        "overall_score": "전체 점수",
        "balance": "계약 편향",
        "employer_bias": "발주자 편향 점수",
        "contractor_bias": "시공사 편향 점수",
        "summary": "요약",
    },
    "en": {
        "sheet_result": "Comparison Result",
        "headers": ["Item", "Score", "Status", "FIDIC Benchmark", "Recommendation"],
        "sheet_summary": "Summary",
        "summary_headers": ["Item", "Value"],
        "overall_score": "Overall Score",
        "balance": "Contract Balance",
        "employer_bias": "Employer Bias Score",
        "contractor_bias": "Contractor Bias Score",
        "summary": "Summary",
    },
}


class ExpertRequestBody(BaseModel):
    request_type: Literal["translation_review", "legal_expert"]
    language: Literal["ko", "en"] = "ko"


class ContractGenerateBody(BaseModel):
    answers: dict[str, str] = {}
    language: Literal["ko", "en"] = "ko"


class FIDICComparisonBody(BaseModel):
    contract_text: str
    language: Literal["ko", "en"] = "ko"


class FIDICComparisonSaveBody(FIDICComparisonBody):
    comparison_id: str | None = None
    user_id: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/contracts/analyze")
async def analyze_contract(file: UploadFile = File(...), language: str = Form("ko")):
    language = language if language in ("ko", "en") else "ko"
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=_msg("unsupported_file_type", language, ext=ext, allowed=allowed))

    contents = await file.read()

    try:
        raw_text = extract_text(contents, file.filename)
        report = run_pipeline(raw_text, language=language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnthropicPermissionDeniedError as e:
        raise HTTPException(
            status_code=502,
            detail=_msg("model_blocked", language),
        ) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=_msg("analyze_error", language, err=e))

    return report


@app.post("/api/v1/expert-requests")
def create_expert_request(body: ExpertRequestBody):
    try:
        return send_expert_request(body.request_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=_msg("expert_request_error", body.language, err=e))


@app.get("/api/v1/standard-contracts")
def list_standard_contracts():
    return {"items": STANDARD_CONTRACT_RESOURCES}


@app.get("/api/v1/contract-templates")
def list_contract_templates():
    return {"items": list_templates()}


@app.post("/api/v1/contract-templates/{template_id}/generate")
def create_contract_draft(template_id: str, body: ContractGenerateBody):
    try:
        return generate_contract(template_id, body.answers, language=body.language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnthropicPermissionDeniedError as e:
        raise HTTPException(
            status_code=502,
            detail=_msg("model_blocked", body.language),
        ) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=_msg("contract_draft_error", body.language, err=e))


@app.post("/api/v1/fidic/compare")
def compare_contract_with_fidic(body: FIDICComparisonBody):
    try:
        result = compare_contract_to_fidic(body.contract_text, language=body.language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("fidic_compare_error", body.language, err=e))


@app.post("/api/v1/fidic/compare/save")
def save_fidic_comparison(body: FIDICComparisonSaveBody):
    try:
        result = compare_contract_to_fidic(body.contract_text, language=body.language)
        comparison_id = body.comparison_id or f"fidic-{len(COMPARISON_RESULTS) + 1}"
        payload = {
            "id": comparison_id,
            "comparison_id": comparison_id,
            "user_id": body.user_id,
            "contract_text": body.contract_text,
            **result,
        }
        COMPARISON_RESULTS[comparison_id] = payload
        return {"comparison_id": comparison_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("fidic_save_error", body.language, err=e))


@app.get("/api/v1/fidic/compare/history")
def list_fidic_comparison_history():
    return {"items": list(COMPARISON_RESULTS.values())}


@app.get("/api/v1/fidic/compare/history/{comparison_id}")
def get_fidic_comparison_history_item(comparison_id: str, language: str = "ko"):
    language = language if language in ("ko", "en") else "ko"
    item = COMPARISON_RESULTS.get(comparison_id)
    if not item:
        raise HTTPException(status_code=404, detail=_msg("fidic_not_found", language))
    return item


@app.delete("/api/v1/fidic/compare/history/{comparison_id}")
def delete_fidic_comparison_history_item(comparison_id: str, language: str = "ko"):
    language = language if language in ("ko", "en") else "ko"
    if comparison_id not in COMPARISON_RESULTS:
        raise HTTPException(status_code=404, detail=_msg("fidic_delete_not_found", language))
    del COMPARISON_RESULTS[comparison_id]
    return {"deleted": True, "comparison_id": comparison_id}


class BatchDeleteBody(BaseModel):
    comparison_ids: list[str]


@app.delete("/api/v1/fidic/compare/history/batch-delete")
def batch_delete_fidic_comparison(body: BatchDeleteBody):
    deleted_count = 0
    for cid in body.comparison_ids:
        if cid in COMPARISON_RESULTS:
            del COMPARISON_RESULTS[cid]
            deleted_count += 1
    return {"deleted": True, "deleted_count": deleted_count, "total_requested": len(body.comparison_ids)}


@app.post("/api/v1/fidic/compare/export")
def export_fidic_comparison(body: FIDICComparisonBody):
    try:
        comparison = compare_contract_to_fidic(body.contract_text, language=body.language)
        pdf_bytes = generate_fidic_pdf_bytes(comparison, language=body.language)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=fidic-comparison-report.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("fidic_export_pdf_error", body.language, err=e))


@app.post("/api/v1/fidic/compare/export-json")
def export_fidic_comparison_json(body: FIDICComparisonBody):
    try:
        comparison = compare_contract_to_fidic(body.contract_text, language=body.language)
        payload = json.dumps(comparison, ensure_ascii=False, indent=2)
        return Response(
            content=payload.encode("utf-8"),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=fidic-comparison-report.json"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("fidic_export_json_error", body.language, err=e))

@app.post("/api/v1/fidic/compare/export-csv")
def export_fidic_comparison_csv(body: FIDICComparisonBody):
    try:
        comparison = compare_contract_to_fidic(body.contract_text, language=body.language)

        # Build CSV content
        lines = [
            _CSV_HEADERS.get(body.language, _CSV_HEADERS["ko"]),
        ]

        for issue in comparison.get("issues", []):
            lines.append(
                f"\"{issue.get('label', '')}\","
                f"\"{issue.get('score', '')}\","
                f"\"{issue.get('status', '')}\","
                f"\"{issue.get('fidic_benchmark', '').replace(chr(34), chr(34) + chr(34))}\","
                f"\"{issue.get('recommendation', '').replace(chr(34), chr(34) + chr(34))}\""
            )

        csv_content = "\n".join(lines)
        return Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=fidic-comparison-report.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("fidic_export_csv_error", body.language, err=e))


@app.post("/api/v1/fidic/compare/export-excel")
def export_fidic_comparison_excel(body: FIDICComparisonBody):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        comparison = compare_contract_to_fidic(body.contract_text, language=body.language)
        excel_labels = _EXCEL_LABELS.get(body.language, _EXCEL_LABELS["ko"])

        wb = Workbook()
        ws = wb.active
        ws.title = excel_labels["sheet_result"]

        # Set column widths
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 10
        ws.column_dimensions["D"].width = 40
        ws.column_dimensions["E"].width = 30

        # Header row
        headers = excel_labels["headers"]
        ws.append(headers)

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(wrap_text=True, vertical="center")

        # Data rows
        for issue in comparison.get("issues", []):
            ws.append([
                issue.get("label", ""),
                issue.get("score", ""),
                issue.get("status", ""),
                issue.get("fidic_benchmark", ""),
                issue.get("recommendation", ""),
            ])

        # Summary sheet
        ws_summary = wb.create_sheet(excel_labels["sheet_summary"])
        ws_summary.append(excel_labels["summary_headers"])
        ws_summary.append([excel_labels["overall_score"], comparison.get("overall_score", "")])
        ws_summary.append([excel_labels["balance"], comparison.get("balance", "")])
        ws_summary.append([excel_labels["employer_bias"], comparison.get("bias_scores", {}).get("employer", "")])
        ws_summary.append([excel_labels["contractor_bias"], comparison.get("bias_scores", {}).get("contractor", "")])
        ws_summary.append([excel_labels["summary"], comparison.get("summary", "")])

        ws_summary.column_dimensions["A"].width = 25
        ws_summary.column_dimensions["B"].width = 50

        # Write to bytes
        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=fidic-comparison-report.xlsx"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("fidic_export_excel_error", body.language, err=e))

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
