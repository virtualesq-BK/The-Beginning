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
import {
  isProfileComplete,
  type SignupProfile,
  type UserProfile,
} from "../types/auth";

type AuthMode = "signup" | "login" | "complete";

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  profile: UserProfile | null;
  profileComplete: boolean;
  loading: boolean;
  configured: boolean;
  authOpen: boolean;
  authMode: AuthMode;
  authMessage: string | null;
  authNotice: string | null;
  openAuth: (mode?: AuthMode, message?: string) => void;
  closeAuth: () => void;
  requireAuth: (message?: string) => boolean;
  signUp: (email: string, password: string, profile: SignupProfile) => Promise<string | null>;
  signIn: (email: string, password: string) => Promise<string | null>;
  completeProfile: (profile: SignupProfile) => Promise<string | null>;
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

function toProfileRow(profile: SignupProfile, userId: string, email?: string | null) {
  return {
    id: userId,
    email: email ?? null,
    full_name: profile.fullName.trim() || null,
    phone: profile.phone.trim() || null,
    company_name: profile.companyName.trim() || null,
    job_title: profile.jobTitle.trim() || null,
    address: profile.address.trim() || null,
    usage_purposes: profile.usagePurposes,
    other_requests: profile.otherRequests.trim() || null,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("signup");
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [authNotice, setAuthNotice] = useState<string | null>(null);

  const refreshProfile = useCallback(async (userId: string) => {
    if (!supabase) {
      setProfile(null);
      return null;
    }

    const { data, error } = await supabase
      .from("profiles")
      .select(
        "id, email, full_name, phone, company_name, job_title, address, usage_purposes, other_requests",
      )
      .eq("id", userId)
      .maybeSingle();

    if (error) {
      console.warn("profiles fetch failed:", error.message);
      setProfile(null);
      return null;
    }

    const next = (data as UserProfile | null) ?? null;
    setProfile(next);
    return next;
  }, []);

  const ensureProfileOrPrompt = useCallback(
    async (nextUser: User, notice?: string) => {
      const nextProfile = await refreshProfile(nextUser.id);
      if (!isProfileComplete(nextProfile)) {
        setAuthMode("complete");
        setAuthMessage(
          "서비스 이용을 위해 전화번호, 회사명, 직책/직위, 주소, 사용목적을 입력해 주세요.",
        );
        setAuthOpen(true);
        if (notice) setAuthNotice(notice);
        return false;
      }
      return true;
    },
    [refreshProfile],
  );

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

      if (data.session?.user) {
        await ensureProfileOrPrompt(data.session.user);
      } else {
        setProfile(null);
      }

      setLoading(false);
      cleanAuthParamsFromUrl();
    }

    void initAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      void (async () => {
        setSession(nextSession);
        setUser(nextSession?.user ?? null);

        if (event === "SIGNED_OUT") {
          setProfile(null);
          setLoading(false);
          return;
        }

        if (nextSession?.user) {
          const complete = await ensureProfileOrPrompt(
            nextSession.user,
            event === "SIGNED_IN" ? "로그인되었습니다." : undefined,
          );
          if (complete && event === "SIGNED_IN") {
            setAuthOpen(false);
            setAuthMessage(null);
            setAuthNotice("로그인되었습니다.");
          }
        } else {
          setProfile(null);
        }

        setLoading(false);
        cleanAuthParamsFromUrl();
      })();
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [ensureProfileOrPrompt]);

  const openAuth = useCallback((mode: AuthMode = "signup", message?: string) => {
    setAuthMode(mode);
    setAuthMessage(message ?? null);
    setAuthOpen(true);
  }, []);

  const closeAuth = useCallback(() => {
    // 프로필 미완료 상태에서는 닫기 차단
    if (user && !isProfileComplete(profile) && authMode === "complete") {
      setAuthMessage("추가 정보를 입력해야 서비스를 이용할 수 있습니다.");
      return;
    }
    setAuthOpen(false);
    setAuthMessage(null);
  }, [authMode, profile, user]);

  const clearAuthNotice = useCallback(() => {
    setAuthNotice(null);
  }, []);

  const requireAuth = useCallback(
    (message?: string) => {
      if (!user) {
        openAuth("login", message ?? "이 기능을 사용하려면 로그인이 필요합니다.");
        return false;
      }
      if (!isProfileComplete(profile)) {
        openAuth(
          "complete",
          message ??
            "서비스 이용을 위해 전화번호, 회사명, 직책/직위, 주소, 사용목적을 입력해 주세요.",
        );
        return false;
      }
      return true;
    },
    [openAuth, profile, user],
  );

  const signUp = useCallback(async (email: string, password: string, profileData: SignupProfile) => {
    if (!supabase) {
      return "Supabase 환경 변수(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)가 설정되지 않았습니다.";
    }

    const metadata = {
      full_name: profileData.fullName.trim(),
      phone: profileData.phone.trim(),
      company_name: profileData.companyName.trim(),
      job_title: profileData.jobTitle.trim(),
      address: profileData.address.trim(),
      usage_purposes: profileData.usagePurposes,
      other_requests: profileData.otherRequests.trim(),
    };

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: getAuthRedirectUrl(),
        data: metadata,
      },
    });

    if (error) return translateAuthError(error.message);

    if (data.user) {
      const { error: profileError } = await supabase
        .from("profiles")
        .upsert(toProfileRow(profileData, data.user.id, data.user.email), { onConflict: "id" });

      if (profileError) {
        console.warn("profiles upsert failed:", profileError.message);
        return `회원 가입은 되었지만 프로필 저장에 실패했습니다: ${profileError.message}. Supabase profiles 컬럼/마이그레이션을 확인해 주세요.`;
      }

      setProfile(toProfileRow(profileData, data.user.id, data.user.email) as UserProfile);
    }

    if (!data.session) {
      setAuthMode("login");
      return "가입 메일을 보냈습니다. 이메일의 확인 링크를 클릭한 뒤, 같은 비밀번호로 로그인해 주세요.";
    }

    setAuthOpen(false);
    setAuthMessage(null);
    setAuthNotice("회원 가입이 완료되었습니다.");
    return null;
  }, []);

  const completeProfile = useCallback(
    async (profileData: SignupProfile) => {
      if (!supabase) {
        return "Supabase 환경 변수(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)가 설정되지 않았습니다.";
      }
      if (!user) return "로그인이 필요합니다.";

      const row = toProfileRow(profileData, user.id, user.email);
      const { error } = await supabase.from("profiles").upsert(row, { onConflict: "id" });
      if (error) return error.message;

      setProfile(row as UserProfile);
      setAuthOpen(false);
      setAuthMessage(null);
      setAuthNotice("회원 정보가 저장되었습니다. 이제 서비스를 이용할 수 있습니다.");
      return null;
    },
    [user],
  );

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) {
      return "Supabase 환경 변수(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)가 설정되지 않았습니다.";
    }

    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return translateAuthError(error.message);

    if (data.user) {
      const nextProfile = await refreshProfile(data.user.id);
      if (!isProfileComplete(nextProfile)) {
        setAuthMode("complete");
        setAuthMessage(
          "서비스 이용을 위해 전화번호, 회사명, 직책/직위, 주소, 사용목적을 입력해 주세요.",
        );
        setAuthOpen(true);
        setAuthNotice("로그인되었습니다. 추가 정보를 입력해 주세요.");
        return null;
      }
    }

    setAuthOpen(false);
    setAuthMessage(null);
    setAuthNotice("로그인되었습니다.");
    return null;
  }, [refreshProfile]);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    await supabase.auth.signOut();
    setProfile(null);
    setAuthNotice("로그아웃되었습니다.");
  }, []);

  const profileComplete = isProfileComplete(profile);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      session,
      profile,
      profileComplete,
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
      completeProfile,
      signOut,
      clearAuthNotice,
    }),
    [
      user,
      session,
      profile,
      profileComplete,
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
      completeProfile,
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
