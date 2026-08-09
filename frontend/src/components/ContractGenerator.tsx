import { useEffect, useMemo, useState } from "react";
import {
  generateContract,
  getContractTemplates,
  type ContractTemplate,
  type GeneratedContract,
} from "../lib/api";

type Status = "idle" | "loading" | "error";

type Props = {
  requireAuth: (message: string) => boolean;
};

function assembleDownloadText(result: GeneratedContract): string {
  const parts = [
    result.title,
    "",
    result.recitals,
    "",
    ...result.clauses.map(
      (clause) => `${clause.clause_no}. ${clause.heading}\n${clause.body_en}`,
    ),
    "",
    result.signature_block,
    "",
    `---\n${result.disclaimer}`,
  ];
  return parts.join("\n\n");
}

export function ContractGenerator({ requireAuth }: Props) {
  const [templates, setTemplates] = useState<ContractTemplate[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GeneratedContract | null>(null);

  useEffect(() => {
    void getContractTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, []);

  const selectedTemplate = useMemo(
    () => templates.find((t) => t.id === selectedId) ?? null,
    [templates, selectedId],
  );

  function selectTemplate(id: string) {
    setSelectedId(id);
    setAnswers({});
    setResult(null);
    setError(null);
  }

  function setField(key: string, value: string) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }

  const missingRequired = useMemo(() => {
    if (!selectedTemplate) return [];
    return selectedTemplate.fields
      .filter((f) => f.required && !(answers[f.key] ?? "").trim())
      .map((f) => f.label);
  }, [selectedTemplate, answers]);

  async function handleGenerate() {
    if (!selectedTemplate) return;
    if (!requireAuth("계약서 초안을 생성하려면 로그인과 회원 정보 입력이 필요합니다.")) {
      return;
    }
    if (missingRequired.length > 0) {
      setError(`다음 항목을 입력해 주세요: ${missingRequired.join(", ")}`);
      return;
    }

    setStatus("loading");
    setError(null);
    setResult(null);
    try {
      const draft = await generateContract(selectedTemplate.id, answers);
      setResult(draft);
      setStatus("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : "알 수 없는 오류가 발생했습니다.");
      setStatus("error");
    }
  }

  function handleDownload() {
    if (!result) return;
    const text = assembleDownloadText(result);
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.template_id}-draft.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="mt-8">
      {!selectedTemplate ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {templates.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => selectTemplate(t.id)}
              className="flex h-full flex-col border border-[var(--tb-line)] bg-[var(--tb-sand)] p-6 text-left transition hover:-translate-y-0.5 hover:border-[var(--tb-green)]"
            >
              <span className="w-fit rounded-full bg-[var(--tb-green-soft)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--tb-green-deep)]">
                {t.family}
              </span>
              <h3 className="mt-4 font-display text-xl font-semibold text-[var(--tb-ink)]">
                {t.title}
              </h3>
              <p className="mt-3 flex-1 text-sm leading-relaxed text-[var(--tb-muted)]">
                {t.description}
              </p>
              <span className="mt-4 text-sm font-semibold text-[var(--tb-green-deep)]">
                질문에 답하고 초안 만들기 →
              </span>
            </button>
          ))}
          {templates.length === 0 && (
            <p className="text-sm text-[var(--tb-muted)]">템플릿 목록을 불러오는 중입니다...</p>
          )}
        </div>
      ) : (
        <div className="border border-[var(--tb-line)] bg-white p-6 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">
                {selectedTemplate.family}
              </p>
              <h3 className="mt-1 font-display text-2xl font-semibold text-[var(--tb-ink)]">
                {selectedTemplate.title}
              </h3>
            </div>
            <button
              type="button"
              onClick={() => selectTemplate("")}
              className="text-sm font-semibold text-[var(--tb-muted)] hover:text-[var(--tb-ink)]"
            >
              ← 템플릿 다시 선택
            </button>
          </div>

          {!result && (
            <div className="mt-8 grid gap-5 sm:grid-cols-2">
              {selectedTemplate.fields.map((field) => (
                <div
                  key={field.key}
                  className={field.type === "textarea" ? "sm:col-span-2" : undefined}
                >
                  <label className="block text-sm font-semibold text-[var(--tb-ink)]">
                    {field.label}
                    {field.required && <span className="text-rose-500"> *</span>}
                  </label>
                  {field.type === "textarea" ? (
                    <textarea
                      value={answers[field.key] ?? ""}
                      onChange={(e) => setField(field.key, e.target.value)}
                      placeholder={field.placeholder}
                      rows={3}
                      className="mt-2 w-full border border-[var(--tb-line)] px-3 py-2 text-sm text-[var(--tb-ink)] focus:border-[var(--tb-green)] focus:outline-none"
                    />
                  ) : field.type === "select" ? (
                    <select
                      value={answers[field.key] ?? ""}
                      onChange={(e) => setField(field.key, e.target.value)}
                      className="mt-2 w-full border border-[var(--tb-line)] bg-white px-3 py-2 text-sm text-[var(--tb-ink)] focus:border-[var(--tb-green)] focus:outline-none"
                    >
                      <option value="">선택하세요</option>
                      {field.options?.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={field.type === "date" ? "date" : field.type === "number" ? "number" : "text"}
                      value={answers[field.key] ?? ""}
                      onChange={(e) => setField(field.key, e.target.value)}
                      placeholder={field.placeholder}
                      className="mt-2 w-full border border-[var(--tb-line)] px-3 py-2 text-sm text-[var(--tb-ink)] focus:border-[var(--tb-green)] focus:outline-none"
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mt-6 border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          {!result && (
            <button
              type="button"
              onClick={handleGenerate}
              disabled={status === "loading"}
              className="mt-8 bg-[var(--tb-green)] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-50"
            >
              {status === "loading" ? "초안 생성 중... (최대 1분)" : "영문 계약서 초안 생성하기"}
            </button>
          )}

          {result && (
            <div className="mt-8">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--tb-line)] pb-4">
                <h4 className="font-display text-xl font-semibold text-[var(--tb-ink)]">
                  {result.title}
                </h4>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleDownload}
                    className="border border-[var(--tb-line)] px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] hover:bg-[var(--tb-green-soft)]"
                  >
                    .txt로 다운로드
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setResult(null);
                    }}
                    className="border border-[var(--tb-line)] px-4 py-2 text-sm font-semibold text-[var(--tb-ink)] hover:bg-[var(--tb-green-soft)]"
                  >
                    조건 다시 입력
                  </button>
                </div>
              </div>

              <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-[var(--tb-ink)]">
                {result.recitals}
              </p>

              <div className="mt-6 space-y-6">
                {result.clauses.map((clause) => (
                  <div key={clause.clause_no} className="border border-[var(--tb-line)] p-5">
                    <h5 className="font-display text-lg font-semibold text-[var(--tb-ink)]">
                      {clause.clause_no}. {clause.heading}
                    </h5>
                    <p className="mt-3 whitespace-pre-wrap font-mono text-sm leading-relaxed text-[var(--tb-ink)]">
                      {clause.body_en}
                    </p>
                    <div className="mt-4 border-l-2 border-[var(--tb-green)] bg-[var(--tb-green-soft)] p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--tb-green-deep)]">
                        조항 해설
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-[var(--tb-green-deep)]">
                        {clause.commentary_kr}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <p className="mt-6 whitespace-pre-wrap text-sm leading-relaxed text-[var(--tb-ink)]">
                {result.signature_block}
              </p>

              <p className="mt-8 border-t border-[var(--tb-line)] pt-4 text-xs leading-relaxed text-[var(--tb-muted)]">
                {result.disclaimer}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
