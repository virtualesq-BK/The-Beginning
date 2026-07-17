import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../contexts/AuthContext";
import { USAGE_PURPOSE_OPTIONS, type UsagePurpose } from "../types/auth";

const inputClass =
  "mt-1.5 w-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2.5 text-sm outline-none transition focus:border-[var(--tb-green)]";

export function AuthModal() {
  const {
    authOpen,
    authMode,
    authMessage,
    configured,
    user,
    profile,
    closeAuth,
    openAuth,
    signUp,
    signIn,
    completeProfile,
  } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [address, setAddress] = useState("");
  const [usagePurposes, setUsagePurposes] = useState<UsagePurpose[]>([]);
  const [otherRequests, setOtherRequests] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const isCompleteMode = authMode === "complete";
  const showProfileFields = authMode === "signup" || isCompleteMode;

  useEffect(() => {
    if (!authOpen) {
      setError(null);
      setInfo(null);
      setSubmitting(false);
      if (authMode !== "complete") {
        setEmail("");
        setPassword("");
        setFullName("");
        setPhone("");
        setCompanyName("");
        setJobTitle("");
        setAddress("");
        setUsagePurposes([]);
        setOtherRequests("");
      }
      return;
    }

    if (authMode === "complete") {
      setEmail(user?.email ?? profile?.email ?? "");
      setFullName(profile?.full_name ?? "");
      setPhone(profile?.phone ?? "");
      setCompanyName(profile?.company_name ?? "");
      setJobTitle(profile?.job_title ?? "");
      setAddress(profile?.address ?? "");
      setUsagePurposes(
        (profile?.usage_purposes ?? []).filter((value): value is UsagePurpose =>
          USAGE_PURPOSE_OPTIONS.some((option) => option.value === value),
        ),
      );
      setOtherRequests(profile?.other_requests ?? "");
      setPassword("");
    }
  }, [authOpen, authMode, profile, user]);

  if (!authOpen) return null;

  function togglePurpose(value: UsagePurpose) {
    setUsagePurposes((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value],
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);

    try {
      if (authMode === "login") {
        const message = await signIn(email.trim(), password);
        if (message) setError(message);
        return;
      }

      if (usagePurposes.length === 0) {
        setError("사용목적을 하나 이상 선택해 주세요.");
        return;
      }

      const profilePayload = {
        fullName: fullName.trim(),
        phone: phone.trim(),
        companyName: companyName.trim(),
        jobTitle: jobTitle.trim(),
        address: address.trim(),
        usagePurposes,
        otherRequests: otherRequests.trim(),
      };

      if (authMode === "complete") {
        const message = await completeProfile(profilePayload);
        if (message) setError(message);
        return;
      }

      const message = await signUp(email.trim(), password, profilePayload);
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

  const title =
    authMode === "signup" ? "회원 가입" : authMode === "complete" ? "회원 정보 입력" : "로그인";

  const description =
    authMode === "signup"
      ? "서비스 이용을 위해 기본 정보와 사용목적을 입력해 주세요."
      : authMode === "complete"
        ? "이메일 확인은 완료되었습니다. 추가 정보를 입력해야 서비스를 이용할 수 있습니다."
        : "가입한 이메일로 로그인해 주세요.";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--tb-ink)]/45 px-4 py-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      onClick={closeAuth}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto border border-[var(--tb-line)] bg-white p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="auth-modal-title" className="font-display text-2xl font-semibold text-[var(--tb-ink)]">
              {title}
            </h2>
            <p className="mt-2 text-sm text-[var(--tb-muted)]">{description}</p>
          </div>
          {!isCompleteMode && (
            <button
              type="button"
              onClick={closeAuth}
              className="text-sm font-semibold text-[var(--tb-muted)] transition hover:text-[var(--tb-ink)]"
            >
              닫기
            </button>
          )}
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
          {(authMode === "login" || authMode === "signup" || isCompleteMode) && (
            <label className="block text-sm font-medium text-[var(--tb-ink)]">
              이메일
              <input
                type="email"
                required={authMode !== "complete"}
                readOnly={isCompleteMode}
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`${inputClass} ${isCompleteMode ? "opacity-70" : ""}`}
              />
            </label>
          )}

          {(authMode === "login" || authMode === "signup") && (
            <label className="block text-sm font-medium text-[var(--tb-ink)]">
              비밀번호
              <input
                type="password"
                required
                minLength={6}
                autoComplete={authMode === "signup" ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
              />
            </label>
          )}

          {showProfileFields && (
            <>
              <label className="block text-sm font-medium text-[var(--tb-ink)]">
                이름
                <input
                  type="text"
                  required
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={inputClass}
                />
              </label>

              <label className="block text-sm font-medium text-[var(--tb-ink)]">
                전화번호
                <input
                  type="tel"
                  required
                  autoComplete="tel"
                  placeholder="010-0000-0000"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className={inputClass}
                />
              </label>

              <label className="block text-sm font-medium text-[var(--tb-ink)]">
                회사명
                <input
                  type="text"
                  required
                  autoComplete="organization"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className={inputClass}
                />
              </label>

              <label className="block text-sm font-medium text-[var(--tb-ink)]">
                직책/직위
                <input
                  type="text"
                  required
                  autoComplete="organization-title"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  className={inputClass}
                />
              </label>

              <label className="block text-sm font-medium text-[var(--tb-ink)]">
                주소
                <input
                  type="text"
                  required
                  autoComplete="street-address"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className={inputClass}
                />
              </label>

              <fieldset>
                <legend className="text-sm font-medium text-[var(--tb-ink)]">
                  사용목적 <span className="font-normal text-[var(--tb-muted)]">(복수 선택 가능)</span>
                </legend>
                <div className="mt-2 space-y-2 border border-[var(--tb-line)] bg-[var(--tb-sand)] p-3">
                  {USAGE_PURPOSE_OPTIONS.map((option) => (
                    <label key={option.value} className="flex items-center gap-2 text-sm text-[var(--tb-ink)]">
                      <input
                        type="checkbox"
                        checked={usagePurposes.includes(option.value)}
                        onChange={() => togglePurpose(option.value)}
                        className="h-4 w-4 accent-[var(--tb-green)]"
                      />
                      {option.label}
                    </label>
                  ))}
                </div>
              </fieldset>

              <label className="block text-sm font-medium text-[var(--tb-ink)]">
                기타 요청 사항
                <textarea
                  rows={3}
                  value={otherRequests}
                  onChange={(e) => setOtherRequests(e.target.value)}
                  placeholder="추가로 전달할 내용이 있으면 적어 주세요."
                  className={`${inputClass} resize-y`}
                />
              </label>
            </>
          )}

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
                : authMode === "complete"
                  ? "정보 저장하고 시작하기"
                  : "로그인하기"}
          </button>
        </form>

        {authMode !== "complete" && (
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
        )}
      </div>
    </div>
  );
}
