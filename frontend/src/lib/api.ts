import type { ContractReport } from "../types";

// 로컬: Vite DEV면 백엔드(8000), 프로덕션: 같은 오리진(상대 경로)
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export type ExpertRequestType = "translation_review" | "legal_expert";

const EXPERT_REQUEST_SUBJECTS: Record<ExpertRequestType, string> = {
  translation_review: "전문가 번역 검수 요청",
  legal_expert: "해외 법률 전문가 연결 요청",
};

function errorDetail(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "object" && item && "msg" in item
          ? String((item as { msg: unknown }).msg)
          : String(item),
      )
      .join(", ");
  }
  return fallback;
}

export async function analyzeContract(file: File): Promise<ContractReport> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/v1/contracts/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body, `분석 요청에 실패했습니다 (HTTP ${res.status})`));
  }

  return res.json();
}

export function openExpertMailto(requestType: ExpertRequestType, to = "virtual.esq@gmail.com") {
  const subject = EXPERT_REQUEST_SUBJECTS[requestType];
  const body = `The Beginning에서 '${subject}'을(를) 요청합니다.`;
  window.location.href = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export async function requestExpert(requestType: ExpertRequestType): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/expert-requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_type: requestType }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body, `전문가 연결 요청에 실패했습니다 (HTTP ${res.status})`));
  }
}
