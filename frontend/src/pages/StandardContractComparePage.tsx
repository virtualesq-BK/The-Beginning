import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  compareDraftToStandardAPI,
  exportStandardContractComparisonCSV,
  exportStandardContractComparisonExcel,
  exportStandardContractComparisonJSON,
  exportStandardContractComparisonPDF,
  saveStandardContractComparisonResult,
  STANDARD_CONTRACT_TYPES,
  type StandardContractComparisonResponse,
  type StandardContractType,
} from "../lib/standardContractApi";

export function StandardContractComparePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [contractType, setContractType] = useState<StandardContractType>("distributor");
  const [contractTextInput, setContractTextInput] = useState<string>("");
  const [result, setResult] = useState<StandardContractComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCompare() {
    if (!contractTextInput.trim()) {
      setError(t("standardContractCompare.errors.emptyCompare"));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const comparison = await compareDraftToStandardAPI(contractTextInput, contractType);
      setResult(comparison);
      if (user) {
        await saveStandardContractComparisonResult(contractTextInput, contractType);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t("standardContractCompare.errors.compareFailed"));
    } finally {
      setLoading(false);
    }
  }

  async function handleExport(kind: "pdf" | "json" | "csv" | "excel") {
    if (!contractTextInput.trim()) {
      setError(t("standardContractCompare.errors.emptyExport"));
      return;
    }
    try {
      if (kind === "pdf") await exportStandardContractComparisonPDF(contractTextInput, contractType);
      if (kind === "json") await exportStandardContractComparisonJSON(contractTextInput, contractType);
      if (kind === "csv") await exportStandardContractComparisonCSV(contractTextInput, contractType);
      if (kind === "excel") await exportStandardContractComparisonExcel(contractTextInput, contractType);
    } catch (e) {
      const fallbackKey =
        kind === "pdf"
          ? "standardContractCompare.errors.exportFailed"
          : kind === "json"
            ? "standardContractCompare.errors.exportJsonFailed"
            : kind === "csv"
              ? "standardContractCompare.errors.exportCsvFailed"
              : "standardContractCompare.errors.exportExcelFailed";
      setError(e instanceof Error ? e.message : t(fallbackKey));
    }
  }

  return (
    <div className="min-h-screen bg-[var(--tb-sand)] text-[var(--tb-ink)]">
      <div className="sticky top-0 z-20 border-b border-[var(--tb-line)] bg-[var(--tb-sand)]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
              {t("standardContractCompare.eyebrow")}
            </p>
            <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight sm:text-3xl">
              {t("standardContractCompare.titleLine1")}
            </h1>
          </div>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)]"
          >
            {t("standardContractCompare.back")}
          </button>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="max-w-2xl text-sm leading-relaxed text-[var(--tb-muted)]">
          {t("standardContractCompare.subtitle")}
        </p>

        {user && (
          <button
            type="button"
            onClick={() => navigate("/standard-contract-history")}
            className="mt-4 text-sm font-semibold text-[var(--tb-green)] underline-offset-2 hover:underline"
          >
            {t("standardContractCompare.viewHistory")}
          </button>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-6 shadow-sm">
            <label className="block text-sm font-semibold text-[var(--tb-ink)]">
              {t("standardContractCompare.typeLabel")}
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              {STANDARD_CONTRACT_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setContractType(type)}
                  className={`rounded-full border px-3 py-1.5 text-sm ${
                    contractType === type
                      ? "border-[var(--tb-green)] bg-[var(--tb-green-soft)] text-[var(--tb-green-deep)]"
                      : "border-[var(--tb-line)] text-[var(--tb-muted)]"
                  }`}
                >
                  {t(`standardContractCompare.types.${type}`)}
                </button>
              ))}
            </div>

            <label className="mt-6 block text-sm font-semibold text-[var(--tb-ink)]">
              {t("standardContractCompare.pasteLabel")}
            </label>
            <textarea
              value={contractTextInput}
              onChange={(e) => setContractTextInput(e.target.value)}
              rows={12}
              placeholder={t("standardContractCompare.pastePlaceholder")}
              className="mt-3 w-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-4 py-3 text-sm leading-relaxed text-[var(--tb-ink)] focus:border-[var(--tb-green)] focus:outline-none"
            />

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleCompare}
                disabled={loading}
                className="bg-[var(--tb-green)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
              >
                {loading ? t("standardContractCompare.comparing") : t("standardContractCompare.compareCta")}
              </button>
              <button
                type="button"
                onClick={() => setContractTextInput("")}
                className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
              >
                {t("standardContractCompare.reset")}
              </button>
              {result && (
                <>
                  <button
                    type="button"
                    onClick={() => void handleExport("pdf")}
                    className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                  >
                    {t("standardContractCompare.exportPdf")}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleExport("json")}
                    className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                  >
                    {t("standardContractCompare.exportJson")}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleExport("csv")}
                    className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                  >
                    {t("standardContractCompare.exportCsv")}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleExport("excel")}
                    className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                  >
                    {t("standardContractCompare.exportExcel")}
                  </button>
                </>
              )}
            </div>

            {error && (
              <div className="mt-4 border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>
            )}
          </div>

          <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-6 shadow-sm">
            {result ? (
              <>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--tb-green)]">
                  {t("standardContractCompare.matchScoreLabel")}
                </p>
                <div className="mt-4 flex items-end gap-3">
                  <span className="font-display text-5xl font-semibold text-[var(--tb-ink)]">
                    {result.overall_score}
                  </span>
                  <span className="pb-2 text-sm text-[var(--tb-muted)]">
                    {t("standardContractCompare.scoreOutOf")}
                  </span>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-[var(--tb-muted)]">{result.summary}</p>
                {result.focus_areas.length > 0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {result.focus_areas.map((area) => (
                      <span
                        key={area}
                        className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
                      >
                        {area}
                      </span>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="flex h-full items-center justify-center text-sm leading-relaxed text-[var(--tb-muted)]">
                {t("standardContractCompare.emptyResult")}
              </div>
            )}
          </div>
        </div>

        {result && (
          <div className="mt-8 space-y-4">
            {result.issues.map((issue) => (
              <div key={issue.id} className="rounded-2xl border border-[var(--tb-line)] bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-[var(--tb-ink)]">{issue.label}</p>
                    <p className="mt-1 text-xs text-[var(--tb-muted)]">{issue.benchmark}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        issue.status === "good"
                          ? "bg-emerald-100 text-emerald-700"
                          : issue.status === "watch"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-rose-100 text-rose-700"
                      }`}
                    >
                      {t(`standardContractCompare.status.${issue.status}`)}
                    </span>
                    <span className="text-lg font-semibold text-[var(--tb-ink)]">{issue.score}</span>
                  </div>
                </div>
                <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-[var(--tb-sand)]">
                  <div
                    className={`h-full ${
                      issue.status === "good"
                        ? "bg-emerald-500"
                        : issue.status === "watch"
                          ? "bg-amber-500"
                          : "bg-rose-500"
                    }`}
                    style={{ width: `${issue.score}%` }}
                  />
                </div>
                {issue.sentence_evidence.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--tb-green)]">
                      {t("standardContractCompare.evidenceLabel")}
                    </p>
                    <ul className="space-y-2">
                      {issue.sentence_evidence.map((sentence) => (
                        <li
                          key={sentence}
                          className="rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2 text-sm leading-relaxed text-[var(--tb-ink)]"
                        >
                          {sentence}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="mt-4 text-sm leading-relaxed text-[var(--tb-muted)]">{issue.recommendation}</p>
              </div>
            ))}
          </div>
        )}

        {user && (
          <div className="mt-8 rounded-2xl border border-[var(--tb-line)] bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--tb-green)]">
                {t("standardContractCompare.mySavedHistory")}
              </p>
              <button
                type="button"
                onClick={() => navigate("/standard-contract-history")}
                className="text-xs font-semibold text-[var(--tb-green)] underline-offset-2 hover:underline"
              >
                {t("standardContractCompare.viewAll")}
              </button>
            </div>
            <p className="mt-2 text-sm text-[var(--tb-muted)]">{t("standardContractCompare.savedHistoryDesc")}</p>
          </div>
        )}
      </div>
    </div>
  );
}
