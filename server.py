import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

COMPARISON_RESULTS: dict[str, dict] = {}
STANDARD_COMPARISON_RESULTS: dict[str, dict] = {}

from anthropic import PermissionDeniedError as AnthropicPermissionDeniedError

from pipeline import run_pipeline
from agents.file_extractor import extract_text, SUPPORTED_EXTENSIONS
from agents.mailer import send_expert_request
from agents.standard_contract_catalog import STANDARD_CONTRACT_RESOURCES
from agents.contract_templates import list_templates
from agents.contract_generator import generate_contract
from agents.fidic_comparison import compare_contract_to_fidic, generate_fidic_pdf_bytes
from agents.standard_contract_comparison import (
    compare_contract_to_standard,
    generate_standard_pdf_bytes,
    supported_contract_types,
)
from agents.regulatory_ontology import build_default_graph
from agents.regulatory_analyzer import run_regulatory_pipeline

REGULATORY_GRAPH = build_default_graph()

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
    "standard_contract_compare_error": {
        "ko": "표준계약서 비교 분석 중 오류가 발생했습니다: {err}",
        "en": "An error occurred during the standard contract comparison analysis: {err}",
    },
    "standard_contract_unsupported_type": {
        "ko": "지원하지 않는 계약유형입니다: {contract_type} (지원: {allowed})",
        "en": "Unsupported contract type: {contract_type} (supported: {allowed})",
    },
    "standard_contract_save_error": {
        "ko": "표준계약서 비교 결과 저장 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while saving the standard contract comparison result: {err}",
    },
    "standard_contract_not_found": {
        "ko": "저장된 비교 결과를 찾을 수 없습니다.",
        "en": "The saved comparison result could not be found.",
    },
    "standard_contract_delete_not_found": {
        "ko": "삭제할 저장 내역이 없습니다.",
        "en": "There is no saved item to delete.",
    },
    "standard_contract_export_pdf_error": {
        "ko": "표준계약서 비교표 내보내기 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while exporting the standard contract comparison report: {err}",
    },
    "regulatory_unsupported_sector": {
        "ko": "지원하지 않는 국가/업종 조합입니다: {country}/{sector} (지원: {allowed})",
        "en": "Unsupported country/sector combination: {country}/{sector} (supported: {allowed})",
    },
    "regulatory_analyze_error": {
        "ko": "인허가 분석 중 오류가 발생했습니다: {err}",
        "en": "An error occurred during the permitting analysis: {err}",
    },
    "standard_contract_export_json_error": {
        "ko": "표준계약서 비교 JSON 내보내기 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while exporting the standard contract comparison JSON: {err}",
    },
    "standard_contract_export_csv_error": {
        "ko": "표준계약서 비교 CSV 내보내기 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while exporting the standard contract comparison CSV: {err}",
    },
    "standard_contract_export_excel_error": {
        "ko": "표준계약서 비교 Excel 내보내기 중 오류가 발생했습니다: {err}",
        "en": "An error occurred while exporting the standard contract comparison Excel file: {err}",
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


_STANDARD_CSV_HEADERS = {
    "ko": "항목,점수,상태,기준,권장사항",
    "en": "Item,Score,Status,Benchmark,Recommendation",
}

_STANDARD_EXCEL_LABELS = {
    "ko": {
        "sheet_result": "비교 결과",
        "headers": ["항목", "점수", "상태", "기준", "권장사항"],
        "sheet_summary": "요약",
        "summary_headers": ["항목", "값"],
        "overall_score": "전체 점수",
        "balance": "계약 편향",
        "summary": "요약",
    },
    "en": {
        "sheet_result": "Comparison Result",
        "headers": ["Item", "Score", "Status", "Benchmark", "Recommendation"],
        "sheet_summary": "Summary",
        "summary_headers": ["Item", "Value"],
        "overall_score": "Overall Score",
        "balance": "Contract Balance",
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


class StandardContractComparisonBody(BaseModel):
    contract_text: str
    contract_type: str
    language: Literal["ko", "en"] = "ko"


class StandardContractComparisonSaveBody(StandardContractComparisonBody):
    comparison_id: str | None = None
    user_id: str | None = None


class BatchDeleteBody(BaseModel):
    comparison_ids: list[str]


class RegulatoryAnalyzeBody(BaseModel):
    project_name: str
    country: str
    sector: str
    submitted: dict[str, str] = {}
    language: Literal["ko", "en"] = "ko"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ContractChatBody(BaseModel):
    contract_summary: str
    clauses_context: str
    messages: list[ChatMessage]
    language: Literal["ko", "en"] = "ko"


@app.get("/health")
def health():
    import os
    from agents.llm_client import _TIER_MODELS, _IS_COPA, _OPENAI_CLIENT
    return {
        "status": "ok",
        "models": _TIER_MODELS,
        "is_copa": _IS_COPA,
        "openai_base_url": os.environ.get("OPENAI_BASE_URL", "(not set)"),
        "openai_client_configured": _OPENAI_CLIENT is not None,
    }


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


class AnalyzeTextBody(BaseModel):
    text: str
    language: str = "ko"


@app.post("/api/v1/contracts/analyze-text")
def analyze_contract_text(body: AnalyzeTextBody):
    language = body.language if body.language in ("ko", "en") else "ko"
    if not body.text.strip():
        raise HTTPException(status_code=400, detail=_msg("unsupported_file_type", language, ext="(text)", allowed="text"))
    try:
        report = run_pipeline(body.text, language=language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AnthropicPermissionDeniedError as e:
        raise HTTPException(status_code=502, detail=_msg("model_blocked", language)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=_msg("analyze_error", language, err=e))
    return report


@app.get("/api/v1/regulatory/sectors")
def list_regulatory_sectors():
    return {"items": REGULATORY_GRAPH.supported_sectors()}


def _require_supported_sector(country: str, sector: str, language: str) -> list[dict]:
    requirements = REGULATORY_GRAPH.requirements(country, sector)
    if not requirements:
        allowed = REGULATORY_GRAPH.supported_sectors()
        raise HTTPException(
            status_code=400,
            detail=_msg(
                "regulatory_unsupported_sector",
                language,
                country=country,
                sector=sector,
                allowed=", ".join(f"{p['country']}/{p['sector']}" for p in allowed),
            ),
        )
    return requirements


@app.get("/api/v1/regulatory/requirements")
def list_regulatory_requirements(country: str, sector: str, language: Literal["ko", "en"] = "ko"):
    return {"items": _require_supported_sector(country, sector, language)}


@app.post("/api/v1/regulatory/analyze")
def analyze_regulatory(body: RegulatoryAnalyzeBody):
    _require_supported_sector(body.country, body.sector, body.language)
    try:
        return run_regulatory_pipeline(
            body.project_name, body.country, body.sector, body.submitted,
            REGULATORY_GRAPH, language=body.language,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("regulatory_analyze_error", body.language, err=e))


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


def _require_supported_contract_type(contract_type: str, language: str) -> None:
    if contract_type not in supported_contract_types():
        raise HTTPException(
            status_code=400,
            detail=_msg(
                "standard_contract_unsupported_type",
                language,
                contract_type=contract_type,
                allowed=", ".join(supported_contract_types()),
            ),
        )


@app.post("/api/v1/standard-contracts/compare")
def compare_contract_with_standard(body: StandardContractComparisonBody):
    _require_supported_contract_type(body.contract_type, body.language)
    try:
        return compare_contract_to_standard(body.contract_text, body.contract_type, language=body.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("standard_contract_compare_error", body.language, err=e))


@app.post("/api/v1/standard-contracts/compare/save")
def save_standard_contract_comparison(body: StandardContractComparisonSaveBody):
    _require_supported_contract_type(body.contract_type, body.language)
    try:
        result = compare_contract_to_standard(body.contract_text, body.contract_type, language=body.language)
        comparison_id = body.comparison_id or f"std-{body.contract_type}-{len(STANDARD_COMPARISON_RESULTS) + 1}"
        payload = {
            "id": comparison_id,
            "comparison_id": comparison_id,
            "user_id": body.user_id,
            "contract_text": body.contract_text,
            **result,
        }
        STANDARD_COMPARISON_RESULTS[comparison_id] = payload
        return {"comparison_id": comparison_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("standard_contract_save_error", body.language, err=e))


@app.get("/api/v1/standard-contracts/compare/history")
def list_standard_contract_comparison_history(contract_type: str | None = None):
    items = list(STANDARD_COMPARISON_RESULTS.values())
    if contract_type:
        items = [item for item in items if item.get("contract_type") == contract_type]
    return {"items": items}


@app.get("/api/v1/standard-contracts/compare/history/{comparison_id}")
def get_standard_contract_comparison_history_item(comparison_id: str, language: str = "ko"):
    language = language if language in ("ko", "en") else "ko"
    item = STANDARD_COMPARISON_RESULTS.get(comparison_id)
    if not item:
        raise HTTPException(status_code=404, detail=_msg("standard_contract_not_found", language))
    return item


@app.delete("/api/v1/standard-contracts/compare/history/batch-delete")
def batch_delete_standard_contract_comparison(body: BatchDeleteBody):
    deleted_count = 0
    for cid in body.comparison_ids:
        if cid in STANDARD_COMPARISON_RESULTS:
            del STANDARD_COMPARISON_RESULTS[cid]
            deleted_count += 1
    return {"deleted": True, "deleted_count": deleted_count, "total_requested": len(body.comparison_ids)}


@app.delete("/api/v1/standard-contracts/compare/history/{comparison_id}")
def delete_standard_contract_comparison_history_item(comparison_id: str, language: str = "ko"):
    language = language if language in ("ko", "en") else "ko"
    if comparison_id not in STANDARD_COMPARISON_RESULTS:
        raise HTTPException(status_code=404, detail=_msg("standard_contract_delete_not_found", language))
    del STANDARD_COMPARISON_RESULTS[comparison_id]
    return {"deleted": True, "comparison_id": comparison_id}


@app.post("/api/v1/standard-contracts/compare/export")
def export_standard_contract_comparison(body: StandardContractComparisonBody):
    _require_supported_contract_type(body.contract_type, body.language)
    try:
        comparison = compare_contract_to_standard(body.contract_text, body.contract_type, language=body.language)
        pdf_bytes = generate_standard_pdf_bytes(comparison, language=body.language)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=standard-contract-comparison-report.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("standard_contract_export_pdf_error", body.language, err=e))


@app.post("/api/v1/standard-contracts/compare/export-json")
def export_standard_contract_comparison_json(body: StandardContractComparisonBody):
    _require_supported_contract_type(body.contract_type, body.language)
    try:
        comparison = compare_contract_to_standard(body.contract_text, body.contract_type, language=body.language)
        payload = json.dumps(comparison, ensure_ascii=False, indent=2)
        return Response(
            content=payload.encode("utf-8"),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=standard-contract-comparison-report.json"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("standard_contract_export_json_error", body.language, err=e))


@app.post("/api/v1/standard-contracts/compare/export-csv")
def export_standard_contract_comparison_csv(body: StandardContractComparisonBody):
    _require_supported_contract_type(body.contract_type, body.language)
    try:
        comparison = compare_contract_to_standard(body.contract_text, body.contract_type, language=body.language)

        lines = [_STANDARD_CSV_HEADERS.get(body.language, _STANDARD_CSV_HEADERS["ko"])]
        for issue in comparison.get("issues", []):
            lines.append(
                f"\"{issue.get('label', '')}\","
                f"\"{issue.get('score', '')}\","
                f"\"{issue.get('status', '')}\","
                f"\"{issue.get('benchmark', '').replace(chr(34), chr(34) + chr(34))}\","
                f"\"{issue.get('recommendation', '').replace(chr(34), chr(34) + chr(34))}\""
            )

        csv_content = "\n".join(lines)
        return Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=standard-contract-comparison-report.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("standard_contract_export_csv_error", body.language, err=e))


@app.post("/api/v1/standard-contracts/compare/export-excel")
def export_standard_contract_comparison_excel(body: StandardContractComparisonBody):
    _require_supported_contract_type(body.contract_type, body.language)
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        comparison = compare_contract_to_standard(body.contract_text, body.contract_type, language=body.language)
        excel_labels = _STANDARD_EXCEL_LABELS.get(body.language, _STANDARD_EXCEL_LABELS["ko"])

        wb = Workbook()
        ws = wb.active
        ws.title = excel_labels["sheet_result"]

        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 10
        ws.column_dimensions["D"].width = 40
        ws.column_dimensions["E"].width = 30

        headers = excel_labels["headers"]
        ws.append(headers)

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(wrap_text=True, vertical="center")

        for issue in comparison.get("issues", []):
            ws.append([
                issue.get("label", ""),
                issue.get("score", ""),
                issue.get("status", ""),
                issue.get("benchmark", ""),
                issue.get("recommendation", ""),
            ])

        ws_summary = wb.create_sheet(excel_labels["sheet_summary"])
        ws_summary.append(excel_labels["summary_headers"])
        ws_summary.append([excel_labels["overall_score"], comparison.get("overall_score", "")])
        ws_summary.append([excel_labels["balance"], comparison.get("balance", "")])
        ws_summary.append([excel_labels["summary"], comparison.get("summary", "")])

        ws_summary.column_dimensions["A"].width = 25
        ws_summary.column_dimensions["B"].width = 50

        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=standard-contract-comparison-report.xlsx"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_msg("standard_contract_export_excel_error", body.language, err=e))


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


@app.delete("/api/v1/fidic/compare/history/batch-delete")
def batch_delete_fidic_comparison(body: BatchDeleteBody):
    deleted_count = 0
    for cid in body.comparison_ids:
        if cid in COMPARISON_RESULTS:
            del COMPARISON_RESULTS[cid]
            deleted_count += 1
    return {"deleted": True, "deleted_count": deleted_count, "total_requested": len(body.comparison_ids)}


@app.delete("/api/v1/fidic/compare/history/{comparison_id}")
def delete_fidic_comparison_history_item(comparison_id: str, language: str = "ko"):
    language = language if language in ("ko", "en") else "ko"
    if comparison_id not in COMPARISON_RESULTS:
        raise HTTPException(status_code=404, detail=_msg("fidic_delete_not_found", language))
    del COMPARISON_RESULTS[comparison_id]
    return {"deleted": True, "comparison_id": comparison_id}


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

_CHAT_SYSTEM_KO = """당신은 계약서 위험 분석 AI 어시스턴트입니다.
사용자가 업로드한 계약서의 분석 결과를 바탕으로, 지속적인 협상 지원을 제공합니다.

[역할 및 원칙]
- 계약서 내용, 위험 조항, 협상 포인트에 대한 질문에 구체적으로 답변합니다.
- 법적 조언이 아닌 분석/의견 형태로 제공합니다. 최종 법적 판단은 전문 변호사와 확인하도록 안내합니다.
- 구체적인 조항 인용, 대안 문구, 협상 전략을 제시할 때는 근거를 명확히 합니다.
- 한국어로 답변하되, 법률 용어는 영문 원어도 병기합니다.

[계약서 분석 컨텍스트]
{context}
"""

_CHAT_SYSTEM_EN = """You are a contract risk analysis AI assistant.
Based on the analyzed results of the contract uploaded by the user, you provide ongoing negotiation support.

[Role & Principles]
- Provide specific answers about contract content, risk clauses, and negotiation points.
- Provide analysis/opinions, not legal advice. Always recommend final legal judgment with a qualified attorney.
- When citing specific clauses, alternative language, or negotiation strategies, make the basis clear.
- Respond in English.

[Contract Analysis Context]
{context}
"""


@app.post("/api/v1/contracts/chat")
def contract_chat(body: ContractChatBody):
    from agents.llm_client import TIER_AGENT

    context = f"계약서 요약:\n{body.contract_summary}\n\n주요 조항 분석:\n{body.clauses_context}"
    system_template = _CHAT_SYSTEM_KO if body.language == "ko" else _CHAT_SYSTEM_EN
    system = system_template.format(context=context)

    history_lines = []
    for msg in body.messages[:-1]:
        prefix = "사용자" if msg.role == "user" else "어시스턴트"
        history_lines.append(f"[{prefix}] {msg.content}")

    last_user_msg = body.messages[-1].content if body.messages else ""
    history_text = "\n".join(history_lines)
    user_prompt = f"{history_text}\n\n[사용자] {last_user_msg}" if history_text else last_user_msg

    try:
        from agents.llm_client import chat as llm_chat
        reply = llm_chat(system, user_prompt, temperature=0.3, tier=TIER_AGENT)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"채팅 응답 생성 중 오류가 발생했습니다: {e}")


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
