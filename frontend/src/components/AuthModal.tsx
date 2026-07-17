import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../contexts/AuthContext";

export function AuthModal() {
  const {
    authOpen,
    authMode,
    authMessage,
    configured,
    closeAuth,
    openAuth,
    signUp,
    signIn,
  } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (!authOpen) {
      setEmail("");
      setPassword("");
      setError(null);
      setInfo(null);
      setSubmitting(false);
    }
  }, [authOpen]);

  if (!authOpen) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);

    try {
      const message =
        authMode === "signup" ? await signUp(email.trim(), password) : await signIn(email.trim(), password);

      if (message) {
        if (message.includes("가입 메일") || message.includes("확인 링크")) {
          setInfo(message);
          openAuth("login", "이메일 확인 후 로그인해 주세요.");
        } else {
          setError(message);
        }
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--tb-ink)]/45 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      onClick={closeAuth}
    >
      <div
        className="w-full max-w-md border border-[var(--tb-line)] bg-white p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="auth-modal-title" className="font-display text-2xl font-semibold text-[var(--tb-ink)]">
              {authMode === "signup" ? "회원 가입" : "로그인"}
            </h2>
            <p className="mt-2 text-sm text-[var(--tb-muted)]">
              {authMode === "signup"
                ? "이메일과 비밀번호로 The Beginning 계정을 만듭니다."
                : "가입한 이메일로 로그인해 주세요."}
            </p>
          </div>
          <button
            type="button"
            onClick={closeAuth}
            className="text-sm font-semibold text-[var(--tb-muted)] transition hover:text-[var(--tb-ink)]"
          >
            닫기
          </button>
        </div>

        {authMessage && (
          <p className="mt-4 border border-[var(--tb-green)]/20 bg-[var(--tb-green-soft)] px-3 py-2 text-sm text-[var(--tb-green-deep)]">
            {authMessage}
          </p>
        )}

        {!configured && (
          <p className="mt-4 border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Supabase 연결을 위해 `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` 환경 변수가
            필요합니다.
          </p>
        )}

        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-[var(--tb-ink)]">
            이메일
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1.5 w-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2.5 text-sm outline-none transition focus:border-[var(--tb-green)]"
            />
          </label>

          <label className="block text-sm font-medium text-[var(--tb-ink)]">
            비밀번호
            <input
              type="password"
              required
              minLength={6}
              autoComplete={authMode === "signup" ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1.5 w-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2.5 text-sm outline-none transition focus:border-[var(--tb-green)]"
            />
          </label>

          {error && <p className="text-sm text-rose-600">{error}</p>}
          {info && <p className="text-sm text-[var(--tb-green-deep)]">{info}</p>}

          <button
            type="submit"
            disabled={submitting || !configured}
            className="w-full bg-[var(--tb-green)] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
          >
            {submitting
              ? "처리 중..."
              : authMode === "signup"
                ? "회원 가입하기"
                : "로그인하기"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-[var(--tb-muted)]">
          {authMode === "signup" ? (
            <>
              이미 계정이 있으신가요?{" "}
              <button
                type="button"
                className="font-semibold text-[var(--tb-green-deep)] underline-offset-2 hover:underline"
                onClick={() => openAuth("login", authMessage ?? undefined)}
              >
                로그인
              </button>
            </>
          ) : (
            <>
              계정이 없으신가요?{" "}
              <button
                type="button"
                className="font-semibold text-[var(--tb-green-deep)] underline-offset-2 hover:underline"
                onClick={() => openAuth("signup", authMessage ?? undefined)}
              >
                회원 가입
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
