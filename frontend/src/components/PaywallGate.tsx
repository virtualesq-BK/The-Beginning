import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";

const PRO_EMAIL = "virtual.esq@gmail.com";
const PRO_SUBJECT = "Pro 플랜 구매 요청";
const PRO_BODY = "The Beginning Pro 플랜(₩49,000/건) 구매를 요청합니다.\n\n이름:\n회사명:\n이메일:";
const PRO_MAILTO = `mailto:${PRO_EMAIL}?subject=${encodeURIComponent(PRO_SUBJECT)}&body=${encodeURIComponent(PRO_BODY)}`;

interface Props {
  children: React.ReactNode;
  /** 페이월 설명 오버라이드 */
  desc?: string;
}

export function PaywallGate({ children, desc }: Props) {
  const { t } = useTranslation();
  const { isPro, requireAuth } = useAuth();
  const [showContact, setShowContact] = useState(false);
  const [copied, setCopied] = useState(false);

  if (isPro) return <>{children}</>;

  function handleUpgradeClick() {
    if (!requireAuth(t("paywall.authRequired"))) return;
    setShowContact(true);
  }

  function handleCopy() {
    navigator.clipboard.writeText(PRO_EMAIL).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="relative overflow-hidden rounded-2xl">
      {/* 블러 처리된 미리보기 */}
      <div className="pointer-events-none select-none blur-sm opacity-60" aria-hidden>
        {children}
      </div>

      {/* 페이월 오버레이 */}
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/85 dark:bg-slate-950/85 px-8 py-10 text-center backdrop-blur-sm">
        <span className="text-3xl" aria-hidden>🔒</span>
        <h3 className="mt-3 text-base font-semibold text-slate-900 dark:text-white">
          {t("paywall.title")}
        </h3>
        <p className="mt-2 max-w-xs text-sm text-slate-500 dark:text-slate-400">
          {desc ?? t("paywall.desc")}
        </p>

        <button
          type="button"
          onClick={handleUpgradeClick}
          className="mt-5 inline-flex items-center gap-2 bg-[var(--tb-green)] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)]"
        >
          {t("paywall.cta")}
          <span aria-hidden>→</span>
        </button>

        <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
          {t("paywall.hint")}
        </p>
      </div>

      {/* 메일 앱이 열리지 않을 때 fallback 모달 */}
      {showContact && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6"
          onClick={() => setShowContact(false)}
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-white p-8 text-center shadow-xl dark:bg-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            <span className="text-3xl" aria-hidden>✉️</span>
            <h3 className="mt-3 text-base font-semibold text-slate-900 dark:text-white">
              Pro 구매 문의
            </h3>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              아래 이메일로 직접 문의해 주세요.
            </p>
            <div className="mt-4 flex items-center justify-center gap-2 rounded-lg bg-slate-50 px-4 py-3 dark:bg-slate-800">
              <span className="text-sm font-mono text-slate-800 dark:text-slate-200 select-all">
                {PRO_EMAIL}
              </span>
              <button
                type="button"
                onClick={handleCopy}
                className="shrink-0 rounded-md bg-[var(--tb-green)]/10 px-2.5 py-1 text-xs font-semibold text-[var(--tb-green-deep)] transition hover:bg-[var(--tb-green)]/20"
              >
                {copied ? "복사됨 ✓" : "복사"}
              </button>
            </div>
            <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
              제목: {PRO_SUBJECT}
            </p>
            <a
              href={PRO_MAILTO}
              className="mt-4 inline-flex items-center gap-1 text-sm text-[var(--tb-green-deep)] underline underline-offset-2"
            >
              메일 앱으로 열기 →
            </a>
            <div className="mt-4">
              <button
                type="button"
                onClick={() => setShowContact(false)}
                className="text-sm text-slate-400 hover:text-slate-600"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
