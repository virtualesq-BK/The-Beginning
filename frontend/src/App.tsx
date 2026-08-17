import { useRef, useState } from "react";
import { analyzeContract, getStandardContracts, type StandardContractItem } from "./lib/api";
import { useEffect, useMemo } from "react";
import { StandardContractDetail } from "./components/StandardContractDetail";
import { ContractGenerator } from "./components/ContractGenerator";
import { saveContractUpload } from "./lib/contracts";
import { ReportView } from "./components/ReportView";
import type { ContractReport } from "./types";
import founderPhoto from "./assets/-OzlO6oyRj3-T6ROIXgs_Dropshot.jpg";
import heroVideo from "./assets/0812.mp4";
import { useAuth } from "./contexts/AuthContext";
import {
  compareDraftToFIDICAPI,
  deleteFIDICComparisonById,
  exportFIDICComparisonJSONReport,
  exportFIDICComparisonReport,
  getFIDICComparisonById,
  listSavedFIDICComparisons,
  saveFIDICComparisonResult,
  type FIDICComparisonResponse,
} from "./lib/fidicApi";

type Status = "idle" | "loading" | "error";

const LIFECYCLE = [
  { step: "01", title: "번역 요약", desc: "해외 계약 조항을 한국어로 정리합니다." },
  { step: "02", title: "리스크 검토", desc: "고위험 조항과 근거를 먼저 보여줍니다." },
  { step: "03", title: "협상 체크", desc: "수정·협상 포인트를 체크리스트로 만듭니다." },
  { step: "04", title: "전 세계 전문가 연결", desc: "필요하면 검수·법률 전문가로 이어집니다." },
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

const PROMO_DEADLINE = new Date("2026-09-01T00:00:00+09:00");
const isPromoActive = () => Date.now() < PROMO_DEADLINE.getTime();

const CONSTRUCTION_DASHBOARD = [
  { label: "기본 기준", value: "FIDIC Red / Yellow / Silver", detail: "패밀리별 책임 분배와 계약 형태를 비교" },
  { label: "입력 계약서", value: "사용자 초안/발주자 문안", detail: "성격·범위·법정 요건을 입력값으로 정리" },
  { label: "핵심 점검", value: "EOT / LD / DLP / Variation", detail: "공기와 비용 조정의 체계성 확인" },
  { label: "리스크 요약", value: "공사액·보증·책임한도·중재", detail: "불균형 조항을 한눈에 식별" },
];

export default function App() {
  const { user, authNotice, clearAuthNotice, openAuth, requireAuth, signOut } = useAuth();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ContractReport | null>(null);
  const [standardContracts, setStandardContracts] = useState<StandardContractItem[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string>("all");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [contractTextInput, setContractTextInput] = useState<string>("");
  const [comparisonResult, setComparisonResult] = useState<FIDICComparisonResponse | null>(null);
  const [savedComparisons, setSavedComparisons] = useState<Array<{ id: string; overall_score: number; balance: string }>>([]);
  const [historyView, setHistoryView] = useState<"list" | "detail">("list");
  const [selectedSavedComparisonId, setSelectedSavedComparisonId] = useState<string | null>(null);
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
      { key: "all", label: "전체" },
      { key: "construction", label: "해외 건설 계약" },
      ...groups.filter((group) => group !== "건설·플랜트").map((group) => ({ key: group, label: group })),
      ...groups.filter((group) => group === "건설·플랜트").map((group) => ({ key: group, label: group })),
    ];
  }, [standardContracts]);

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

  async function handleCompareContractText() {
    if (!contractTextInput.trim()) {
      setComparisonError("비교할 계약서 내용을 먼저 입력해 주세요.");
      return;
    }
    setComparisonLoading(true);
    setComparisonError(null);
    try {
      const result = await compareDraftToFIDICAPI(contractTextInput);
      setComparisonResult(result);
      const saved = await saveFIDICComparisonResult(contractTextInput);
      setSavedComparisons((prev) => [{ id: saved.comparison_id, overall_score: saved.result.overall_score, balance: saved.result.balance }, ...prev.filter((item) => item.id !== saved.comparison_id)]);
      await refreshSavedComparisons();
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : "비교 분석에 실패했습니다.");
    } finally {
      setComparisonLoading(false);
    }
  }

  const refreshSavedComparisons = async () => {
    try {
      const items = await listSavedFIDICComparisons();
      setSavedComparisons(items.slice(0, 5));
    } catch {
      setSavedComparisons([]);
    }
  };

  useEffect(() => {
    void refreshSavedComparisons();
  }, [user?.id]);

  async function handleExportComparisonReport() {
    if (!contractTextInput.trim()) {
      setComparisonError("내보낼 계약서 내용을 먼저 입력해 주세요.");
      return;
    }
    try {
      await exportFIDICComparisonReport(contractTextInput);
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : "내보내기에 실패했습니다.");
    }
  }

  async function handleExportComparisonJSONReport() {
    if (!contractTextInput.trim()) {
      setComparisonError("내보낼 계약서 내용을 먼저 입력해 주세요.");
      return;
    }
    try {
      await exportFIDICComparisonJSONReport(contractTextInput);
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : "JSON 내보내기에 실패했습니다.");
    }
  }

  async function handleLoadSavedComparison(comparisonId: string) {
    try {
      const result = await getFIDICComparisonById(comparisonId);
      setSelectedSavedComparisonId(comparisonId);
      setComparisonResult(result);
      setContractTextInput(result.contract_text ?? contractTextInput);
      setHistoryView("detail");
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : "저장된 비교 결과를 불러오지 못했습니다.");
    }
  }

  async function handleDeleteSavedComparison(comparisonId: string) {
    if (!window.confirm("이 저장 내역을 삭제하시겠습니까?")) return;

    try {
      await deleteFIDICComparisonById(comparisonId);
      if (selectedSavedComparisonId === comparisonId) {
        setSelectedSavedComparisonId(null);
        setHistoryView("list");
      }
      if (comparisonResult && comparisonResult.contract_text && comparisonId === selectedSavedComparisonId) {
        setComparisonResult(null);
      }
      await refreshSavedComparisons();
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : "저장 내역 삭제에 실패했습니다.");
    }
  }

  async function handleExportSavedComparisonReport() {
    const savedText = comparisonResult?.contract_text ?? contractTextInput;
    if (!savedText.trim()) {
      setComparisonError("내보낼 저장된 계약 내용을 찾을 수 없습니다.");
      return;
    }

    try {
      await exportFIDICComparisonReport(savedText);
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : "저장 결과 PDF 내보내기에 실패했습니다.");
    }
  }

  async function handleExportSavedComparisonJSONReport() {
    const savedText = comparisonResult?.contract_text ?? contractTextInput;
    if (!savedText.trim()) {
      setComparisonError("내보낼 저장된 계약 내용을 찾을 수 없습니다.");
      return;
    }

    try {
      await exportFIDICComparisonJSONReport(savedText);
    } catch (e) {
      setComparisonError(e instanceof Error ? e.message : "저장 결과 JSON 내보내기에 실패했습니다.");
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
              닫기 ✕
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
                🔊 소리와 함께 재생하기
              </button>
            )}
          </div>
        </div>
      )}
      <div className="sticky top-0 z-30">
        {isPromoActive() && (
          <div className="bg-[var(--tb-green-deep)] px-6 py-2.5 text-center text-sm font-semibold text-white">
            <span className="mr-2 rounded-full bg-white/15 px-2 py-0.5 text-xs font-bold uppercase tracking-[0.1em]">
              MVP 베타 출시
            </span>
            회원가입 시 8월 말까지 무료로 무제한 사용 · 지금 가입하고 바로 시작하세요
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
              onClick={() => generatorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
              className="border border-[var(--tb-line)] bg-white px-4 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
            >
              계약서 자동 생성
            </button>
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
            해외 계약 서명 전,
            <br />
            <em className="not-italic text-[var(--tb-green-soft)]">5분이면 충분합니다</em>
          </h1>
          <p className="tb-fade-up tb-fade-up-delay-2 mt-5 max-w-xl text-base leading-relaxed text-white/80 sm:text-lg">
            각종 해외 계약서(복잡한 대규모 해외 인프라 투자/건설 PF 사업 관련 FIDIC·EPC 실무 포함)를 해외 법률 전문가들이 직접 훈련시킨 AI가 번역 요약부터 주요 리스크, 협상 체크리스트까지 한 번에
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
            { label: "다음 단계", value: "전 세계 전문가 연결", note: "검수·해외 법률 자문" },
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
              <div className="mt-8 mb-8 rounded-2xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
                  FIDIC vs 사용자 계약서 대시보드
                </p>
                <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  {CONSTRUCTION_DASHBOARD.map((item) => (
                    <div key={item.label} className="rounded-xl border border-[var(--tb-line)] bg-white p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--tb-muted)]">{item.label}</p>
                      <p className="mt-2 font-display text-lg font-semibold text-[var(--tb-ink)]">{item.value}</p>
                      <p className="mt-2 text-sm leading-relaxed text-[var(--tb-muted)]">{item.detail}</p>
                    </div>
                  ))}
                </div>
              </div>

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
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            FIDIC Comparison Engine
          </p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            계약서 내용을 붙여 넣으면
            <br />
            FIDIC 기준과 자동 비교합니다
          </h2>

          <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-6 shadow-sm">
              <label className="block text-sm font-semibold text-[var(--tb-ink)]">
                계약서 초안 또는 주요 조항 붙여넣기
              </label>
              <textarea
                value={contractTextInput}
                onChange={(e) => setContractTextInput(e.target.value)}
                rows={12}
                placeholder="예: The Contractor shall complete the Works within 18 months ... Variation may be ordered by the Employer ... Liquidated Damages shall be ..."
                className="mt-3 w-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-4 py-3 text-sm leading-relaxed text-[var(--tb-ink)] focus:border-[var(--tb-green)] focus:outline-none"
              />
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleCompareContractText}
                  disabled={comparisonLoading}
                  className="bg-[var(--tb-green)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
                >
                  {comparisonLoading ? "비교 중..." : "FIDIC 비교표 생성"}
                </button>
                <button
                  type="button"
                  onClick={() => setContractTextInput("")}
                  className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                >
                  초기화
                </button>
                {comparisonResult && (
                  <>
                    <button
                      type="button"
                      onClick={handleExportComparisonReport}
                      className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                    >
                      PDF로 내보내기
                    </button>
                    <button
                      type="button"
                      onClick={handleExportComparisonJSONReport}
                      className="border border-[var(--tb-line)] px-5 py-2.5 text-sm font-semibold text-[var(--tb-ink)] transition hover:bg-[var(--tb-green-soft)]"
                    >
                      JSON으로 내보내기
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
                    FIDIC 매칭 점수
                  </p>
                  <div className="mt-4 flex items-end gap-3">
                    <span className="font-display text-5xl font-semibold text-[var(--tb-ink)]">
                      {comparisonResult.overall_score}
                    </span>
                    <span className="pb-2 text-sm text-[var(--tb-muted)]">/ 100</span>
                  </div>
                  <div className="mt-4 rounded-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-2 text-sm font-semibold text-[var(--tb-ink)]">
                    계약 편향: {comparisonResult.balance}
                  </div>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-3 text-sm">
                      <div className="text-[var(--tb-muted)]">발주자 편향 점수</div>
                      <div className="mt-1 text-lg font-semibold text-[var(--tb-ink)]">{comparisonResult.bias_scores.employer}</div>
                    </div>
                    <div className="rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-3 text-sm">
                      <div className="text-[var(--tb-muted)]">시공사 편향 점수</div>
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
                  계약서 내용을 입력하면 FIDIC 기준에 대한 종합 점수와 핵심 비교 항목이 표시됩니다.
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
                        {issue.status === "good" ? "양호" : issue.status === "watch" ? "주의" : "위험"}
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
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--tb-green)]">근거 문장</p>
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

          <div className="mt-8 rounded-2xl border border-[var(--tb-line)] bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--tb-green)]">내 저장 내역</p>
              <button
                type="button"
                onClick={() => setHistoryView((current) => (current === "list" ? "detail" : "list"))}
                className="text-xs font-semibold text-[var(--tb-green)] underline-offset-2 hover:underline"
              >
                {historyView === "list" ? "상세 보기" : "목록 보기"}
              </button>
            </div>

            {historyView === "list" && savedComparisons.length > 0 && (
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {savedComparisons.map((item) => (
                  <div key={item.id} className="rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-3">
                    <button
                      type="button"
                      onClick={() => void handleLoadSavedComparison(item.id)}
                      className="block w-full text-left"
                    >
                      <div className="text-xs text-[var(--tb-muted)]">{item.id.slice(0, 8)}</div>
                      <div className="mt-2 text-lg font-semibold text-[var(--tb-ink)]">{item.overall_score}</div>
                      <div className="text-sm text-[var(--tb-muted)]">{item.balance}</div>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {historyView === "detail" && comparisonResult && (
              <div className="mt-4 rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="text-xs text-[var(--tb-muted)]">{selectedSavedComparisonId?.slice(0, 8)}</div>
                    <div className="mt-1 text-xl font-semibold text-[var(--tb-ink)]">점수 {comparisonResult.overall_score} / 100</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={handleExportSavedComparisonReport}
                      className="border border-[var(--tb-line)] bg-white px-3 py-2 text-xs font-semibold text-[var(--tb-ink)] hover:bg-[var(--tb-green-soft)]"
                    >
                      PDF 재다운로드
                    </button>
                    <button
                      type="button"
                      onClick={handleExportSavedComparisonJSONReport}
                      className="border border-[var(--tb-line)] bg-white px-3 py-2 text-xs font-semibold text-[var(--tb-ink)] hover:bg-[var(--tb-green-soft)]"
                    >
                      JSON 재다운로드
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteSavedComparison(selectedSavedComparisonId ?? "")}
                      className="border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                    >
                      삭제
                    </button>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-[var(--tb-muted)]">{comparisonResult.summary}</p>
              </div>
            )}

            {savedComparisons.length === 0 && (
              <div className="mt-4 rounded-xl border border-dashed border-[var(--tb-line)] bg-[var(--tb-sand)] p-4 text-sm text-[var(--tb-muted)]">
                {user
                  ? "저장된 비교 내역이 아직 없습니다. 계약서를 비교해 첫 기록을 남겨보세요."
                  : "로그인하면 비교 결과를 개인별 저장 목록에서 다시 조회할 수 있습니다."}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Contract generator */}
      <section ref={generatorRef} className="border-t border-[var(--tb-line)] bg-[var(--tb-sand)] px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
            Contract Generator
          </p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl font-semibold tracking-tight text-[var(--tb-ink)] sm:text-4xl">
            인하우스 변호사 없이도,
            <br />
            몇 가지 질문으로 영문 계약서 초안을
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-[var(--tb-muted)]">
            해외 진출을 준비하는 중소기업·스타트업을 위한 서비스입니다. 계약 유형을 고르고 거래 조건을
            입력하면, 표준계약서 자료를 근거로 영문 초안과 조항별 한국어 해설을 함께 만들어 드립니다.
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
              본 서비스는 참고용 정보를 제공하며 법적 효력이 없습니다.
            </p>
          </div>
          <p className="text-xs">© 2026 The Beginning · NoFear</p>
        </div>
      </footer>
    </div>
  );
}
