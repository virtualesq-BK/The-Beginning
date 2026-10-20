import type { ContractReport } from "../types";
import i18n from "../i18n";

function currentLanguage(): "ko" | "en" {
  return i18n.language?.startsWith("en") ? "en" : "ko";
}

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
  formData.append("language", currentLanguage());

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

export async function analyzeContractText(text: string): Promise<ContractReport> {
  const res = await fetch(`${API_BASE}/api/v1/contracts/analyze-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language: currentLanguage() }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body, `분析 요청에 실패했습니다 (HTTP ${res.status})`));
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
    body: JSON.stringify({ request_type: requestType, language: currentLanguage() }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body, `전문가 연결 요청에 실패했습니다 (HTTP ${res.status})`));
  }
}

export type StandardContractItem = {
  id: string;
  title: string;
  category: string;
  group: string;
  description: string;
  detail: string;
  url: string;
  tags: string[];
};

export async function getStandardContracts(): Promise<StandardContractItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/standard-contracts`);
  if (!res.ok) {
    throw new Error("표준계약서 자료를 불러오지 못했습니다.");
  }
  const body = await res.json();
  return body.items ?? [];
}

export type ContractTemplateFieldOption = { value: string; label: string };

export type ContractTemplateField = {
  key: string;
  label: string;
  type: "text" | "textarea" | "select" | "date" | "number";
  required?: boolean;
  placeholder?: string;
  options?: ContractTemplateFieldOption[];
};

export type ContractTemplate = {
  id: string;
  title: string;
  family: string;
  description: string;
  fields: ContractTemplateField[];
};

export async function getContractTemplates(): Promise<ContractTemplate[]> {
  const res = await fetch(`${API_BASE}/api/v1/contract-templates`);
  if (!res.ok) {
    throw new Error("계약서 템플릿 목록을 불러오지 못했습니다.");
  }
  const body = await res.json();
  return body.items ?? [];
}

export type GeneratedClause = {
  clause_no: number;
  heading: string;
  body_en: string;
  commentary_kr: string;
  commentary?: string;
};

export type GeneratedContract = {
  template_id: string;
  template_title: string;
  title: string;
  recitals: string;
  clauses: GeneratedClause[];
  signature_block: string;
  references: { doc_id: string; score: number }[];
  disclaimer: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export async function sendContractChat(
  contractSummary: string,
  clausesContext: string,
  messages: ChatMessage[],
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/contracts/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contract_summary: contractSummary,
      clauses_context: clausesContext,
      messages,
      language: currentLanguage(),
    }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body, `채팅 응답 요청에 실패했습니다 (HTTP ${res.status})`));
  }

  const data = await res.json();
  return data.reply as string;
}

export async function generateContract(
  templateId: string,
  answers: Record<string, string>,
): Promise<GeneratedContract> {
  const res = await fetch(`${API_BASE}/api/v1/contract-templates/${templateId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, language: currentLanguage() }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body, `계약서 초안 생성에 실패했습니다 (HTTP ${res.status})`));
  }

  return res.json();
}
