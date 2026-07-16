import { useState } from "react";
import type { Clause, ContractReport } from "../types";
import { requestExpert, openExpertMailto, type ExpertRequestType } from "../lib/api";
import { RiskBadge } from "./RiskBadge";
import { ClauseTypeIcon } from "./ClauseTypeIcon";

const EXPERT_EMAIL = "virtual.esq@gmail.com";

function ClauseDetailCard({ clause }: { clause: Clause }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <ClauseTypeIcon clauseType={clause.clause_type} />
          <div>
            <span className="text-xs font-medium text-[var(--tb-green)]">
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
        <p className="border-l-2 border-[var(--tb-green)]/30 pl-3 italic text-slate-500">
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
  );
}

export function ReportView({ report }: { report: ContractReport }) {
  const [showRiskDetails, setShowRiskDetails] = useState(false);
  const [showExpertOptions, setShowExpertOptions] = useState(false);
  const [expertStatus, setExpertStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [expertMessage, setExpertMessage] = useState<string | null>(null);

  async function handleExpertRequest(requestType: ExpertRequestType) {
    setExpertStatus("loading");
    setExpertMessage(null);
    try {
      await requestExpert(requestType);
      setExpertStatus("success");
      setExpertMessage(`${EXPERT_EMAIL}로 요청 메일을 보냈습니다. 받은편지함(스팸함 포함)을 확인해 주세요.`);
    } catch (e) {
      // 서버 발송 실패 시 메일 앱으로 바로 연결
      openExpertMailto(requestType, EXPERT_EMAIL);
      setExpertStatus("error");
      const msg = e instanceof Error ? e.message : "전문가 연결 요청에 실패했습니다.";
      setExpertMessage(
        msg.includes("Activate") || msg.includes("활성화")
          ? msg
          : `${msg} 메일 앱이 열리면 ${EXPERT_EMAIL}로 전송해 주세요.`,
      );
    }
  }

  const majorRisks = [...report.clauses]
    .filter((c) => c.risk.risk_score >= 3)
    .sort((a, b) => b.risk.risk_score - a.risk.risk_score);

  const checklistItems = report.clauses
    .filter((c) => c.risk.risk_score >= 3 && c.risk.recommendation)
    .sort((a, b) => b.risk.risk_score - a.risk.risk_score)
    .map((c) => ({
      id: c.id,
      title: c.title,
      recommendation: c.risk.recommendation,
      score: c.risk.risk_score,
    }));

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
        ⚠ {report.disclaimer}
      </div>

      {/* 1. 번역 요약 */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
          번역 요약
        </h2>
        <p className="leading-relaxed text-slate-700 dark:text-slate-200">
          {report.document_summary}
        </p>
        <div className="mt-4 flex gap-6 border-t border-slate-100 pt-4 text-sm dark:border-slate-800">
          <span className="text-slate-500 dark:text-slate-400">
            총 조항{" "}
            <span className="font-semibold text-slate-900 dark:text-white">
              {report.clause_count}
            </span>
            건
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            고위험(4점 이상){" "}
            <span className="font-semibold text-rose-600 dark:text-rose-400">
              {report.high_risk_count}
            </span>
            건
          </span>
        </div>
      </section>

      {/* 2. 주요 리스크 */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
          주요 리스크
        </h2>

        {majorRisks.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            중위험 이상의 주요 리스크가 탐지되지 않았습니다.
          </p>
        ) : (
          <ul className="space-y-3">
            {majorRisks.slice(0, 5).map((clause) => (
              <li
                key={clause.id}
                className="flex items-start justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/60"
              >
                <div className="min-w-0">
                  <p className="font-medium text-slate-900 dark:text-white">{clause.title}</p>
                  <p className="mt-0.5 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">
                    {clause.risk.risk_reason}
                  </p>
                </div>
                <RiskBadge score={clause.risk.risk_score} />
              </li>
            ))}
          </ul>
        )}

        <button
          type="button"
          onClick={() => setShowRiskDetails((v) => !v)}
          className="mt-5 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
        >
          {showRiskDetails ? "주요 리스크 접기" : "주요 리스크 더보기"}
          <span aria-hidden>{showRiskDetails ? "↑" : "↓"}</span>
        </button>

        {showRiskDetails && (
          <div className="mt-6 space-y-4 border-t border-slate-100 pt-6 dark:border-slate-800">
            {report.clauses.map((clause) => (
              <ClauseDetailCard key={clause.id} clause={clause} />
            ))}
          </div>
        )}
      </section>

      {/* 3. 협상 체크리스트 */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
          협상 체크리스트
        </h2>

        {checklistItems.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            협상 시 별도 확인이 필요한 항목이 없습니다.
          </p>
        ) : (
          <ul className="space-y-3">
            {checklistItems.map((item) => (
              <li key={item.id} className="flex items-start gap-3">
                <span
                  className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-slate-300 text-xs text-slate-400 dark:border-slate-600"
                  aria-hidden
                >
                  ☐
                </span>
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">
                    {item.title}
                    <span className="ml-2 text-xs font-normal text-rose-600 dark:text-rose-400">
                      위험도 {item.score}/5
                    </span>
                  </p>
                  <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">
                    {item.recommendation}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 4. 전문가 연결 */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
          전문가 연결
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          AI 1차 검토 결과를 바탕으로 전문가 검수 또는 해외 법률 자문을 요청할 수 있습니다.
        </p>

        <button
          type="button"
          onClick={() => setShowExpertOptions((v) => !v)}
          className="inline-flex items-center gap-2 bg-[var(--tb-green)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)]"
        >
          전문가 연결
          <span aria-hidden>{showExpertOptions ? "↑" : "→"}</span>
        </button>

        {showExpertOptions && (
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={expertStatus === "loading"}
                onClick={() => handleExpertRequest("translation_review")}
                className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-5 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
              >
                전문가 번역 검수
              </button>
              <button
                type="button"
                disabled={expertStatus === "loading"}
                onClick={() => handleExpertRequest("legal_expert")}
                className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-5 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
              >
                해외 법률 전문가 연결
              </button>
            </div>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              요청 알림 수신: {EXPERT_EMAIL}
            </p>
            {expertStatus === "loading" && (
              <p className="text-sm text-slate-500 dark:text-slate-400">요청 메일 발송 중...</p>
            )}
            {expertMessage && (
              <p
                className={`text-sm ${
                  expertStatus === "error"
                    ? "text-rose-600 dark:text-rose-400"
                    : "text-emerald-700 dark:text-emerald-400"
                }`}
              >
                {expertMessage}
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
