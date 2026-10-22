import type { ContractReport } from "../types";

function riskLabel(score: number): string {
  if (score >= 5) return "매우 높음";
  if (score >= 4) return "높음";
  if (score >= 3) return "중간";
  if (score >= 2) return "낮음";
  return "매우 낮음";
}

function riskColor(score: number): string {
  if (score >= 5) return "#dc2626";
  if (score >= 4) return "#ea580c";
  if (score >= 3) return "#d97706";
  return "#16a34a";
}

function esc(s: string): string {
  return (s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function downloadReportPDF(report: ContractReport): void {
  const dateStr = new Date(report.generated_at).toLocaleString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });

  const majorRisks = [...report.clauses]
    .filter((c) => c.risk.risk_score >= 3)
    .sort((a, b) => b.risk.risk_score - a.risk.risk_score);

  const checklistItems = report.clauses
    .filter((c) => c.risk.risk_score >= 3 && c.risk.recommendation)
    .sort((a, b) => b.risk.risk_score - a.risk.risk_score);

  const clauseRows = report.clauses
    .sort((a, b) => b.risk.risk_score - a.risk.risk_score)
    .map((c) => {
      const num = c.clause_number ? `${c.clause_number} ` : "";
      const color = riskColor(c.risk.risk_score);
      return `
        <div class="clause-card">
          <div class="clause-header">
            <span class="clause-type">${esc(c.clause_type)}</span>
            <span class="risk-badge" style="background:${color}">${c.risk.risk_score}/5 ${riskLabel(c.risk.risk_score)}</span>
          </div>
          <h3>${esc(num + c.title)}</h3>
          <p class="translated">${esc(c.translated_text ?? "")}</p>
          <table class="detail-table">
            <tr><td class="label">근거 인용</td><td><em>${esc(c.risk.evidence_quote ?? "")}</em></td></tr>
            <tr><td class="label">리스크 원인</td><td>${esc(c.risk.risk_reason ?? "")}</td></tr>
            ${c.risk.business_impact ? `<tr><td class="label">실무 영향</td><td>${esc(c.risk.business_impact)}</td></tr>` : ""}
            <tr><td class="label">수정 권고</td><td>${esc(c.risk.recommendation ?? "")}</td></tr>
            ${c.risk.negotiation_point ? `<tr><td class="label">협상 전략</td><td>${esc(c.risk.negotiation_point)}</td></tr>` : ""}
            ${c.risk.alternative_text ? `<tr><td class="label">대체 문구</td><td class="alt-text">${esc(c.risk.alternative_text)}</td></tr>` : ""}
          </table>
          ${c.risk.requires_lawyer_review ? '<p class="lawyer-warn">⚠ 법률 전문가 검토 필요</p>' : ""}
        </div>`;
    }).join("");

  const crossRows = (report.cross_clause_risks ?? []).map((combo) => `
    <div class="clause-card cross-risk">
      <div class="clause-header">
        <span class="risk-badge" style="background:#dc2626">${combo.combined_severity.toUpperCase()}</span>
        ${combo.matched_rules.map((r) => `<span class="rule-tag">${esc(r)}</span>`).join("")}
      </div>
      <p>${esc(combo.description)}</p>
      <table class="detail-table">
        <tr><td class="label">실무 영향</td><td>${esc(combo.business_impact)}</td></tr>
        <tr><td class="label">협상 우선순위</td><td>${esc(combo.negotiation_priority)}</td></tr>
      </table>
    </div>`).join("");

  const checkRows = checklistItems.map((c) => `
    <tr>
      <td>☐</td>
      <td><strong>${esc(c.title)}</strong><br><span style="color:#6b7280;font-size:12px">${esc(c.risk.recommendation)}</span></td>
      <td style="color:${riskColor(c.risk.risk_score)};white-space:nowrap">${c.risk.risk_score}/5</td>
    </tr>`).join("");

  const html = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>계약서 리스크 분석 리포트 — The Beginning</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: "Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif; font-size: 13px; color: #111; line-height: 1.6; padding: 32px; max-width: 900px; margin: 0 auto; }
  h1 { font-size: 22px; font-weight: 700; color: #12241c; }
  h2 { font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: #1f8a5b; margin: 28px 0 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
  h3 { font-size: 13px; font-weight: 700; color: #111; margin: 6px 0 4px; }
  .meta { font-size: 12px; color: #6b7280; margin-top: 4px; }
  .summary-box { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0; }
  .summary-box p { color: #374151; }
  .stats { display: flex; gap: 32px; margin-top: 10px; font-size: 12px; color: #6b7280; }
  .stats strong { font-size: 18px; font-weight: 700; }
  .clause-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 12px; break-inside: avoid; }
  .cross-risk { border-color: #fecaca; background: #fff5f5; }
  .clause-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
  .clause-type { font-size: 11px; font-weight: 600; color: #1f8a5b; background: #f0fdf4; padding: 2px 8px; border-radius: 99px; }
  .risk-badge { font-size: 11px; font-weight: 700; color: #fff; padding: 2px 8px; border-radius: 99px; }
  .rule-tag { font-size: 11px; background: #f3f4f6; color: #374151; padding: 2px 8px; border-radius: 99px; }
  .translated { color: #374151; font-size: 12px; margin: 6px 0 10px; }
  .detail-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .detail-table td { padding: 4px 6px; vertical-align: top; }
  .detail-table .label { font-weight: 700; color: #111; white-space: nowrap; width: 90px; }
  .alt-text { font-family: monospace; background: #f9fafb; border-radius: 4px; padding: 4px; font-size: 11px; color: #6b7280; }
  .lawyer-warn { margin-top: 8px; font-size: 12px; font-weight: 600; color: #b91c1c; background: #fff1f2; border-radius: 6px; padding: 6px 10px; }
  .checklist-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .checklist-table td { padding: 6px 8px; border-bottom: 1px solid #f3f4f6; vertical-align: top; }
  .disclaimer { font-size: 11px; color: #9ca3af; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px; margin-top: 24px; }
  .page-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 24px; border-bottom: 2px solid #1f8a5b; padding-bottom: 12px; }
  @media print {
    body { padding: 16px; }
    h2 { margin-top: 18px; }
    .clause-card { break-inside: avoid; }
    @page { margin: 1.5cm; size: A4; }
  }
</style>
</head>
<body>
  <div class="page-header">
    <div>
      <h1>계약서 리스크 분석 리포트</h1>
      <p class="meta">The Beginning &nbsp;·&nbsp; AI 계약서 검토 플랫폼</p>
    </div>
    <p class="meta" style="text-align:right">생성: ${esc(dateStr)}</p>
  </div>

  <h2>계약서 요약</h2>
  <div class="summary-box">
    <p>${esc(report.document_summary)}</p>
    <div class="stats">
      <div>총 조항 수 <strong>${report.clause_count}</strong>개</div>
      <div style="color:#dc2626">고위험 조항 <strong>${report.high_risk_count}</strong>개</div>
    </div>
  </div>

  <h2>주요 리스크 조항</h2>
  ${majorRisks.length === 0
    ? "<p style='color:#6b7280'>고위험 조항이 탐지되지 않았습니다.</p>"
    : majorRisks.map((c) => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#f9fafb;border-radius:6px;margin-bottom:6px;break-inside:avoid">
        <div>
          <strong>${esc(c.title)}</strong>
          <span style="font-size:11px;color:#6b7280;margin-left:8px">${esc(c.clause_type)}</span>
          <p style="font-size:12px;color:#6b7280;margin-top:2px">${esc(c.risk.risk_reason ?? "")}</p>
        </div>
        <span class="risk-badge" style="background:${riskColor(c.risk.risk_score)};flex-shrink:0;margin-left:12px">${c.risk.risk_score}/5</span>
      </div>`).join("")}

  <h2>전체 조항 상세 분석</h2>
  ${clauseRows || "<p style='color:#6b7280'>분석된 조항이 없습니다.</p>"}

  ${(report.cross_clause_risks ?? []).length > 0 ? `
  <h2>조항 복합 리스크</h2>
  ${crossRows}` : ""}

  <h2>협상 체크리스트</h2>
  ${checklistItems.length === 0
    ? "<p style='color:#6b7280'>체크리스트 항목이 없습니다.</p>"
    : `<table class="checklist-table">${checkRows}</table>`}

  <div class="disclaimer">
    <strong>면책 고지:</strong> ${esc(report.disclaimer)}
  </div>

  <script>window.onload = function(){ window.print(); }</script>
</body>
</html>`;

  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const win = window.open(url, "_blank");
  if (!win) {
    // 팝업 차단된 경우 직접 다운로드
    const a = document.createElement("a");
    a.href = url;
    a.download = `contract-report-${Date.now()}.html`;
    a.click();
  }
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
