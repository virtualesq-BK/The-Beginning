import { supabase } from "./supabase";
import type { ContractReport } from "../types";

const BUCKET = "contract-uploads";

function fileExt(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

function sanitizeFileName(name: string): string {
  return name.replace(/[^\w.\-가-힣]+/g, "_").slice(0, 120);
}

export type SavedContractAnalysis = {
  id: string;
  storagePath: string;
};

/**
 * 분석 완료된 계약서를 Supabase Storage + contract_analyses에 저장합니다.
 * 로그인된 사용자만 호출해야 합니다.
 */
export async function saveContractUpload(
  userId: string,
  file: File,
  report: ContractReport,
): Promise<SavedContractAnalysis> {
  if (!supabase) {
    throw new Error("Supabase가 설정되지 않았습니다.");
  }

  const ext = fileExt(file.name);
  const safeName = sanitizeFileName(file.name || `contract${ext || ".bin"}`);
  const storagePath = `${userId}/${crypto.randomUUID()}_${safeName}`;

  const { error: uploadError } = await supabase.storage.from(BUCKET).upload(storagePath, file, {
    cacheControl: "3600",
    upsert: false,
    contentType: file.type || "application/octet-stream",
  });

  if (uploadError) {
    throw new Error(`문서 파일 저장에 실패했습니다: ${uploadError.message}`);
  }

  const { data, error: insertError } = await supabase
    .from("contract_analyses")
    .insert({
      user_id: userId,
      file_name: file.name,
      file_ext: ext || null,
      file_size: file.size,
      mime_type: file.type || null,
      storage_path: storagePath,
      document_summary: report.document_summary,
      clause_count: report.clause_count,
      high_risk_count: report.high_risk_count,
      report,
    })
    .select("id, storage_path")
    .single();

  if (insertError) {
    // DB 실패 시 업로드된 파일 정리 시도
    await supabase.storage.from(BUCKET).remove([storagePath]);
    throw new Error(`분석 결과 저장에 실패했습니다: ${insertError.message}`);
  }

  return {
    id: data.id as string,
    storagePath: data.storage_path as string,
  };
}
