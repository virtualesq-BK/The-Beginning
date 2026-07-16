import { useRef, useState } from "react";
import { analyzeContract } from "./lib/api";
import { ReportView } from "./components/ReportView";
import type { ContractReport } from "./types";
import founderPhoto from "./assets/founder.jpg";

type Status = "idle" | "loading" | "error";

const FEATURES = [
  {
    icon: "🌐",
    title: "해외 건설 도메인 특화",
    desc: "FIDIC, EPC, 지체상금, 하자담보 등 해외 건설 계약 실무에 특화된 150개 이상의 리스크 탐지 규칙",
  },
  {
    icon: "🔍",
    title: "SAC-RAG 기반 근거 검색",
    desc: "Summary-Augmented Chunking으로 국제 실무 기준을 검색해 모든 위험 판정에 출처를 제시",
  },
  {
    icon: "🇰🇷",
    title: "한국어 완전 지원",
    desc: "법률 용어 특화 번역과 리스크 분석을 모두 한국어로 제공, 해외 경쟁사 대비 접근성 향상",
  },
];

export default function App() {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ContractReport | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setStatus("loading");
    setError(null);
    setReport(null);
    try {
      const result = await analyzeContract(file);
      setReport(result);
      setStatus("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : "알 수 없는 오류가 발생했습니다.");
      setStatus("error");
    }
  }

  return (
    <div className="min-h-screen bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-50">
      <header className="sticky top-0 z-10 border-b border-slate-100 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-lg font-bold tracking-tight">
            The Beginning<span className="text-blue-600">.</span>
          </span>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/50 dark:text-blue-300">
            AI Legal Intelligence
          </span>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-6 pb-20 pt-24 text-center">
        <img
          src={founderPhoto}
          alt="The Beginning 대표"
          className="mx-auto mb-6 h-24 w-24 rounded-full object-cover ring-4 ring-blue-50 dark:ring-blue-950/50"
        />
        <span className="mb-5 inline-block rounded-full bg-blue-50 px-4 py-1.5 text-sm font-medium text-blue-700 dark:bg-blue-950/50 dark:text-blue-300">
          해외 법률 시장의 민주화
        </span>
        <h1 className="mb-6 text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl dark:text-white">
          해외 건설·인프라 계약,
          <br />
          <span className="text-blue-600">AI가 먼저 검토</span>합니다
        </h1>
        <p className="mx-auto mb-10 max-w-2xl text-lg leading-relaxed text-slate-500 dark:text-slate-400">
          FIDIC·EPC 계약 실무에 특화된 AI가 위험 조항을 탐지하고 국제 실무 기준을 근거로
          제시합니다. 고비용 법률 자문 없이도 1차 리스크 검토를 받아보세요.
        </p>

        <div className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-slate-50/60 p-10 shadow-sm dark:border-slate-800 dark:bg-slate-900/40">
          <input
            ref={inputRef}
            type="file"
            accept=".txt,.pdf,.docx,.doc"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
          <button
            onClick={() => inputRef.current?.click()}
            disabled={status === "loading"}
            className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-7 py-3.5 text-base font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"
          >
            {status === "loading" ? "분석 중... (최대 1분 소요)" : "계약서 업로드하고 분석하기"}
            {status !== "loading" && <span aria-hidden>→</span>}
          </button>
          <p className="mt-4 text-xs text-slate-400 dark:text-slate-500">
            지원 형식: .txt · .pdf · .docx · .doc · 최대 5페이지 (스캔 이미지 PDF는 미지원)
          </p>
        </div>

        {error && (
          <div className="mx-auto mt-8 max-w-xl rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
            {error}
          </div>
        )}
      </section>

      {!report && (
        <section className="border-t border-slate-100 bg-slate-50/60 px-6 py-20 dark:border-slate-800 dark:bg-slate-900/30">
          <div className="mx-auto grid max-w-5xl gap-8 sm:grid-cols-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950"
              >
                <span className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-xl dark:bg-blue-950/50">
                  {f.icon}
                </span>
                <h3 className="mb-2 font-semibold text-slate-900 dark:text-white">{f.title}</h3>
                <p className="text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {report && (
        <section className="border-t border-slate-100 bg-slate-50/60 px-6 py-16 dark:border-slate-800 dark:bg-slate-900/30">
          <ReportView report={report} />
        </section>
      )}

      <footer className="border-t border-slate-100 px-6 py-10 text-center text-xs text-slate-400 dark:border-slate-800 dark:text-slate-500">
        © 2026 The Beginning · NoFear. 본 서비스는 참고용 정보를 제공하며 법적 효력이 없습니다.
      </footer>
    </div>
  );
}
