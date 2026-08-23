import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  deleteFIDICComparisonById,
  deleteFIDICComparisonsBatch,
  exportFIDICComparisonCSV,
  exportFIDICComparisonExcel,
  exportFIDICComparisonJSONReport,
  exportFIDICComparisonReport,
  getFIDICComparisonById,
  listSavedFIDICComparisons,
  type FIDICComparisonResponse,
} from "../lib/fidicApi";

type HistoryItem = { id: string; overall_score: number; balance: string; created_at?: string };
type SortBy = "recent" | "score-high" | "score-low";
type DateFilter = "7days" | "all";

export function FIDICHistoryPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<FIDICComparisonResponse | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [sortBy, setSortBy] = useState<SortBy>("recent");
  const [dateFilter, setDateFilter] = useState<DateFilter>("all");
  const [operationInProgress, setOperationInProgress] = useState(false);
  const [selectedForDelete, setSelectedForDelete] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!user) {
      navigate("/");
      return;
    }
    void loadHistory();
  }, [user, navigate]);

  async function loadHistory() {
    try {
      setLoading(true);
      setError(null);
      const historyItems = await listSavedFIDICComparisons();
      setItems(historyItems);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("fidicHistory.errors.loadHistory"));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  const filteredItems = items.filter(() => {
    if (dateFilter === "7days") {
      // Note: This is a simplified filter - actual dates would come from API response
      // For now, all items are included since we don't have created_at in the summary
      return true;
    }
    return true;
  });

  const sortedItems = [...filteredItems].sort((a, b) => {
    if (sortBy === "score-high") return b.overall_score - a.overall_score;
    if (sortBy === "score-low") return a.overall_score - b.overall_score;
    return 0; // recent is default
  });

  async function handleSelectItem(itemId: string) {
    try {
      setOperationInProgress(true);
      const result = await getFIDICComparisonById(itemId);
      setSelectedItem(result);
      setShowModal(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("fidicHistory.errors.loadItem"));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleDelete() {
    if (!selectedItem || !window.confirm(t("fidicHistory.confirm.deleteOne"))) return;

    try {
      setOperationInProgress(true);
      // Get comparison_id from selected item - we need to find it from the items list
      const itemToDelete = items.find(
        (item) =>
          item.overall_score === selectedItem.overall_score &&
          item.balance === selectedItem.balance
      );
      if (!itemToDelete) throw new Error(t("fidicHistory.errors.itemNotFound"));

      await deleteFIDICComparisonById(itemToDelete.id);
      setShowModal(false);
      setSelectedItem(null);
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("fidicHistory.errors.delete"));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleExportPDF() {
    if (!selectedItem?.contract_text) {
      setError(t("fidicHistory.errors.contractNotFound"));
      return;
    }

    try {
      setOperationInProgress(true);
      await exportFIDICComparisonReport(selectedItem.contract_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("fidicHistory.errors.pdfDownload"));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleExportJSON() {
    if (!selectedItem?.contract_text) {
      setError(t("fidicHistory.errors.contractNotFound"));
      return;
    }

    try {
      setOperationInProgress(true);
      await exportFIDICComparisonJSONReport(selectedItem.contract_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("fidicHistory.errors.jsonDownload"));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleExportCSV() {
    if (!selectedItem?.contract_text) {
      setError(t("fidicHistory.errors.contractNotFound"));
      return;
    }

    try {
      setOperationInProgress(true);
      await exportFIDICComparisonCSV(selectedItem.contract_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("fidicHistory.errors.csvDownload"));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleExportExcel() {
    if (!selectedItem?.contract_text) {
      setError(t("fidicHistory.errors.contractNotFound"));
      return;
    }

    try {
      setOperationInProgress(true);
      await exportFIDICComparisonExcel(selectedItem.contract_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("fidicHistory.errors.excelDownload"));
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleBatchDelete() {
    if (selectedForDelete.size === 0 || !window.confirm(t("fidicHistory.confirm.deleteBatch", { count: selectedForDelete.size }))) return;

    try {
      setOperationInProgress(true);
      await deleteFIDICComparisonsBatch(Array.from(selectedForDelete));
      setSelectedForDelete(new Set());
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("fidicHistory.errors.batchDelete"));
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
                {t("fidicHistory.heading")}
              </h1>
              <p className="mt-1 text-sm text-[var(--tb-muted)]">
                {sortedItems.length}{t("fidicHistory.countSuffix")}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)]"
            >
              {t("fidicHistory.back")}
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-8">
        {/* Filters */}
        <div className="mb-8 flex flex-col gap-4 rounded-2xl border border-[var(--tb-line)] bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                {t("fidicHistory.sort.label")}
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="mt-2 rounded-lg border border-[var(--tb-line)] bg-white px-3 py-2 text-sm text-[var(--tb-ink)]"
              >
                <option value="recent">{t("fidicHistory.sort.recent")}</option>
                <option value="score-high">{t("fidicHistory.sort.scoreHigh")}</option>
                <option value="score-low">{t("fidicHistory.sort.scoreLow")}</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                {t("fidicHistory.period.label")}
              </label>
              <select
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value as DateFilter)}
                className="mt-2 rounded-lg border border-[var(--tb-line)] bg-white px-3 py-2 text-sm text-[var(--tb-ink)]"
              >
                <option value="7days">{t("fidicHistory.period.last7days")}</option>
                <option value="all">{t("fidicHistory.period.all")}</option>
              </select>
            </div>
          </div>

          <div className="text-sm text-[var(--tb-muted)]">
            {sortedItems.length === 0 ? t("fidicHistory.noHistory") : t("fidicHistory.itemsCount", { count: sortedItems.length })}
            {selectedForDelete.size > 0 && (
              <span className="ml-4 font-semibold text-[var(--tb-green)]">
                {t("fidicHistory.selectedCount", { count: selectedForDelete.size })}
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
              {t("fidicHistory.deleteSelected", { count: selectedForDelete.size })}
            </button>
          )}
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
            <button
              type="button"
              onClick={() => setError(null)}
              className="ml-3 font-semibold underline"
            >
              {t("fidicHistory.close")}
            </button>
          </div>
        )}

        {loading ? (
          <div className="text-center text-[var(--tb-muted)]">{t("fidicHistory.loading")}</div>
        ) : sortedItems.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[var(--tb-line)] bg-white p-12 text-center">
            <p className="text-[var(--tb-muted)]">{t("fidicHistory.empty.message")}</p>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="mt-4 inline-block rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] hover:bg-white"
            >
              {t("fidicHistory.empty.cta")}
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
                    {item.id.slice(0, 8)}
                  </div>
                  <div className="mt-3 text-3xl font-semibold text-[var(--tb-ink)]">
                    {item.overall_score}
                  </div>
                  <div className="mt-2 text-sm text-[var(--tb-muted)]">{item.balance}</div>
                  <div className="mt-3 text-xs text-[var(--tb-muted)]">
                    {formatDate(item.created_at)}
                  </div>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                {t("fidicHistory.modal.eyebrow")}
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-[var(--tb-ink)]">
                {t("fidicHistory.modal.score", { score: selectedItem.overall_score })}
              </h2>
              <p className="mt-1 text-sm text-[var(--tb-muted)]">
                {selectedItem.balance}
              </p>
            </div>

            <div className="mb-6 max-h-96 overflow-y-auto rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] p-4">
              <h3 className="text-sm font-semibold text-[var(--tb-ink)]">{t("fidicHistory.modal.summary")}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--tb-muted)]">
                {selectedItem.summary}
              </p>

              {selectedItem.focus_areas.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                    {t("fidicHistory.modal.focusAreas")}
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
                }}
                disabled={operationInProgress}
                className="order-2 rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50 sm:order-1"
              >
                {t("fidicHistory.modal.close")}
              </button>

              <button
                type="button"
                onClick={handleExportJSON}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                {t("fidicHistory.modal.json")}
              </button>

              <button
                type="button"
                onClick={handleExportCSV}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                {t("fidicHistory.modal.csv")}
              </button>

              <button
                type="button"
                onClick={handleExportExcel}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                {t("fidicHistory.modal.excel")}
              </button>

              <button
                type="button"
                onClick={handleExportPDF}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                {t("fidicHistory.modal.pdf")}
              </button>

              <button
                type="button"
                onClick={handleDelete}
                disabled={operationInProgress}
                className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
              >
                {t("fidicHistory.modal.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
