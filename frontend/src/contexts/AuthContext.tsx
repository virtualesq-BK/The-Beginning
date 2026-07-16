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
import { isSupabaseConfigured, supabase } from "../lib/supabase";

type AuthMode = "signup" | "login";

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  configured: boolean;
  authOpen: boolean;
  authMode: AuthMode;
  authMessage: string | null;
  openAuth: (mode?: AuthMode, message?: string) => void;
  closeAuth: () => void;
  requireAuth: (message?: string) => boolean;
  signUp: (email: string, password: string) => Promise<string | null>;
  signIn: (email: string, password: string) => Promise<string | null>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("signup");
  const [authMessage, setAuthMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }

    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setUser(nextSession?.user ?? null);
      setLoading(false);
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

  const requireAuth = useCallback(
    (message?: string) => {
      if (user) return true;
      openAuth(
        "signup",
        message ?? "이 기능을 사용하려면 회원 가입 또는 로그인이 필요합니다.",
      );
      return false;
    },
    [openAuth, user],
  );

  const signUp = useCallback(async (email: string, password: string) => {
    if (!supabase) {
      return "Supabase 환경 변수(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)가 설정되지 않았습니다.";
    }

    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) return error.message;

    if (!data.session) {
      return "가입 메일을 보냈습니다. 이메일의 확인 링크를 클릭한 뒤 로그인해 주세요.";
    }

    setAuthOpen(false);
    setAuthMessage(null);
    return null;
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) {
      return "Supabase 환경 변수(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)가 설정되지 않았습니다.";
    }

    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return error.message;

    setAuthOpen(false);
    setAuthMessage(null);
    return null;
  }, []);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    await supabase.auth.signOut();
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
      openAuth,
      closeAuth,
      requireAuth,
      signUp,
      signIn,
      signOut,
    }),
    [
      user,
      session,
      loading,
      authOpen,
      authMode,
      authMessage,
      openAuth,
      closeAuth,
      requireAuth,
      signUp,
      signIn,
      signOut,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
