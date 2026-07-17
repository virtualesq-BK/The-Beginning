import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Session, User } from "@supabase/supabase-js";
import { getAuthRedirectUrl, isSupabaseConfigured, supabase, translateAuthError } from "../lib/supabase";

type AuthMode = "signup" | "login";

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  configured: boolean;
  authOpen: boolean;
  authMode: AuthMode;
  authMessage: string | null;
  authNotice: string | null;
  openAuth: (mode?: AuthMode, message?: string) => void;
  closeAuth: () => void;
  requireAuth: (message?: string) => boolean;
  signUp: (email: string, password: string) => Promise<string | null>;
  signIn: (email: string, password: string) => Promise<string | null>;
  signOut: () => Promise<void>;
  clearAuthNotice: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function cleanAuthParamsFromUrl() {
  if (typeof window === "undefined") return;

  const url = new URL(window.location.href);
  const authParams = [
    "code",
    "access_token",
    "refresh_token",
    "type",
    "error",
    "error_description",
  ];

  let changed = false;
  for (const key of authParams) {
    if (url.searchParams.has(key)) {
      url.searchParams.delete(key);
      changed = true;
    }
  }

  if (url.hash.includes("access_token") || url.hash.includes("type=")) {
    url.hash = "";
    changed = true;
  }

  if (changed) {
    window.history.replaceState({}, document.title, `${url.pathname}${url.search}`);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("signup");
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [authNotice, setAuthNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }

    let mounted = true;

    async function initAuth() {
      const client = supabase;
      if (!client) return;

      const params = new URLSearchParams(window.location.search);
      const authError = params.get("error_description") ?? params.get("error");

      if (authError) {
        setAuthNotice(translateAuthError(decodeURIComponent(authError)));
        setAuthMode("login");
        setAuthOpen(true);
        cleanAuthParamsFromUrl();
      }

      const { data, error } = await client.auth.getSession();
      if (!mounted) return;

      if (error) {
        setAuthNotice(translateAuthError(error.message));
      }

      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
      cleanAuthParamsFromUrl();
    }

    void initAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      setSession(nextSession);
      setUser(nextSession?.user ?? null);
      setLoading(false);

      if (event === "SIGNED_IN" && nextSession?.user) {
        setAuthOpen(false);
        setAuthMessage(null);
        if (nextSession.user.email_confirmed_at) {
          setAuthNotice("로그인되었습니다.");
        }
        cleanAuthParamsFromUrl();
      }

      if (event === "PASSWORD_RECOVERY") {
        setAuthMode("login");
        setAuthOpen(true);
        setAuthNotice("비밀번호 재설정 링크가 확인되었습니다. 새 비밀번호로 로그인해 주세요.");
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const openAuth = useCallback((mode: AuthMode = "signup", message?: string) => {
    setAuthMode(mode);
    setAuthMessage(message ?? null);
    setAuthOpen(true);
  }, []);

  const closeAuth = useCallback(() => {
    setAuthOpen(false);
    setAuthMessage(null);
  }, []);

  const clearAuthNotice = useCallback(() => {
    setAuthNotice(null);
  }, []);

  const requireAuth = useCallback(
    (message?: string) => {
      if (user) return true;
      openAuth(
        "login",
        message ?? "이 기능을 사용하려면 로그인이 필요합니다.",
      );
      return false;
    },
    [openAuth, user],
  );

  const signUp = useCallback(async (email: string, password: string) => {
    if (!supabase) {
      return "Supabase 환경 변수(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)가 설정되지 않았습니다.";
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: getAuthRedirectUrl(),
      },
    });

    if (error) return translateAuthError(error.message);

    if (!data.session) {
      setAuthMode("login");
      return "가입 메일을 보냈습니다. 이메일의 확인 링크를 클릭한 뒤, 같은 비밀번호로 로그인해 주세요.";
    }

    setAuthOpen(false);
    setAuthMessage(null);
    setAuthNotice("회원 가입이 완료되었습니다.");
    return null;
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) {
      return "Supabase 환경 변수(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)가 설정되지 않았습니다.";
    }

    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return translateAuthError(error.message);

    setAuthOpen(false);
    setAuthMessage(null);
    setAuthNotice("로그인되었습니다.");
    return null;
  }, []);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    await supabase.auth.signOut();
    setAuthNotice("로그아웃되었습니다.");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      session,
      loading,
      configured: isSupabaseConfigured,
      authOpen,
      authMode,
      authMessage,
      authNotice,
      openAuth,
      closeAuth,
      requireAuth,
      signUp,
      signIn,
      signOut,
      clearAuthNotice,
    }),
    [
      user,
      session,
      loading,
      authOpen,
      authMode,
      authMessage,
      authNotice,
      openAuth,
      closeAuth,
      requireAuth,
      signUp,
      signIn,
      signOut,
      clearAuthNotice,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
