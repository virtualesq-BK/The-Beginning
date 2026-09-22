import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  deleteStandardContractComparisonById,
  deleteStandardContractComparisonsBatch,
  exportStandardContractComparisonCSV,
  exportStandardContractComparisonExcel,
  exportStandardContractComparisonJSON,
  exportStandardContractComparisonPDF,
  getStandardContractComparisonById,
  listSavedStandardContractComparisons,
  type StandardContractComparisonResponse,
  type StandardContractHistoryItem,
  type StandardContractType,
} from "../lib/standardContractApi";

type SortBy = "recent" | "score-high" | "score-low";
type TypeFilter = "all" | StandardContractType;

export function StandardContractHistoryPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState<StandardContractHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<StandardContractComparisonResponse | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [sortBy, setSortBy] = useState<SortBy>("recent");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [operationInProgress, setOperationInProgress] = useState(false);
  const [selectedForDelete, setSelectedForDelete] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!user) {
      navigate("/");
      return;
    }
    void loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, navigate]);

  async function loadHistory() {
    try {
      setLoading(true);
      setError(null);
      const historyItems = await listSavedStandardContractComparisons();
      setItems(historyItems);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("standardContractHistory.errors.loadHistory"));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  const filteredItems = items.filter((item) => (typeFilter === "all" ? true : item.contract_type === typeFilter));

  const sortedItems = [...filteredItems].sort((a, b) => {
    if (sortBy === "score-high") return b.overall_score - a.overall_score;
    if (sortBy === "score-low") return a.overall_score - b.overall_score;
    return 0;
  });

  async function handleSelectItem(itemId: string) {
    try {
      setOperationInProgress(true);
      const result = await getStandardContractComparisonById(itemId);
      setSelectedItem(result);
      setSelectedItemId(itemId);
      setShowModal(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("standardContractHistory.errors.loadItem"));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleDelete() {
    if (!selectedItemId || !window.confirm(t("standardContractHistory.confirm.deleteOne"))) return;

    try {
      setOperationInProgress(true);
      await deleteStandardContractComparisonById(selectedItemId);
      setShowModal(false);
      setSelectedItem(null);
      setSelectedItemId(null);
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("standardContractHistory.errors.delete"));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function withExport(fn: (text: string, type: StandardContractType) => Promise<void>, errorKey: string) {
    if (!selectedItem?.contract_text) {
      setError(t("standardContractHistory.errors.contractNotFound"));
      return;
    }
    try {
      setOperationInProgress(true);
      await fn(selectedItem.contract_text, selectedItem.contract_type);
    } catch (e) {
      setError(e instanceof Error ? e.message : t(errorKey));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleBatchDelete() {
    if (
      selectedForDelete.size === 0 ||
      !window.confirm(t("standardContractHistory.confirm.deleteBatch", { count: selectedForDelete.size }))
    )
      return;

    try {
      setOperationInProgress(true);
      await deleteStandardContractComparisonsBatch(Array.from(selectedForDelete));
      setSelectedForDelete(new Set());
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("standardContractHistory.errors.batchDelete"));
    } finally {
      setOperationInProgress(false);
    }
  }

  function formatDate(dateString?: string): string {
    if (!dateString) return "";
    try {
      return new Date(dateString).toLocaleDateString(i18n.language === "en" ? "en-US" : "ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  }

  return (
    <div className="min-h-screen bg-[var(--tb-sand)] text-[var(--tb-ink)]">
      <div className="sticky top-0 z-20 border-b border-[var(--tb-line)] bg-[var(--tb-sand)]/90 backdrop-blur-md">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display text-3xl font-semibold tracking-tight text-[var(--tb-ink)]">
                {t("standardContractHistory.heading")}
              </h1>
              <p className="mt-1 text-sm text-[var(--tb-muted)]">
                {sortedItems.length}
                {t("standardContractHistory.countSuffix")}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/standard-contract-compare")}
              className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)]"
            >
              {t("standardContractHistory.back")}
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-8 flex flex-col gap-4 rounded-2xl border border-[var(--tb-line)] bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                {t("standardContractHistory.sort.label")}
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="mt-2 rounded-lg border border-[var(--tb-line)] bg-white px-3 py-2 text-sm text-[var(--tb-ink)]"
              >
                <option value="recent">{t("standardContractHistory.sort.recent")}</option>
                <option value="score-high">{t("standardContractHistory.sort.scoreHigh")}</option>
                <option value="score-low">{t("standardContractHistory.sort.scoreLow")}</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                {t("standardContractHistory.typeFilter.label")}
              </label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
                className="mt-2 rounded-lg border border-[var(--tb-line)] bg-white px-3 py-2 text-sm text-[var(--tb-ink)]"
              >
                <option value="all">{t("standardContractHistory.typeFilter.all")}</option>
                <option value="distributor">{t("standardContractHistory.typeFilter.distributor")}</option>
                <option value="oem_odm">{t("standardContractHistory.typeFilter.oem_odm")}</option>
                <option value="license">{t("standardContractHistory.typeFilter.license")}</option>
              </select>
            </div>
          </div>

          <div className="text-sm text-[var(--tb-muted)]">
            {sortedItems.length === 0
              ? t("standardContractHistory.noHistory")
              : t("standardContractHistory.itemsCount", { count: sortedItems.length })}
            {selectedForDelete.size > 0 && (
              <span className="ml-4 font-semibold text-[var(--tb-green)]">
                {t("standardContractHistory.selectedCount", { count: selectedForDelete.size })}
              </span>
            )}
          </div>

          {selectedForDelete.size > 0 && (
            <button
              type="button"
              onClick={handleBatchDelete}
              disabled={operationInProgress}
              className="ml-auto mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
            >
              {t("standardContractHistory.deleteSelected", { count: selectedForDelete.size })}
            </button>
          )}
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
            <button type="button" onClick={() => setError(null)} className="ml-3 font-semibold underline">
              {t("standardContractHistory.close")}
            </button>
          </div>
        )}

        {loading ? (
          <div className="text-center text-[var(--tb-muted)]">{t("standardContractHistory.loading")}</div>
        ) : sortedItems.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[var(--tb-line)] bg-white p-12 text-center">
            <p className="text-[var(--tb-muted)]">{t("standardContractHistory.empty.message")}</p>
            <button
              type="button"
              onClick={() => navigate("/standard-contract-compare")}
              className="mt-4 inline-block rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] hover:bg-white"
            >
              {t("standardContractHistory.empty.cta")}
            </button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sortedItems.map((item) => (
              <div
                key={item.id}
                className="relative rounded-xl border border-[var(--tb-line)] bg-white p-4 transition hover:border-[var(--tb-green)] hover:bg-[var(--tb-green-soft)]"
              >
                <div className="absolute left-3 top-3">
                  <input
                    type="checkbox"
                    checked={selectedForDelete.has(item.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      const newSelected = new Set(selectedForDelete);
                      if (newSelected.has(item.id)) {
                        newSelected.delete(item.id);
                      } else {
                        newSelected.add(item.id);
                      }
                      setSelectedForDelete(newSelected);
                    }}
                    className="h-4 w-4 cursor-pointer rounded border-[var(--tb-line)]"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => void handleSelectItem(item.id)}
                  disabled={operationInProgress}
                  className="block w-full text-left disabled:opacity-50"
                >
                  <div className="text-xs font-semibold text-[var(--tb-green)] uppercase tracking-[0.1em]">
                    {t(`standardContractHistory.typeFilter.${item.contract_type}`)}
                  </div>
                  <div className="mt-3 text-3xl font-semibold text-[var(--tb-ink)]">{item.overall_score}</div>
                  <div className="mt-2 text-sm text-[var(--tb-muted)]">{item.balance}</div>
                  <div className="mt-3 text-xs text-[var(--tb-muted)]">{formatDate(item.created_at)}</div>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                {t("standardContractHistory.modal.eyebrow")}
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-[var(--tb-ink)]">
                {t("standardContractHistory.modal.score", { score: selectedItem.overall_score })}
              </h2>
              <p className="mt-1 text-sm text-[var(--tb-muted)]">{selectedItem.balance}</p>
            </div>

            <div className="mb-6 max-h-96 overflow-y-auto rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] p-4">
              <h3 className="text-sm font-semibold text-[var(--tb-ink)]">{t("standardContractHistory.modal.summary")}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--tb-muted)]">{selectedItem.summary}</p>

              {selectedItem.focus_areas.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                    {t("standardContractHistory.modal.focusAreas")}
                  </h4>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedItem.focus_areas.map((area) => (
                      <span
                        key={area}
                        className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
                      >
                        {area}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => {
                  setShowModal(false);
                  setSelectedItem(null);
                  setSelectedItemId(null);
                }}
                disabled={operationInProgress}
                className="order-2 rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50 sm:order-1"
              >
                {t("standardContractHistory.modal.close")}
              </button>

              <button
                type="button"
                onClick={() => void withExport(exportStandardContractComparisonJSON, "standardContractHistory.errors.jsonDownload")}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                {t("standardContractHistory.modal.json")}
              </button>

              <button
                type="button"
                onClick={() => void withExport(exportStandardContractComparisonCSV, "standardContractHistory.errors.csvDownload")}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                {t("standardContractHistory.modal.csv")}
              </button>

              <button
                type="button"
                onClick={() => void withExport(exportStandardContractComparisonExcel, "standardContractHistory.errors.excelDownload")}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                {t("standardContractHistory.modal.excel")}
              </button>

              <button
                type="button"
                onClick={() => void withExport(exportStandardContractComparisonPDF, "standardContractHistory.errors.pdfDownload")}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                {t("standardContractHistory.modal.pdf")}
              </button>

              <button
                type="button"
                onClick={handleDelete}
                disabled={operationInProgress}
                className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
              >
                {t("standardContractHistory.modal.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
