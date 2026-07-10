import type { ContractReport } from "../types";
import { RiskBadge } from "./RiskBadge";
import { ClauseTypeIcon } from "./ClauseTypeIcon";

export function ReportView({ report }: { report: ContractReport }) {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
        ⚠ {report.disclaimer}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">
          계약서 요약
        </h2>
        <p className="leading-relaxed text-slate-700 dark:text-slate-200">
          {report.document_summary}
        </p>
        <div className="mt-4 flex gap-6 border-t border-slate-100 pt-4 text-sm dark:border-slate-800">
          <span className="text-slate-500 dark:text-slate-400">
            총 조항 <span className="font-semibold text-slate-900 dark:text-white">{report.clause_count}</span>건
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            고위험(4점 이상){" "}
            <span className="font-semibold text-rose-600 dark:text-rose-400">
              {report.high_risk_count}
            </span>
            건
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {report.clauses.map((clause) => (
          <div
            key={clause.id}
            className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950"
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <ClauseTypeIcon clauseType={clause.clause_type} />
                <div>
                  <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
                    {clause.clause_type}
                  </span>
                  <h3 className="font-semibold text-slate-900 dark:text-white">{clause.title}</h3>
                </div>
              </div>
              <RiskBadge score={clause.risk.risk_score} />
            </div>

            <p className="mb-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
              {clause.translated_text}
            </p>

            <div className="space-y-2 rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-900/60">
              <p>
                <span className="font-semibold text-slate-900 dark:text-white">위험 근거 </span>
                <span className="text-slate-600 dark:text-slate-300">{clause.risk.risk_reason}</span>
              </p>
              <p className="border-l-2 border-blue-200 pl-3 italic text-slate-500 dark:border-blue-800 dark:text-slate-400">
                “{clause.risk.evidence_quote}”
              </p>
              <p>
                <span className="font-semibold text-slate-900 dark:text-white">수정 권고 </span>
                <span className="text-slate-600 dark:text-slate-300">{clause.risk.recommendation}</span>
              </p>
              {clause.risk.references && clause.risk.references.length > 0 && (
                <p className="pt-1 text-xs text-slate-400 dark:text-slate-500">
                  근거 출처: {clause.risk.references.join(", ")}
                </p>
              )}
            </div>

            {clause.risk.requires_lawyer_review && (
              <div className="mt-3 flex items-center gap-2 rounded-xl bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                <span aria-hidden>⚠</span>
                이 조항은 위험도 4점 이상으로, 변호사 검토를 권고합니다.
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
