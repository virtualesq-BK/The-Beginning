import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  deleteFIDICComparisonById,
  exportFIDICComparisonJSONReport,
  exportFIDICComparisonReport,
  getFIDICComparisonById,
  listSavedFIDICComparisons,
  type FIDICComparisonResponse,
} from "../lib/fidicApi";

type HistoryItem = { id: string; overall_score: number; balance: string };
type SortBy = "recent" | "score-high" | "score-low";
type DateFilter = "7days" | "all";

export function FIDICHistoryPage() {
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
      setError(e instanceof Error ? e.message : "히스토리 로드에 실패했습니다.");
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
      setError(e instanceof Error ? e.message : "항목 로드에 실패했습니다.");
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleDelete() {
    if (!selectedItem || !window.confirm("이 저장 내역을 삭제하시겠습니까?")) return;

    try {
      setOperationInProgress(true);
      // Get comparison_id from selected item - we need to find it from the items list
      const itemToDelete = items.find(
        (item) =>
          item.overall_score === selectedItem.overall_score &&
          item.balance === selectedItem.balance
      );
      if (!itemToDelete) throw new Error("항목을 찾을 수 없습니다.");

      await deleteFIDICComparisonById(itemToDelete.id);
      setShowModal(false);
      setSelectedItem(null);
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "삭제에 실패했습니다.");
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleExportPDF() {
    if (!selectedItem?.contract_text) {
      setError("계약 내용을 찾을 수 없습니다.");
      return;
    }

    try {
      setOperationInProgress(true);
      await exportFIDICComparisonReport(selectedItem.contract_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF 다운로드에 실패했습니다.");
    } finally {
      setOperationInProgress(false);
    }
  }

  async function handleExportJSON() {
    if (!selectedItem?.contract_text) {
      setError("계약 내용을 찾을 수 없습니다.");
      return;
    }

    try {
      setOperationInProgress(true);
      await exportFIDICComparisonJSONReport(selectedItem.contract_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "JSON 다운로드에 실패했습니다.");
    } finally {
      setOperationInProgress(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--tb-sand)] text-[var(--tb-ink)]">
      <div className="sticky top-0 z-20 border-b border-[var(--tb-line)] bg-[var(--tb-sand)]/90 backdrop-blur-md">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display text-3xl font-semibold tracking-tight text-[var(--tb-ink)]">
                내 저장 내역
              </h1>
              <p className="mt-1 text-sm text-[var(--tb-muted)]">
                {sortedItems.length}개의 비교 결과
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)]"
            >
              ← 돌아가기
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
                정렬
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="mt-2 rounded-lg border border-[var(--tb-line)] bg-white px-3 py-2 text-sm text-[var(--tb-ink)]"
              >
                <option value="recent">최근순</option>
                <option value="score-high">점수 높음순</option>
                <option value="score-low">점수 낮음순</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                기간
              </label>
              <select
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value as DateFilter)}
                className="mt-2 rounded-lg border border-[var(--tb-line)] bg-white px-3 py-2 text-sm text-[var(--tb-ink)]"
              >
                <option value="7days">최근 7일</option>
                <option value="all">전체</option>
              </select>
            </div>
          </div>

          <div className="text-sm text-[var(--tb-muted)]">
            {sortedItems.length === 0 ? "저장 내역이 없습니다" : `${sortedItems.length}개 항목`}
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
            <button
              type="button"
              onClick={() => setError(null)}
              className="ml-3 font-semibold underline"
            >
              닫기
            </button>
          </div>
        )}

        {loading ? (
          <div className="text-center text-[var(--tb-muted)]">로드 중...</div>
        ) : sortedItems.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[var(--tb-line)] bg-white p-12 text-center">
            <p className="text-[var(--tb-muted)]">저장된 비교 결과가 없습니다.</p>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="mt-4 inline-block rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] hover:bg-white"
            >
              계약서 비교하러 가기
            </button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sortedItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => void handleSelectItem(item.id)}
                disabled={operationInProgress}
                className="rounded-xl border border-[var(--tb-line)] bg-white p-4 text-left transition hover:border-[var(--tb-green)] hover:bg-[var(--tb-green-soft)] disabled:opacity-50"
              >
                <div className="text-xs font-semibold text-[var(--tb-green)] uppercase tracking-[0.1em]">
                  {item.id.slice(0, 8)}
                </div>
                <div className="mt-3 text-3xl font-semibold text-[var(--tb-ink)]">
                  {item.overall_score}
                </div>
                <div className="mt-2 text-sm text-[var(--tb-muted)]">{item.balance}</div>
              </button>
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
                저장된 비교 결과
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-[var(--tb-ink)]">
                점수 {selectedItem.overall_score} / 100
              </h2>
              <p className="mt-1 text-sm text-[var(--tb-muted)]">
                {selectedItem.balance}
              </p>
            </div>

            <div className="mb-6 max-h-96 overflow-y-auto rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] p-4">
              <h3 className="text-sm font-semibold text-[var(--tb-ink)]">요약</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--tb-muted)]">
                {selectedItem.summary}
              </p>

              {selectedItem.focus_areas.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--tb-green)]">
                    핵심 항목
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
                닫기
              </button>

              <button
                type="button"
                onClick={handleExportJSON}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                JSON
              </button>

              <button
                type="button"
                onClick={handleExportPDF}
                disabled={operationInProgress}
                className="rounded-lg border border-[var(--tb-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-sand)] disabled:opacity-50"
              >
                PDF
              </button>

              <button
                type="button"
                onClick={handleDelete}
                disabled={operationInProgress}
                className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
