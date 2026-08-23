import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { analyzeContract, getStandardContracts, type StandardContractItem } from "./lib/api";
import { useEffect, useMemo } from "react";
import { StandardContractDetail } from "./components/StandardContractDetail";
import { ContractGenerator } from "./components/ContractGenerator";
import { saveContractUpload } from "./lib/contracts";
import { ReportView } from "./components/ReportView";
import type { ContractReport } from "./types";
import founderPhoto from "./assets/-OzlO6oyRj3-T6ROIXgs_Dropshot.jpg";
import heroVideo from "./assets/0812.mp4";
import testimonialsImage from "./assets/testimonials.png";
import { useAuth } from "./contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import {
  compareDraftToFIDICAPI,
  exportFIDICComparisonJSONReport,
  exportFIDICComparisonReport,
  saveFIDICComparisonResult,
  type FIDICComparisonResponse,
} from "./lib/fidicApi";

type Status = "idle" | "loading" | "error";

const PROMO_DEADLINE = new Date("2026-09-01T00:00:00+09:00");
const isPromoActive = () => Date.now() < PROMO_DEADLINE.getTime();

export default function App() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const LIFECYCLE = [
    { step: "01", title: t("lifecycle.step1.title"), desc: t("lifecycle.step1.desc") },
    { step: "02", title: t("lifecycle.step2.title"), desc: t("lifecycle.step2.desc") },
    { step: "03", title: t("lifecycle.step3.title"), desc: t("lifecycle.step3.desc") },
    { step: "04", title: t("lifecycle.step4.title"), desc: t("lifecycle.step4.desc") },
  ];

  const VALUE_PROPS = [
    { title: t("valueProps.item1.title"), desc: t("valueProps.item1.desc") },
    { title: t("valueProps.item2.title"), desc: t("valueProps.item2.desc") },
    { title: t("valueProps.item3.title"), desc: t("valueProps.item3.desc") },
  ];

  const TESTIMONIALS = [
    {
      quote: t("testimonials.item1.quote"),
      body: t("testimonials.item1.body"),
      author: t("testimonials.item1.author"),
    },
    {
      quote: t("testimonials.item2.quote"),
      body: t("testimonials.item2.body"),
      author: t("testimonials.item2.author"),
    },
    {
      quote: t("testimonials.item3.quote"),
      body: t("testimonials.item3.body"),
      author: t("testimonials.item3.author"),
    },
  ];

  const CONSTRUCTION_DASHBOARD = [
    { label: t("constructionDashboard.item1.label"), value: t("constructionDashboard.item1.value"), detail: t("constructionDashboard.item1.detail") },
    { label: t("constructionDashboard.item2.label"), value: t("constructionDashboard.item2.value"), detail: t("constructionDashboard.item2.detail") },
    { label: t("constructionDashboard.item3.label"), value: t("constructionDashboard.item3.value"), detail: t("constructionDashboard.item3.detail") },
    { label: t("constructionDashboard.item4.label"), value: t("constructionDashboard.item4.value"), detail: t("constructionDashboard.item4.detail") },
  ];

  function toggleLanguage() {
    void i18n.changeLanguage(i18n.language === "en" ? "ko" : "en");
  }

  const { user, authNotice, clearAuthNotice, openAuth, requireAuth, signOut } = useAuth();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ContractReport | null>(null);
  const [standardContracts, setStandardContracts] = useState<StandardContractItem[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string>("all");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [contractTextInput, setContractTextInput] = useState<string>("");
  const [comparisonResult, setComparisonResult] = useState<FIDICComparisonResponse | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState<boolean>(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadRef = useRef<HTMLElement>(null);
  const generatorRef = useRef<HTMLElement>(null);
  const introVideoRef = useRef<HTMLVideoElement>(null);
  const [showIntro, setShowIntro] = useState(true);
  const [needsSoundTap, setNeedsSoundTap] = useState(false);

  useEffect(() => {
    const video = introVideoRef.current;
    if (!video) return;
    video.play().catch(() => setNeedsSoundTap(true));
  }, []);

  function closeIntro() {
    setShowIntro(false);
  }

  function unmuteIntro() {
    const video = introVideoRef.current;
    if (!video) return;
    video.muted = false;
    video.play().catch(() => {});
    setNeedsSoundTap(false);
  }

  useState(() => {
    void getStandardContracts()
      .then(setStandardContracts)
      .catch(() => setStandardContracts([]));
  });

  useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith("/standard-contracts/")) {
      setDetailId(path.split("/").pop() ?? null);
    } else {
      setDetailId(null);
    }
  }, []);

  const groupOptions = useMemo(() => {
    const groups = Array.from(new Set(standardContracts.map((item) => item.group)));
    return [
      { key: "all", label: t("standardContracts.groupAll") },
      { key: "construction", label: t("standardContracts.groupConstruction") },
      ...groups.filter((group) => group !== "건설·플랜트").map((group) => ({ key: group, label: group })),
      ...groups.filter((group) => group === "건설·플랜트").map((group) => ({ key: group, label: group })),
    ];
  }, [standardContracts, t]);

  const visibleContracts = useMemo(() => {
    if (selectedGroup === "all") return standardContracts;
    if (selectedGroup === "construction") {
      return standardContracts.filter((item) => {
        const tags = item.tags.map((tag) => tag.toLowerCase());
        return (
          item.group === "건설·플랜트" ||
          tags.includes("fidic") ||
          tags.includes("건설") ||
          tags.includes("epc") ||
          tags.includes("플랜트")
        );
      });
    }
    return standardContracts.filter((item) => item.group === selectedGroup);
  }, [selectedGroup, standardContracts]);

  async function handleFile(file: File) {
    if (!requireAuth(t("errors.authRequiredUpload"))) {
      return;
    }
    if (!user) return;

    setStatus("loading");
    setError(null);
    setReport(null);
    try {
      const result = await analyzeContract(file);
      await saveContractUpload(user.id, file, result);
      setReport(result);
      setStatus("idle");
      uploadRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      setError(e instanceof Error ? e.message : t("errors.unknown"));
      setStatus("error");
    }
  }

  function triggerUpload() {
    if (!requireAuth(t("errors.authRequiredUpload"))) {
      return;
    }
    inputRef.current?.click();
  }

  async function handleCompareContractText() {
    if (!contractTextInput.trim()) {
      setComparisonError(t("constructionSpecial.errors.emptyCompare"));
      return;
    }
    setComparisonLoading(true);
    setComparisonError(null);
    try {
      const result = await compareDraftToFIDICAPI(contractTextInput);
      setComparisonResult(result);
      await saveFIDICComparisonResult(contractTextInput);
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : t("constructionSpecial.errors.compareFailed"));
    } finally {
      setComparisonLoading(false);
    }
  }


  async function handleExportComparisonReport() {
    if (!contractTextInput.trim()) {
      setComparisonError(t("constructionSpecial.errors.emptyExport"));
      return;
    }
    try {
      await exportFIDICComparisonReport(contractTextInput);
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : t("constructionSpecial.errors.exportFailed"));
    }
  }

  async function handleExportComparisonJSONReport() {
    if (!contractTextInput.trim()) {
      setComparisonError(t("constructionSpecial.errors.emptyExport"));
      return;
    }
    try {
      await exportFIDICComparisonJSONReport(contractTextInput);
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : t("constructionSpecial.errors.exportJsonFailed"));
    }
  }

  return (
    <div className="min-h-screen bg-[var(--tb-sand)] text-[var(--tb-ink)]">
      {showIntro && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 px-4">
          <div className="relative w-full max-w-2xl">
            <button
              type="button"
              onClick={closeIntro}
              className="absolute -top-10 right-0 text-sm font-semibold text-white/80 hover:text-white"
            >
              {t("intro.close")}
            </button>
            <video
              ref={introVideoRef}
              src={heroVideo}
              playsInline
              onEnded={closeIntro}
              className="w-full bg-black"
            />
            {needsSoundTap && (
              <button
                type="button"
                onClick={unmuteIntro}
                className="absolute inset-0 flex items-center justify-center bg-black/40 text-base font-semibold text-white"
              >
                {t("intro.unmute")}
              </button>
            )}
          </div>
        </div>
      )}
      <div className="sticky top-0 z-30">
        {isPromoActive() && (
          <div className="bg-[var(--tb-green-deep)] px-6 py-2.5 text-center text-sm font-semibold text-white">
            <span className="mr-2 rounded-full bg-white/15 px-2 py-0.5 text-xs font-bold uppercase tracking-[0.1em]">
              {t("promo.badge")}
            </span>
            {t("promo.text")}
          </div>
        )}
        <header className="border-b border-[var(--tb-line)]/80 bg-[var(--tb-sand)]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <a href="#" className="font-display text-2xl font-semibold tracking-tight text-[var(--tb-ink)]">
            The Beginning
          </a>
          <div className="flex items-center gap-2 sm:gap-3">
            {user ? (
              <>
                <span className="hidden max-w-[180px] truncate text-sm text-[var(--tb-muted)] sm:inline">
                  {user.email}
                </span>
                <button
                  type="button"
                  onClick={() => void signOut()}
                  className="border border-[var(--tb-line)] bg-white px-4 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                >
                  {t("nav.logout")}
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => openAuth("signup")}
                className="border border-[var(--tb-line)] bg-white px-4 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
              >
                {t("nav.signup")}
              </button>
            )}
            <button
              type="button"
              onClick={() => generatorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
              className="border border-[var(--tb-line)] bg-white px-4 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
            >
              {t("nav.contractGenerator")}
            </button>
            <button
              type="button"
              onClick={triggerUpload}
              disabled={status === "loading"}
              className="bg-[var(--tb-green)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
            >
              {status === "loading" ? t("nav.analyzing") : t("nav.reviewStart")}
            </button>
            <button
              type="button"
              onClick={toggleLanguage}
              className="border border-[var(--tb-line)] bg-white px-3 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
            >
              {t("nav.langToggle")}
            </button>
          </div>
        </div>
        </header>
      </div>

      {authNotice && (
        <div className="border-b border-[var(--tb-green)]/20 bg-[var(--tb-green-soft)] px-6 py-3">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <p className="text-sm text-[var(--tb-green-deep)]">{authNotice}</p>
            <button
              type="button"
              onClick={clearAuthNotice}
              className="shrink-0 text-sm font-semibold text-[var(--tb-green-deep)]"
            >
              {t("authNotice.close")}
            </button>
          </div>
        </div>
      )}

      {/* Hero — Ironclad-style: brand, headline, support, CTA, full-bleed visual */}
      <section className="relative min-h-[min(92vh,920px)] overflow-hidden">
        <div className="absolute inset-0">
          <img
            src={founderPhoto}
            alt=""
            className="tb-hero-media h-full w-full object-cover object-[center_20%]"
          />
          <div className="absolute inset-0 bg-[linear-gradient(105deg,rgba(18,36,28,0.92)_0%,rgba(18,36,28,0.78)_42%,rgba(18,36,28,0.35)_68%,rgba(31,138,91,0.25)_100%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_20%,rgba(31,138,91,0.22),transparent_55%)]" />
        </div>

        <div className="relative mx-auto flex min-h-[min(92vh,920px)] max-w-6xl flex-col justify-end px-6 pb-16 pt-28 sm:pb-24 sm:pt-32">
          <p className="tb-fade-up font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl md:text-6xl">
            The Beginning
          </p>
          <h1 className="tb-fade-up tb-fade-up-delay-1 mt-5 max-w-3xl font-display text-3xl font-medium leading-[1.15] tracking-tight text-white sm:text-4xl md:text-5xl">
            {t("hero.titleLine1")}
            <br />
            <em className="not-italic text-[var(--tb-green-soft)]">{t("hero.titleEm")}</em>
          </h1>
          <p className="tb-fade-up tb-fade-up-delay-2 mt-5 max-w-xl text-base leading-relaxed text-white/80 sm:text-lg">
            {t("hero.subtitle")}
          </p>
          <div className="tb-fade-up tb-fade-up-delay-3 mt-8 flex flex-wrap items-center gap-4">
            <input
              ref={inputRef}
              type="file"
              accept=".txt,.pdf,.docx,.doc"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
                e.target.value = "";
              }}
            />
            <button
              type="button"
              onClick={triggerUpload}
              disabled={status === "loading"}
              className="bg-[var(--tb-green)] px-7 py-3.5 text-base font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
            >
              {status === "loading" ? t("hero.uploadCtaLoading") : t("hero.uploadCta")}
            </button>
            <p className="text-sm text-white/70">
              {t("hero.formats")}
            </p>
          </div>
          {error && (
            <div className="mt-6 max-w-xl border border-rose-300/40 bg-rose-950/50 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          )}
        </div>
      </section>

      {/* Trust / outcomes — Ironclad metric strip style */}
      <section className="border-y border-[var(--tb-line)] bg-white">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 py-12 sm:grid-cols-3">
          {[
            { label: t("metrics.item1.label"), value: t("metrics.item1.value"), note: t("metrics.item1.note") },
            { label: t("metrics.item2.label"), value: t("metrics.item2.value"), note: t("metrics.item2.note") },
            { label: t("metrics.item3.label"), value: t("metrics.item3.value"), note: t("metrics.item3.note") },
          ].map((item) => (
            <div key={item.label}>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--tb-green)]">
                {item.label}
              </p>
              <p className="mt-2 font-display text-2xl font-semibold text-[var(--tb-ink)] sm:text-3xl">
                {item.value}
              </p>
              <p className="mt-1 text-sm text-[var(--tb-muted)]">{item.note}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Contract review loop — Ironclad lifecycle visualization */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            {t("reviewLoop.eyebrow")}
          </p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl font-semibold tracking-tight text-[var(--tb-ink)] sm:text-4xl">
            {t("reviewLoop.titleLine1")}
            <br />
            {t("reviewLoop.titleLine2")}
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-[var(--tb-muted)]">
            {t("reviewLoop.subtitle")}
          </p>

          <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {LIFECYCLE.map((item, idx) => (
              <li
                key={item.step}
                className="relative border border-[var(--tb-line)] bg-white p-6"
              >
                <span
                  className={`inline-flex h-10 w-10 items-center justify-center bg-[var(--tb-green-soft)] text-sm font-bold text-[var(--tb-green-deep)] ${idx === 0 ? "tb-loop-node" : ""}`}
                >
                  {item.step}
                </span>
                <h3 className="mt-4 font-display text-xl font-semibold text-[var(--tb-ink)]">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--tb-muted)]">{item.desc}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Value props — one job per section, no emoji cards */}
      <section className="border-t border-[var(--tb-line)] bg-white px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            {t("whyUs.eyebrow")}
          </p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("whyUs.titleLine1")}
            <br />
            {t("whyUs.titleLine2")}
          </h2>
          <div className="mt-12 grid gap-10 md:grid-cols-3">
            {VALUE_PROPS.map((item) => (
              <div key={item.title} className="border-t-2 border-[var(--tb-green)] pt-5">
                <h3 className="font-display text-xl font-semibold text-[var(--tb-ink)]">
                  {item.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-[var(--tb-muted)]">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* User testimonials */}
      <section className="border-t border-[var(--tb-line)] bg-white px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            Testimonials
          </p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("testimonials.heading")}
          </h2>
          <div className="mt-8 grid gap-8 lg:grid-cols-2 lg:items-stretch">
            <div className="overflow-hidden rounded-2xl border border-[var(--tb-line)]">
              <img
                src={testimonialsImage}
                alt={t("testimonials.imageAlt")}
                className="mx-auto h-full w-full max-w-xl object-cover"
              />
            </div>
            <div className="grid grid-rows-3 gap-6">
              {TESTIMONIALS.map((item) => (
                <div key={item.author} className="flex flex-col justify-center rounded-2xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-6">
                  <p className="font-display text-lg font-semibold leading-snug text-[var(--tb-ink)]">
                    “{item.quote}”
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-[var(--tb-muted)]">{item.body}</p>
                  <p className="mt-4 text-sm font-semibold text-[var(--tb-ink)]">👤 {item.author}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Standard contracts library */}
      <section className="border-t border-[var(--tb-line)] bg-white px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            Standard Contracts
          </p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("standardContracts.titleLine1")}
            <br />
            {t("standardContracts.titleLine2")}
          </h2>
          <p className="mt-4 max-w-2xl text-base text-[var(--tb-muted)]">
            {t("standardContracts.subtitle")}
          </p>

          {detailId ? (
            <div className="mt-8">
              <StandardContractDetail
                itemId={detailId}
                onBack={() => {
                  window.history.pushState({}, "", "/");
                  setDetailId(null);
                }}
              />
            </div>
          ) : (
            <>
              <div className="mt-8 flex flex-wrap gap-2">
                {groupOptions.map((group) => (
                  <button
                    key={group.key}
                    type="button"
                    onClick={() => setSelectedGroup(group.key)}
                    className={`rounded-full border px-3 py-1.5 text-sm ${selectedGroup === group.key ? "border-[var(--tb-green)] bg-[var(--tb-green-soft)] text-[var(--tb-green-deep)]" : "border-[var(--tb-line)] text-[var(--tb-muted)]"}`}
                  >
                    {group.label}
                  </button>
                ))}
              </div>

              <div className="mt-8 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                {visibleContracts.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      window.history.pushState({}, "", `/standard-contracts/${item.id}`);
                      setDetailId(item.id);
                    }}
                    className="flex h-full flex-col border border-[var(--tb-line)] bg-[var(--tb-sand)] p-6 text-left transition hover:-translate-y-0.5 hover:border-[var(--tb-green)]"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="rounded-full bg-[var(--tb-green-soft)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--tb-green-deep)]">
                        {item.category}
                      </span>
                      <span className="text-xs text-[var(--tb-muted)]">{item.group}</span>
                    </div>
                    <h3 className="mt-5 font-display text-xl font-semibold text-[var(--tb-ink)]">
                      {item.title}
                    </h3>
                    <p className="mt-3 flex-1 text-sm leading-relaxed text-[var(--tb-muted)]">
                      {item.description}
                    </p>
                    <p className="mt-3 text-sm leading-relaxed text-[var(--tb-ink)]">
                      {item.detail}
                    </p>
                    <div className="mt-5 flex flex-wrap gap-2">
                      {item.tags.map((tag) => (
                        <span key={tag} className="rounded-full border border-[var(--tb-line)] px-2.5 py-1 text-xs text-[var(--tb-muted)]">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      <section className="border-t border-[var(--tb-line)] bg-[var(--tb-sand)] px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <p className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("constructionSpecial.label")}
          </p>

          <div className="mt-3 mb-8 rounded-2xl border border-[var(--tb-line)] bg-white p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
              {t("constructionSpecial.dashboardEyebrow")}
            </p>
            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {CONSTRUCTION_DASHBOARD.map((item) => (
                <div key={item.label} className="rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--tb-muted)]">{item.label}</p>
                  <p className="mt-2 font-display text-lg font-semibold text-[var(--tb-ink)]">{item.value}</p>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--tb-muted)]">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            {t("constructionSpecial.engineEyebrow")}
          </p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("constructionSpecial.titleLine1")}
            <br />
            {t("constructionSpecial.titleLine2")}
          </h2>

          <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-6 shadow-sm">
              <label className="block text-sm font-semibold text-[var(--tb-ink)]">
                {t("constructionSpecial.pasteLabel")}
              </label>
              <textarea
                value={contractTextInput}
                onChange={(e) => setContractTextInput(e.target.value)}
                rows={12}
                placeholder={t("constructionSpecial.pastePlaceholder")}
                className="mt-3 w-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-4 py-3 text-sm leading-relaxed text-[var(--tb-ink)] focus:border-[var(--tb-green)] focus:outline-none"
              />
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleCompareContractText}
                  disabled={comparisonLoading}
                  className="bg-[var(--tb-green)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
                >
                  {comparisonLoading ? t("constructionSpecial.comparing") : t("constructionSpecial.compareCta")}
                </button>
                <button
                  type="button"
                  onClick={() => setContractTextInput("")}
                  className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                >
                  {t("constructionSpecial.reset")}
                </button>
                {comparisonResult && (
                  <>
                    <button
                      type="button"
                      onClick={handleExportComparisonReport}
                      className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                    >
                      {t("constructionSpecial.exportPdf")}
                    </button>
                    <button
                      type="button"
                      onClick={handleExportComparisonJSONReport}
                      className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                    >
                      {t("constructionSpecial.exportJson")}
                    </button>
                  </>
                )}
              </div>
              {comparisonError && (
                <div className="mt-4 border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {comparisonError}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-6 shadow-sm">
              {comparisonResult ? (
                <>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--tb-green)]">
                    {t("constructionSpecial.matchScoreLabel")}
                  </p>
                  <div className="mt-4 flex items-end gap-3">
                    <span className="font-display text-5xl font-semibold text-[var(--tb-ink)]">
                      {comparisonResult.overall_score}
                    </span>
                    <span className="pb-2 text-sm text-[var(--tb-muted)]">{t("constructionSpecial.scoreOutOf")}</span>
                  </div>
                  <div className="mt-4 rounded-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2 text-sm font-semibold text-[var(--tb-ink)]">
                    {t("constructionSpecial.biasLabel", { balance: comparisonResult.balance })}
                  </div>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-3 text-sm">
                      <div className="text-[var(--tb-muted)]">{t("constructionSpecial.employerBias")}</div>
                      <div className="mt-1 text-lg font-semibold text-[var(--tb-ink)]">{comparisonResult.bias_scores.employer}</div>
                    </div>
                    <div className="rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-3 text-sm">
                      <div className="text-[var(--tb-muted)]">{t("constructionSpecial.contractorBias")}</div>
                      <div className="mt-1 text-lg font-semibold text-[var(--tb-ink)]">{comparisonResult.bias_scores.contractor}</div>
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-relaxed text-[var(--tb-muted)]">
                    {comparisonResult.summary}
                  </p>
                  {comparisonResult.focus_areas.length > 0 && (
                    <div className="mt-5 flex flex-wrap gap-2">
                      {comparisonResult.focus_areas.map((area) => (
                        <span
                          key={area}
                          className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
                        >
                          {area}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="flex h-full items-center justify-center text-sm leading-relaxed text-[var(--tb-muted)]">
                  {t("constructionSpecial.emptyResult")}
                </div>
              )}
            </div>
          </div>

          {comparisonResult && (
            <div className="mt-8 space-y-4">
              {comparisonResult.issues.map((issue) => (
                <div key={issue.id} className="rounded-2xl border border-[var(--tb-line)] bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-[var(--tb-ink)]">{issue.label}</p>
                      <p className="mt-1 text-xs text-[var(--tb-muted)]">{issue.fidic_benchmark}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          issue.status === "good"
                            ? "bg-emerald-100 text-emerald-700"
                            : issue.status === "watch"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {issue.status === "good" ? t("constructionSpecial.status.good") : issue.status === "watch" ? t("constructionSpecial.status.watch") : t("constructionSpecial.status.risk")}
                      </span>
                      <span className="text-lg font-semibold text-[var(--tb-ink)]">{issue.score}</span>
                    </div>
                  </div>
                  <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-[var(--tb-sand)]">
                    <div
                      className={`h-full ${
                        issue.status === "good"
                          ? "bg-emerald-500"
                          : issue.status === "watch"
                            ? "bg-amber-500"
                            : "bg-rose-500"
                      }`}
                      style={{ width: `${issue.score}%` }}
                    />
                  </div>
                  {issue.sentence_evidence && issue.sentence_evidence.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--tb-green)]">{t("constructionSpecial.evidenceLabel")}</p>
                      <ul className="space-y-2">
                        {issue.sentence_evidence.map((sentence) => (
                          <li key={sentence} className="rounded-lg border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2 text-sm leading-relaxed text-[var(--tb-ink)]">
                            {sentence}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {issue.evidence.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {issue.evidence.map((evidence) => (
                        <span key={evidence} className="rounded-full border border-[var(--tb-line)] px-2.5 py-1 text-xs text-[var(--tb-muted)]">
                          {evidence}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="mt-4 text-sm leading-relaxed text-[var(--tb-muted)]">{issue.recommendation}</p>
                </div>
              ))}
            </div>
          )}

          {user && (
            <div className="mt-8 rounded-2xl border border-[var(--tb-line)] bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--tb-green)]">{t("constructionSpecial.mySavedHistory")}</p>
                <button
                  type="button"
                  onClick={() => navigate("/fidic-history")}
                  className="text-xs font-semibold text-[var(--tb-green)] underline-offset-2 hover:underline"
                >
                  {t("constructionSpecial.viewAll")}
                </button>
              </div>
              <p className="mt-2 text-sm text-[var(--tb-muted)]">{t("constructionSpecial.savedHistoryDesc")}</p>
            </div>
          )}
        </div>
      </section>

      {/* Contract generator */}
      <section ref={generatorRef} className="border-t border-[var(--tb-line)] bg-[var(--tb-sand)] px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            Contract Generator
          </p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl font-semibold tracking-tight text-[var(--tb-ink)] sm:text-4xl">
            {t("contractGeneratorSection.titleLine1")}
            <br />
            {t("contractGeneratorSection.titleLine2")}
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-[var(--tb-muted)]">
            {t("contractGeneratorSection.subtitle")}
          </p>

          <ContractGenerator requireAuth={requireAuth} />
        </div>
      </section>

      {/* Upload / results anchor */}
      <section ref={uploadRef} className="border-t border-[var(--tb-line)] px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
                Start Review
              </p>
              <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
                {t("startReview.titleLine1")}
                <br />
                {t("startReview.titleLine2")}
              </h2>
              <p className="mt-4 max-w-xl text-base text-[var(--tb-muted)]">
                {t("startReview.formats")}
                <br />
                <span className="font-semibold text-[var(--tb-ink)]">
                  {t("startReview.maxPages")}
                </span>
              </p>
            </div>
            <button
              type="button"
              onClick={triggerUpload}
              disabled={status === "loading"}
              className="shrink-0 bg-[var(--tb-green)] px-7 py-3.5 text-base font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
            >
              {status === "loading" ? t("hero.uploadCtaLoading") : t("hero.uploadCta")}
            </button>
          </div>

          {error && (
            <div className="mt-8 border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          {report && (
            <div className="mt-12">
              <ReportView report={report} />
            </div>
          )}
        </div>
      </section>

      <footer className="border-t border-[var(--tb-line)] bg-[var(--tb-ink)] px-6 py-12 text-white/70">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-display text-2xl font-semibold text-white">The Beginning</p>
            <p className="mt-2 max-w-lg text-sm leading-relaxed">
              {t("footer.disclaimer")}
            </p>
          </div>
          <p className="text-xs">{t("footer.copyright")}</p>
        </div>
      </footer>
    </div>
  );
}
