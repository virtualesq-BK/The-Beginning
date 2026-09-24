import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  analyzeRegulatory,
  getRegulatoryRequirements,
  listRegulatorySectors,
  type RegulatoryReport,
  type RegulatoryRequirement,
  type RegulatorySector,
} from "../lib/regulatoryApi";

type DocStatus = "ready" | "insufficient" | "missing";

const STATUS_BADGE: Record<DocStatus, string> = {
  ready: "bg-emerald-100 text-emerald-700",
  insufficient: "bg-amber-100 text-amber-700",
  missing: "bg-rose-100 text-rose-700",
};

const sectorKey = (s: RegulatorySector) => `${s.country}:${s.sector}`;

export function RegulatoryAnalysisPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [sectors, setSectors] = useState<RegulatorySector[] | null>(null);
  const [selected, setSelected] = useState<RegulatorySector | null>(null);
  const [requirements, setRequirements] = useState<RegulatoryRequirement[]>([]);
  const [loadingRequirements, setLoadingRequirements] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [submitted, setSubmitted] = useState<Record<string, string>>({});
  const [report, setReport] = useState<RegulatoryReport | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listRegulatorySectors()
      .then(setSectors)
      .catch((e) => {
        setSectors([]);
        setError(e instanceof Error ? e.message : t("regulatory.errors.loadFailed"));
      });
  }, [t]);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoadingRequirements(true);
    getRegulatoryRequirements(selected)
      .then((items) => {
        if (!cancelled) setRequirements(items);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : t("regulatory.errors.loadFailed"));
      })
      .finally(() => {
        if (!cancelled) setLoadingRequirements(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected, t]);

  const documents = [...new Set(requirements.flatMap((r) => r.documents))];

  function selectSector(sector: RegulatorySector) {
    setSelected(sector);
    setRequirements([]);
    setSubmitted({});
    setReport(null);
    setError(null);
  }

  function reset() {
    setSubmitted({});
    setReport(null);
    setError(null);
  }

  async function handleAnalyze() {
    if (!projectName.trim()) {
      setError(t("regulatory.errors.noProjectName"));
      return;
    }
    if (!selected) {
      setError(t("regulatory.errors.noSector"));
      return;
    }
    const filled = Object.fromEntries(Object.entries(submitted).filter(([, text]) => text.trim()));
    setAnalyzing(true);
    setError(null);
    try {
      setReport(await analyzeRegulatory(projectName.trim(), selected, filled));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("regulatory.errors.analyzeFailed"));
    } finally {
      setAnalyzing(false);
    }
  }

  function docStatus(permit: string, document: string): DocStatus {
    return report?.gaps.find((g) => g.permit === permit && g.document === document)?.status ?? "ready";
  }

  const totals = report
    ? (() => {
        const required = report.requirements.reduce((n, r) => n + r.documents.length, 0);
        const missing = report.gaps.filter((g) => g.status === "missing").length;
        const insufficient = report.gaps.filter((g) => g.status === "insufficient").length;
        return { required, ready: required - missing - insufficient, insufficient, missing };
      })()
    : null;

  return (
    <div className="min-h-screen bg-[var(--tb-sand)] text-[var(--tb-ink)]">
      <div className="sticky top-0 z-20 border-b border-[var(--tb-line)] bg-[var(--tb-sand)]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
              {t("regulatory.eyebrow")}
            </p>
            <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight sm:text-3xl">
              {t("regulatory.title")}
            </h1>
          </div>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)]"
          >
            {t("regulatory.back")}
          </button>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="max-w-2xl text-sm leading-relaxed text-[var(--tb-muted)]">{t("regulatory.subtitle")}</p>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-6 shadow-sm">
            <label htmlFor="regulatory-project-name" className="block text-sm font-semibold text-[var(--tb-ink)]">
              {t("regulatory.projectNameLabel")}
            </label>
            <input
              id="regulatory-project-name"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder={t("regulatory.projectNamePlaceholder")}
              className="mt-3 w-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-4 py-2.5 text-sm text-[var(--tb-ink)] focus:border-[var(--tb-green)] focus:outline-none"
            />

            <p className="mt-6 text-sm font-semibold text-[var(--tb-ink)]">{t("regulatory.sectorLabel")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {sectors === null ? (
                <span className="text-sm text-[var(--tb-muted)]">{t("regulatory.loadingSectors")}</span>
              ) : (
                sectors.map((s) => (
                  <button
                    key={sectorKey(s)}
                    type="button"
                    aria-pressed={selected !== null && sectorKey(selected) === sectorKey(s)}
                    onClick={() => selectSector(s)}
                    className={`rounded-full border px-3 py-1.5 text-sm ${
                      selected && sectorKey(selected) === sectorKey(s)
                        ? "border-[var(--tb-green)] bg-[var(--tb-green-soft)] text-[var(--tb-green-deep)]"
                        : "border-[var(--tb-line)] text-[var(--tb-muted)]"
                    }`}
                  >
                    {t(`regulatory.countries.${s.country}`, s.country)} ·{" "}
                    {t(`regulatory.sectors.${s.sector}`, s.sector)}
                  </button>
                ))
              )}
            </div>

            <p className="mt-6 text-sm font-semibold text-[var(--tb-ink)]">{t("regulatory.documentsLabel")}</p>
            {!selected ? (
              <p className="mt-2 text-sm text-[var(--tb-muted)]">{t("regulatory.selectSectorFirst")}</p>
            ) : loadingRequirements ? (
              <p className="mt-2 text-sm text-[var(--tb-muted)]">{t("common.loading")}</p>
            ) : (
              <>
                <p className="mt-2 text-xs leading-relaxed text-[var(--tb-muted)]">{t("regulatory.documentsHint")}</p>
                <div className="mt-3 space-y-3">
                  {documents.map((doc, i) => (
                    <div key={doc}>
                      <label htmlFor={`regulatory-doc-${i}`} className="block text-xs font-semibold text-[var(--tb-ink)]">
                        {doc}
                      </label>
                      <textarea
                        id={`regulatory-doc-${i}`}
                        rows={2}
                        value={submitted[doc] ?? ""}
                        onChange={(e) => setSubmitted((prev) => ({ ...prev, [doc]: e.target.value }))}
                        placeholder={t("regulatory.documentPlaceholder")}
                        className="mt-1 w-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2 text-sm leading-relaxed text-[var(--tb-ink)] focus:border-[var(--tb-green)] focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </>
            )}

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={analyzing || !selected || loadingRequirements}
                className="bg-[var(--tb-green)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
              >
                {analyzing ? t("regulatory.analyzing") : t("regulatory.analyzeCta")}
              </button>
              <button
                type="button"
                onClick={reset}
                className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
              >
                {t("regulatory.reset")}
              </button>
            </div>

            {error && (
              <div role="alert" className="mt-4 border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {error}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-6 shadow-sm">
            {report && totals ? (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {(["required", "ready", "insufficient", "missing"] as const).map((key) => (
                    <div key={key} className="rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-3">
                      <p className="text-xs text-[var(--tb-muted)]">{t(`regulatory.summary.${key}`)}</p>
                      <p className="mt-1 font-display text-3xl font-semibold text-[var(--tb-ink)]">{totals[key]}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-5 border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-800">
                  {report.disclaimer}
                </p>
              </>
            ) : (
              <div className="flex h-full items-center justify-center text-sm leading-relaxed text-[var(--tb-muted)]">
                {t("regulatory.emptyResult")}
              </div>
            )}
          </div>
        </div>

        {report && (
          <ol className="mt-8 space-y-4">
            {report.requirements.map((req, i) => (
              <li key={req.permit} className="rounded-2xl border border-[var(--tb-line)] bg-white p-5 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--tb-green)]">
                  {t("regulatory.stepLabel", { n: i + 1 })}
                </p>
                <p className="mt-1 text-base font-semibold text-[var(--tb-ink)]">{req.permit}</p>
                <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-[auto_1fr] sm:gap-x-4">
                  <dt className="text-[var(--tb-muted)]">{t("regulatory.authorityLabel")}</dt>
                  <dd className="text-[var(--tb-ink)]">{req.authority}</dd>
                  <dt className="text-[var(--tb-muted)]">{t("regulatory.legalBasisLabel")}</dt>
                  <dd className="text-[var(--tb-ink)]">{req.legal_basis.join(", ")}</dd>
                </dl>
                <ul className="mt-4 space-y-2">
                  {req.documents.map((doc) => {
                    const status = docStatus(req.permit, doc);
                    return (
                      <li
                        key={doc}
                        className="flex items-center justify-between gap-3 rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2 text-sm"
                      >
                        <span className="text-[var(--tb-ink)]">{doc}</span>
                        <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${STATUS_BADGE[status]}`}>
                          {t(`regulatory.docStatus.${status}`)}
                        </span>
                      </li>
                    );
                  })}
                </ul>
                {report.drafts[req.permit] && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-sm font-semibold text-[var(--tb-green)]">
                      {t("regulatory.draftLabel")}
                    </summary>
                    <p className="mt-2 whitespace-pre-wrap rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2 text-sm leading-relaxed text-[var(--tb-ink)]">
                      {report.drafts[req.permit]}
                    </p>
                  </details>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
