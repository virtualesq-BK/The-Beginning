import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";

const PRO_MAILTO = `mailto:virtual.esq@gmail.com?subject=${encodeURIComponent("Pro 플랜 구매 요청")}&body=${encodeURIComponent("The Beginning Pro 플랜(₩49,000/건) 구매를 요청합니다.\n\n이름:\n회사명:\n이메일:")}`;

interface Props {
  children: React.ReactNode;
  /** 페이월 설명 오버라이드 */
  desc?: string;
}

export function PaywallGate({ children, desc }: Props) {
  const { t } = useTranslation();
  const { isPro, requireAuth } = useAuth();

  if (isPro) return <>{children}</>;

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

        <a
          href={PRO_MAILTO}
          onClick={() => requireAuth(t("paywall.authRequired"))}
          className="mt-5 inline-flex items-center gap-2 bg-[var(--tb-green)] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)]"
        >
          {t("paywall.cta")}
          <span aria-hidden>→</span>
        </a>

        <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
          {t("paywall.hint")}
        </p>
      </div>
    </div>
  );
}
