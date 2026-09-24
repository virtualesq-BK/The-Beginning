import i18n from "../i18n";

function currentLanguage(): "ko" | "en" {
  return i18n.language?.startsWith("en") ? "en" : "ko";
}

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export type RegulatorySector = { country: string; sector: string };

export type RegulatoryRequirement = {
  permit: string;
  authority: string;
  documents: string[];
  legal_basis: string[];
};

export type RegulatoryGap = {
  permit: string;
  document: string;
  status: "missing" | "insufficient";
  detail: string;
};

export type RegulatoryReport = {
  requirements: RegulatoryRequirement[];
  gaps: RegulatoryGap[];
  drafts: Record<string, string>;
  disclaimer: string;
};

async function failure(res: Response, fallback: string): Promise<Error> {
  const body = await res.json().catch(() => ({}));
  const detail = (body as { detail?: unknown }).detail;
  return new Error(typeof detail === "string" ? detail : fallback);
}

export async function listRegulatorySectors(): Promise<RegulatorySector[]> {
  const res = await fetch(`${API_BASE}/api/v1/regulatory/sectors`);
  if (!res.ok) throw await failure(res, "지원 업종 목록을 불러오지 못했습니다.");
  const body = await res.json();
  return body.items ?? [];
}

export async function getRegulatoryRequirements(sector: RegulatorySector): Promise<RegulatoryRequirement[]> {
  const params = new URLSearchParams({ ...sector, language: currentLanguage() });
  const res = await fetch(`${API_BASE}/api/v1/regulatory/requirements?${params}`);
  if (!res.ok) throw await failure(res, "인허가 요건을 불러오지 못했습니다.");
  const body = await res.json();
  return body.items ?? [];
}

export async function analyzeRegulatory(
  projectName: string,
  sector: RegulatorySector,
  submitted: Record<string, string>,
): Promise<RegulatoryReport> {
  const res = await fetch(`${API_BASE}/api/v1/regulatory/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_name: projectName,
      country: sector.country,
      sector: sector.sector,
      submitted,
      language: currentLanguage(),
    }),
  });
  if (!res.ok) throw await failure(res, "인허가 분석에 실패했습니다.");
  return res.json();
}
