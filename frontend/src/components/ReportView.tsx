import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Clause, ContractReport } from "../types";
import { requestExpert, openExpertMailto, type ExpertRequestType } from "../lib/api";
import { RiskBadge } from "./RiskBadge";
import { ClauseTypeIcon } from "./ClauseTypeIcon";
import { useAuth } from "../contexts/AuthContext";

const EXPERT_EMAIL = "virtual.esq@gmail.com";

function ClauseDetailCard({ clause }: { clause: Clause }) {
  const { t } = useTranslation();
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
        {clause.risk.rules_applied && clause.risk.rules_applied.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pb-1">
            {clause.risk.rules_applied.map((ruleId) => (
              <span
                key={ruleId}
                className="rounded-full bg-[var(--tb-green)]/10 px-2.5 py-0.5 text-xs font-medium text-[var(--tb-green-deep)] dark:bg-[var(--tb-green)]/20"
                title={t("report.clauseDetail.ruleAppliedTooltip")}
              >
                {ruleId}
              </span>
            ))}
          </div>
        )}
        <p className="border-l-2 border-[var(--tb-green)]/30 pl-3 italic text-slate-500">
          “{clause.risk.evidence_quote}”
        </p>
        <p>
          <span className="font-semibold text-slate-900 dark:text-white">{t("report.clauseDetail.riskReason")} </span>
          <span className="text-slate-600 dark:text-slate-300">{clause.risk.risk_reason}</span>
        </p>
        {clause.risk.business_impact && (
          <p>
            <span className="font-semibold text-slate-900 dark:text-white">{t("report.clauseDetail.businessImpact")} </span>
            <span className="text-slate-600 dark:text-slate-300">{clause.risk.business_impact}</span>
          </p>
        )}
        <p>
          <span className="font-semibold text-slate-900 dark:text-white">{t("report.clauseDetail.recommendation")} </span>
          <span className="text-slate-600 dark:text-slate-300">{clause.risk.recommendation}</span>
        </p>
        {clause.risk.negotiation_point && (
          <p>
            <span className="font-semibold text-slate-900 dark:text-white">{t("report.clauseDetail.negotiationPoint")} </span>
            <span className="text-slate-600 dark:text-slate-300">{clause.risk.negotiation_point}</span>
          </p>
        )}
        {clause.risk.alternative_text && (
          <p className="rounded-lg bg-white p-3 font-mono text-xs text-slate-500 dark:bg-slate-950 dark:text-slate-400">
            <span className="mb-1 block font-semibold text-slate-900 dark:text-white">
              {t("report.clauseDetail.alternativeText")}
            </span>
            {clause.risk.alternative_text}
          </p>
        )}
        {clause.risk.references && clause.risk.references.length > 0 && (
          <p className="pt-1 text-xs text-slate-400 dark:text-slate-500">
            {t("report.clauseDetail.references")}: {clause.risk.references.join(", ")}
          </p>
        )}
      </div>

      {clause.risk.requires_lawyer_review && (
        <div className="mt-3 flex items-center gap-2 rounded-xl bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
          <span aria-hidden>⚠</span>
          {t("report.clauseDetail.lawyerReviewWarning")}
        </div>
      )}
    </div>
  );
}

export function ReportView({ report }: { report: ContractReport }) {
  const { t } = useTranslation();
  const { requireAuth } = useAuth();
  const [showRiskDetails, setShowRiskDetails] = useState(false);
  const [showExpertOptions, setShowExpertOptions] = useState(false);
  const [expertStatus, setExpertStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [expertMessage, setExpertMessage] = useState<string | null>(null);

  function handleToggleRiskDetails() {
    if (showRiskDetails) {
      setShowRiskDetails(false);
      return;
    }
    if (!requireAuth(t("report.riskDetailsAuthRequired"))) {
      return;
    }
    setShowRiskDetails(true);
  }

  async function handleExpertRequest(requestType: ExpertRequestType) {
    const label =
      requestType === "translation_review" ? t("report.expert.translationReview") : t("report.expert.legalExpert");
    if (!requireAuth(t("report.expert.authRequired", { label }))) {
      return;
    }

    setExpertStatus("loading");
    setExpertMessage(null);
    try {
      await requestExpert(requestType);
      setExpertStatus("success");
      setExpertMessage(t("report.expert.successMessage", { email: EXPERT_EMAIL }));
    } catch (e) {
      // Fall back to opening the mail app directly if the server-side send fails
      openExpertMailto(requestType, EXPERT_EMAIL);
      setExpertStatus("error");
      const msg = e instanceof Error ? e.message : t("report.expert.genericError");
      setExpertMessage(
        msg.includes("Activate") || msg.includes("활성화")
          ? msg
          : t("report.expert.errorFallback", { msg, email: EXPERT_EMAIL }),
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
        {t("report.disclaimerPrefix")} {report.disclaimer}
      </div>

      {/* 1. Translation summary */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
          {t("report.translationSummary.heading")}
        </h2>
        <p className="leading-relaxed text-slate-700 dark:text-slate-200">
          {report.document_summary}
        </p>
        <div className="mt-4 flex gap-6 border-t border-slate-100 pt-4 text-sm dark:border-slate-800">
          <span className="text-slate-500 dark:text-slate-400">
            {t("report.translationSummary.totalClauses")}{" "}
            <span className="font-semibold text-slate-900 dark:text-white">
              {report.clause_count}
            </span>
            {t("report.translationSummary.clauseUnit")}
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            {t("report.translationSummary.highRisk")}{" "}
            <span className="font-semibold text-rose-600 dark:text-rose-400">
              {report.high_risk_count}
            </span>
            {t("report.translationSummary.highRiskUnit")}
          </span>
        </div>
      </section>

      {/* 2. Major risks */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
          {t("report.majorRisks.heading")}
        </h2>

        {majorRisks.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t("report.majorRisks.empty")}
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
          onClick={handleToggleRiskDetails}
          className="mt-5 inline-flex items-center gap-2 border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
        >
          {showRiskDetails ? t("report.majorRisks.showLess") : t("report.majorRisks.showMore")}
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

      {/* 2.5. Cross-clause combination risks */}
      {report.cross_clause_risks && report.cross_clause_risks.length > 0 && (
        <section className="rounded-2xl border border-rose-200 bg-rose-50/60 p-6 dark:border-rose-900/60 dark:bg-rose-950/20">
          <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-rose-700 dark:text-rose-300">
            {t("report.crossClauseRisks.heading")}
          </h2>
          <p className="mb-4 text-sm text-rose-700/80 dark:text-rose-300/80">
            {t("report.crossClauseRisks.desc")}
          </p>
          <ul className="space-y-4">
            {report.cross_clause_risks.map((combo) => (
              <li
                key={combo.combo_id}
                className="rounded-xl border border-rose-200 bg-white p-4 dark:border-rose-900/60 dark:bg-slate-950"
              >
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap gap-1.5">
                    {combo.matched_rules.map((ruleId) => (
                      <span
                        key={ruleId}
                        className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      >
                        {ruleId}
                      </span>
                    ))}
                  </div>
                  <span className="rounded-full bg-rose-600 px-3 py-0.5 text-xs font-semibold uppercase text-white">
                    {combo.combined_severity}
                  </span>
                </div>
                <p className="mb-2 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
                  {combo.description}
                </p>
                <p className="mb-1 text-sm">
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {t("report.crossClauseRisks.businessImpact")}{" "}
                  </span>
                  <span className="text-slate-600 dark:text-slate-300">{combo.business_impact}</span>
                </p>
                <p className="text-sm">
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {t("report.crossClauseRisks.negotiationPriority")}{" "}
                  </span>
                  <span className="text-slate-600 dark:text-slate-300">{combo.negotiation_priority}</span>
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* 3. Negotiation checklist */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
          {t("report.checklist.heading")}
        </h2>

        {checklistItems.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t("report.checklist.empty")}
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
                      {t("report.checklist.riskLevel", { score: item.score })}
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

      {/* 4. Expert connection */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
          {t("report.expert.heading")}
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          {t("report.expert.desc")}
        </p>

        <button
          type="button"
          onClick={() => setShowExpertOptions((v) => !v)}
          className="inline-flex items-center gap-2 bg-[var(--tb-green)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)]"
        >
          {t("report.expert.cta")}
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
                {t("report.expert.translationReview")}
              </button>
              <button
                type="button"
                disabled={expertStatus === "loading"}
                onClick={() => handleExpertRequest("legal_expert")}
                className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-5 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
              >
                {t("report.expert.legalExpert")}
              </button>
            </div>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              {t("report.expert.notifyLabel")}: {EXPERT_EMAIL}
            </p>
            {expertStatus === "loading" && (
              <p className="text-sm text-slate-500 dark:text-slate-400">{t("report.expert.sending")}</p>
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
