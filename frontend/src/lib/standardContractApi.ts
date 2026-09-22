import { supabase } from "./supabase";
import i18n from "../i18n";

function currentLanguage(): "ko" | "en" {
  return i18n.language?.startsWith("en") ? "en" : "ko";
}

export type StandardContractType = "distributor" | "oem_odm" | "license";

export const STANDARD_CONTRACT_TYPES: StandardContractType[] = ["distributor", "oem_odm", "license"];

export type StandardContractComparisonIssue = {
  id: string;
  label: string;
  score: number;
  status: "good" | "watch" | "risk";
  benchmark: string;
  evidence: string[];
  sentence_evidence: string[];
  recommendation: string;
};

export type StandardContractComparisonResponse = {
  contract_type: StandardContractType;
  overall_score: number;
  summary: string;
  issues: StandardContractComparisonIssue[];
  focus_areas: string[];
  balance: string;
  contract_text?: string;
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export async function compareDraftToStandardAPI(
  contractText: string,
  contractType: StandardContractType,
): Promise<StandardContractComparisonResponse> {
  const res = await fetch(`${API_BASE}/api/v1/standard-contracts/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_text: contractText, contract_type: contractType, language: currentLanguage() }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? "표준계약서 비교 요청에 실패했습니다.");
  }

  return res.json();
}

export async function getStandardContractComparisonById(
  comparisonId: string,
): Promise<StandardContractComparisonResponse> {
  if (supabase) {
    const { data, error } = await supabase
      .from("standard_contract_comparisons")
      .select("*")
      .eq("comparison_id", comparisonId)
      .maybeSingle();

    if (!error && data) {
      return {
        contract_type: data.contract_type,
        overall_score: data.overall_score,
        summary: data.summary,
        issues: data.issues,
        focus_areas: data.focus_areas,
        balance: data.balance,
        contract_text: data.contract_text ?? "",
      } as StandardContractComparisonResponse;
    }
  }

  const res = await fetch(`${API_BASE}/api/v1/standard-contracts/compare/history/${comparisonId}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? "저장된 비교 결과를 불러오지 못했습니다.");
  }

  const body = await res.json();
  return {
    contract_type: body.contract_type,
    overall_score: body.overall_score,
    summary: body.summary,
    issues: body.issues,
    focus_areas: body.focus_areas,
    balance: body.balance,
    contract_text: body.contract_text ?? "",
  } as StandardContractComparisonResponse;
}

export async function saveStandardContractComparisonResult(
  contractText: string,
  contractType: StandardContractType,
  comparisonId?: string,
): Promise<{ comparison_id: string; result: StandardContractComparisonResponse }> {
  const result = await compareDraftToStandardAPI(contractText, contractType);

  if (supabase) {
    const userResult = await supabase.auth.getUser();
    const user = userResult.data?.user ?? null;

    if (user) {
      const payload = {
        comparison_id: comparisonId ?? crypto.randomUUID(),
        user_id: user.id,
        contract_type: contractType,
        contract_text: contractText,
        overall_score: result.overall_score,
        balance: result.balance,
        summary: result.summary,
        focus_areas: result.focus_areas,
        issues: result.issues,
      };

      const { data, error } = await supabase
        .from("standard_contract_comparisons")
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
  }

  const res = await fetch(`${API_BASE}/api/v1/standard-contracts/compare/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contract_text: contractText,
      contract_type: contractType,
      comparison_id: comparisonId ?? null,
      language: currentLanguage(),
    }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? "비교 결과 저장에 실패했습니다.");
  }

  return res.json();
}

export type StandardContractHistoryItem = {
  id: string;
  contract_type: StandardContractType;
  overall_score: number;
  balance: string;
  created_at?: string;
};

export async function listSavedStandardContractComparisons(): Promise<StandardContractHistoryItem[]> {
  if (supabase) {
    const userResult = await supabase.auth.getUser();
    const user = userResult.data?.user ?? null;

    if (user) {
      const { data, error } = await supabase
        .from("standard_contract_comparisons")
        .select("comparison_id, contract_type, overall_score, balance, created_at")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(30);

      if (!error && data) {
        return (data ?? []).map((item) => ({
          id: item.comparison_id,
          contract_type: item.contract_type,
          overall_score: item.overall_score,
          balance: item.balance,
          created_at: item.created_at,
        }));
      }
    }
  }

  const res = await fetch(`${API_BASE}/api/v1/standard-contracts/compare/history`);
  if (!res.ok) throw new Error("저장된 비교 결과 조회에 실패했습니다.");
  const body = await res.json();
  return (body.items ?? []).map((item: StandardContractHistoryItem) => ({
    id: item.id,
    contract_type: item.contract_type,
    overall_score: item.overall_score,
    balance: item.balance,
    created_at: item.created_at,
  }));
}

export async function deleteStandardContractComparisonById(comparisonId: string): Promise<void> {
  if (supabase) {
    const userResult = await supabase.auth.getUser();
    const user = userResult.data?.user ?? null;

    if (user) {
      const { error } = await supabase
        .from("standard_contract_comparisons")
        .delete()
        .eq("comparison_id", comparisonId)
        .eq("user_id", user.id);

      if (!error) {
        return;
      }
    }
  }

  const res = await fetch(`${API_BASE}/api/v1/standard-contracts/compare/history/${comparisonId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? "저장 내역 삭제에 실패했습니다.");
  }
}

export async function deleteStandardContractComparisonsBatch(comparisonIds: string[]): Promise<void> {
  if (comparisonIds.length === 0) return;

  if (supabase) {
    const userResult = await supabase.auth.getUser();
    const user = userResult.data?.user ?? null;

    if (user) {
      const { error } = await supabase
        .from("standard_contract_comparisons")
        .delete()
        .in("comparison_id", comparisonIds)
        .eq("user_id", user.id);

      if (!error) {
        return;
      }
    }
  }

  const res = await fetch(`${API_BASE}/api/v1/standard-contracts/compare/history/batch-delete`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comparison_ids: comparisonIds }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? "배치 삭제에 실패했습니다.");
  }
}

async function downloadExport(
  path: string,
  contractText: string,
  contractType: StandardContractType,
  filename: string,
  errorMessage: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_text: contractText, contract_type: contractType, language: currentLanguage() }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? errorMessage);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function exportStandardContractComparisonPDF(contractText: string, contractType: StandardContractType) {
  return downloadExport(
    "/api/v1/standard-contracts/compare/export",
    contractText,
    contractType,
    "standard-contract-comparison-report.pdf",
    "비교 리포트 다운로드에 실패했습니다.",
  );
}

export function exportStandardContractComparisonJSON(contractText: string, contractType: StandardContractType) {
  return downloadExport(
    "/api/v1/standard-contracts/compare/export-json",
    contractText,
    contractType,
    "standard-contract-comparison-report.json",
    "비교 JSON 다운로드에 실패했습니다.",
  );
}

export function exportStandardContractComparisonCSV(contractText: string, contractType: StandardContractType) {
  return downloadExport(
    "/api/v1/standard-contracts/compare/export-csv",
    contractText,
    contractType,
    "standard-contract-comparison-report.csv",
    "CSV 다운로드에 실패했습니다.",
  );
}

export function exportStandardContractComparisonExcel(contractText: string, contractType: StandardContractType) {
  return downloadExport(
    "/api/v1/standard-contracts/compare/export-excel",
    contractText,
    contractType,
    "standard-contract-comparison-report.xlsx",
    "Excel 다운로드에 실패했습니다.",
  );
}
