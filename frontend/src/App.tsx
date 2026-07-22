import { useRef, useState } from "react";
import { analyzeContract, getStandardContracts, type StandardContractItem } from "./lib/api";
import { useEffect, useMemo } from "react";
import { StandardContractDetail } from "./components/StandardContractDetail";
import { saveContractUpload } from "./lib/contracts";
import { ReportView } from "./components/ReportView";
import type { ContractReport } from "./types";
import founderPhoto from "./assets/founder.jpg";
import { useAuth } from "./contexts/AuthContext";

type Status = "idle" | "loading" | "error";

const LIFECYCLE = [
  { step: "01", title: "번역 요약", desc: "해외 계약 조항을 한국어로 정리합니다." },
  { step: "02", title: "리스크 검토", desc: "고위험 조항과 근거를 먼저 보여줍니다." },
  { step: "03", title: "협상 체크", desc: "수정·협상 포인트를 체크리스트로 만듭니다." },
  { step: "04", title: "전문가 연결", desc: "필요하면 검수·법률 전문가로 이어집니다." },
];

const VALUE_PROPS = [
  {
    title: "해외 계약에 특화",
    desc: "FIDIC·EPC·지체상금·하자담보 등 다양한 해외 계약 실무 리스크를 중심으로 1차 검토합니다.",
  },
  {
    title: "근거가 남는 AI 검토",
    desc: "SAC-RAG로 국제 실무 기준을 검색해, 위험 판정마다 출처를 함께 제시합니다.",
  },
  {
    title: "한국어로 바로 의사결정",
    desc: "번역·리스크·협상 포인트를 한 흐름으로 제공해 검토 시간을 줄입니다.",
  },
];

export default function App() {
  const { user, authNotice, clearAuthNotice, openAuth, requireAuth, signOut } = useAuth();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ContractReport | null>(null);
  const [standardContracts, setStandardContracts] = useState<StandardContractItem[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string>("all");
  const [detailId, setDetailId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadRef = useRef<HTMLElement>(null);

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
    return ["all", ...groups];
  }, [standardContracts]);

  const visibleContracts = useMemo(() => {
    if (selectedGroup === "all") return standardContracts;
    return standardContracts.filter((item) => item.group === selectedGroup);
  }, [selectedGroup, standardContracts]);

  async function handleFile(file: File) {
    if (
      !requireAuth(
        "문서를 Supabase에 저장하고 분석하려면 로그인과 회원 정보 입력이 필요합니다.",
      )
    ) {
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
      setError(e instanceof Error ? e.message : "알 수 없는 오류가 발생했습니다.");
      setStatus("error");
    }
  }

  function triggerUpload() {
    if (
      !requireAuth(
        "문서를 Supabase에 저장하고 분석하려면 로그인과 회원 정보 입력이 필요합니다.",
      )
    ) {
      return;
    }
    inputRef.current?.click();
  }

  return (
    <div className="min-h-screen bg-[var(--tb-sand)] text-[var(--tb-ink)]">
      <header className="sticky top-0 z-20 border-b border-[var(--tb-line)]/80 bg-[var(--tb-sand)]/90 backdrop-blur-md">
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
                  로그아웃
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => openAuth("signup")}
                className="border border-[var(--tb-line)] bg-white px-4 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
              >
                회원 가입
              </button>
            )}
            <button
              type="button"
              onClick={triggerUpload}
              disabled={status === "loading"}
              className="bg-[var(--tb-green)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
            >
              {status === "loading" ? "분석 중..." : "계약서 검토 시작"}
            </button>
          </div>
        </div>
      </header>

      {authNotice && (
        <div className="border-b border-[var(--tb-green)]/20 bg-[var(--tb-green-soft)] px-6 py-3">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <p className="text-sm text-[var(--tb-green-deep)]">{authNotice}</p>
            <button
              type="button"
              onClick={clearAuthNotice}
              className="shrink-0 text-sm font-semibold text-[var(--tb-green-deep)]"
            >
              닫기
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
            해외 계약을 움직이고,
            <br />
            <em className="not-italic text-[var(--tb-green-soft)]">리스크를 먼저 드러냅니다</em>
          </h1>
          <p className="tb-fade-up tb-fade-up-delay-2 mt-5 max-w-xl text-base leading-relaxed text-white/80 sm:text-lg">
            특히 대규모 해외 건설 사업인 FIDIC·EPC 실무도 포함하여 AI가 번역 요약부터 주요 리스크, 협상 체크리스트까지 한 번에
            정리합니다.
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
              {status === "loading" ? "분석 중... (최대 1분)" : "계약서 업로드하고 분석하기"}
            </button>
            <p className="text-sm text-white/70">
              .txt · .pdf · .docx · .doc · 최대 5페이지
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
            { label: "1차 검토 속도", value: "수 분 내", note: "업로드 후 AI 분석" },
            { label: "검토 범위", value: "번역·리스크·협상", note: "의사결정에 필요한 핵심만" },
            { label: "다음 단계", value: "전문가 연결", note: "검수·해외 법률 자문" },
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
            Review Loop
          </p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl font-semibold tracking-tight text-[var(--tb-ink)] sm:text-4xl">
            계약 검토의 전 과정을
            <br />
            하나의 루프로
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-[var(--tb-muted)]">
            업로드부터 번역·리스크·협상·전문가 연결까지, 계약 검토 흐름을 끊김 없이 이어줍니다.
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
            Why The Beginning
          </p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            팀이 실제로 쓰는
            <br />
            계약 인텔리전스
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

      {/* Standard contracts library */}
      <section className="border-t border-[var(--tb-line)] bg-white px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            Standard Contracts
          </p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            해외 사업에 바로 쓰는
            <br />
            표준계약서 자료를 열람하세요
          </h2>
          <p className="mt-4 max-w-2xl text-base text-[var(--tb-muted)]">
            ITC·ICC·국내 기관 자료를 기준으로, 준거법·중재·CISG·현지 강행규정 체크 포인트까지 함께 안내합니다.
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
                <button
                  type="button"
                  onClick={() => setSelectedGroup("all")}
                  className={`rounded-full border px-3 py-1.5 text-sm ${selectedGroup === "all" ? "border-[var(--tb-green)] bg-[var(--tb-green-soft)] text-[var(--tb-green-deep)]" : "border-[var(--tb-line)] text-[var(--tb-muted)]"}`}
                >
                  전체
                </button>
                {groupOptions
                  .filter((group) => group !== "all")
                  .map((group) => (
                    <button
                      key={group}
                      type="button"
                      onClick={() => setSelectedGroup(group)}
                      className={`rounded-full border px-3 py-1.5 text-sm ${selectedGroup === group ? "border-[var(--tb-green)] bg-[var(--tb-green-soft)] text-[var(--tb-green-deep)]" : "border-[var(--tb-line)] text-[var(--tb-muted)]"}`}
                    >
                      {group}
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

      {/* Upload / results anchor */}
      <section ref={uploadRef} className="border-t border-[var(--tb-line)] px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
                Start Review
              </p>
              <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
                지금 바로 1차 검토를
                <br />
                시작하세요
              </h2>
              <p className="mt-4 max-w-xl text-base text-[var(--tb-muted)]">
                지원 형식: .txt · .pdf · .docx · .doc (스캔 이미지 PDF는 미지원)
                <br />
                <span className="font-semibold text-[var(--tb-ink)]">
                  최대 5페이지까지 업로드할 수 있습니다.
                </span>
              </p>
            </div>
            <button
              type="button"
              onClick={triggerUpload}
              disabled={status === "loading"}
              className="shrink-0 bg-[var(--tb-green)] px-7 py-3.5 text-base font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
            >
              {status === "loading" ? "분석 중... (최대 1분)" : "계약서 업로드하고 분석하기"}
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
              본 서비스는 참고용 정보를 제공하며 법적 효력이 없습니다. 해외 건설·인프라 계약의 1차 AI
              검토에 집중합니다.
            </p>
          </div>
          <p className="text-xs">© 2026 The Beginning · NoFear</p>
        </div>
      </footer>
    </div>
  );
}
