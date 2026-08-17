import { supabase } from "./supabase";

export type FIDICComparisonIssue = {
  id: string;
  label: string;
  score: number;
  status: "good" | "watch" | "risk";
  fidic_benchmark: string;
  evidence: string[];
  sentence_evidence: string[];
  recommendation: string;
};

export type FIDICComparisonResponse = {
  overall_score: number;
  summary: string;
  issues: FIDICComparisonIssue[];
  focus_areas: string[];
  balance: "발주자 유리" | "시공사 유리" | "균형형";
  bias_scores: { employer: number; contractor: number };
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export async function compareDraftToFIDICAPI(contractText: string): Promise<FIDICComparisonResponse> {
  const res = await fetch(`${API_BASE}/api/v1/fidic/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_text: contractText }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? "FIDIC 비교 요청에 실패했습니다.");
  }

  return res.json();
}

export async function saveFIDICComparisonResult(contractText: string, comparisonId?: string): Promise<{ comparison_id: string; result: FIDICComparisonResponse }> {
  const result = await compareDraftToFIDICAPI(contractText);

  if (supabase) {
    const payload = {
      comparison_id: comparisonId ?? crypto.randomUUID(),
      contract_text: contractText,
      overall_score: result.overall_score,
      balance: result.balance,
      summary: result.summary,
      focus_areas: result.focus_areas,
      bias_scores: result.bias_scores,
      issues: result.issues,
    };

    const { data, error } = await supabase
      .from("fidic_comparisons")
      .upsert({ ...payload, updated_at: new Date().toISOString() }, { onConflict: "comparison_id" })
      .select("comparison_id, overall_score, balance")
      .single();

    if (!error && data) {
      return {
        comparison_id: data.comparison_id,
        result,
      };
    }
  }

  const fallbackRes = await fetch(`${API_BASE}/api/v1/fidic/compare/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_text: contractText, comparison_id: comparisonId ?? null }),
  });

  if (!fallbackRes.ok) {
    const body = await fallbackRes.json().catch(() => ({}));
    throw new Error(body?.detail ?? "비교 결과 저장에 실패했습니다.");
  }

  return fallbackRes.json();
}

export async function listSavedFIDICComparisons(): Promise<{ id: string; overall_score: number; balance: string }[]> {
  if (supabase) {
    const { data, error } = await supabase
      .from("fidic_comparisons")
      .select("comparison_id, overall_score, balance")
      .order("created_at", { ascending: false })
      .limit(5);

    if (!error && data) {
      return (data ?? []).map((item) => ({
        id: item.comparison_id,
        overall_score: item.overall_score,
        balance: item.balance,
      }));
    }
  }

  const res = await fetch(`${API_BASE}/api/v1/fidic/compare/history`);
  if (!res.ok) throw new Error("저장된 비교 결과 조회에 실패했습니다.");
  const body = await res.json();
  return (body.items ?? []).map((item: { id: string; overall_score: number; balance: string }) => ({
    id: item.id,
    overall_score: item.overall_score,
    balance: item.balance,
  }));
}

export async function exportFIDICComparisonReport(contractText: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/fidic/compare/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_text: contractText }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? "비교 리포트 다운로드에 실패했습니다.");
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "fidic-comparison-report.pdf";
  anchor.click();
  URL.revokeObjectURL(url);
}
