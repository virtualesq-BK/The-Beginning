import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export function getAuthRedirectUrl() {
  if (typeof window === "undefined") return undefined;
  return `${window.location.origin}/`;
}

export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(supabaseUrl!, supabaseAnonKey!, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        flowType: "pkce",
      },
    })
  : null;

function translateAuthError(message: string): string {
  const normalized = message.toLowerCase();

  if (normalized.includes("email not confirmed")) {
    return "이메일 확인이 아직 완료되지 않았습니다. 메일함(스팸함 포함)의 확인 링크를 다시 확인해 주세요.";
  }
  if (normalized.includes("invalid login credentials")) {
    return "이메일 또는 비밀번호가 올바르지 않습니다.";
  }
  if (normalized.includes("user already registered")) {
    return "이미 가입된 이메일입니다. 로그인해 주세요.";
  }
  if (normalized.includes("signup is disabled")) {
    return "현재 회원 가입이 비활성화되어 있습니다. Supabase Auth 설정을 확인해 주세요.";
  }

  return message;
}

export { translateAuthError };
