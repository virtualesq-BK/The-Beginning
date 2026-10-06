import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ContractReport } from "../types";
import { sendContractChat, type ChatMessage } from "../lib/api";

function buildClausesContext(report: ContractReport): string {
  const lines: string[] = [];
  for (const clause of report.clauses) {
    const num = clause.clause_number ? `[${clause.clause_number}] ` : "";
    lines.push(
      `${num}${clause.title} (위험도: ${clause.risk.risk_score}/5)\n` +
        `  - 사유: ${clause.risk.risk_reason}\n` +
        `  - 권장사항: ${clause.risk.recommendation}` +
        (clause.risk.negotiation_point ? `\n  - 협상 포인트: ${clause.risk.negotiation_point}` : ""),
    );
  }
  return lines.join("\n\n");
}

export function ContractChat({ report }: { report: ContractReport }) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const clausesContext = buildClausesContext(report);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend() {
    const userMsg = input.trim();
    if (!userMsg || loading) return;

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: userMsg }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const reply = await sendContractChat(report.document_summary, clausesContext, nextMessages);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("contractChat.genericError"));
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  const SUGGESTED = [
    t("contractChat.suggest1"),
    t("contractChat.suggest2"),
    t("contractChat.suggest3"),
  ];

  return (
    <section className="rounded-2xl border border-[var(--tb-green)]/30 bg-white p-6 dark:border-slate-700 dark:bg-slate-950">
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-[var(--tb-green)]">
        {t("contractChat.heading")}
      </h2>
      <p className="mb-5 text-sm text-slate-500 dark:text-slate-400">
        {t("contractChat.subheading")}
      </p>

      {/* Suggested questions — only shown when no messages yet */}
      {messages.length === 0 && (
        <div className="mb-5 flex flex-wrap gap-2">
          {SUGGESTED.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => setInput(q)}
              className="rounded-full border border-[var(--tb-line)] bg-[var(--tb-sand)] px-3 py-1.5 text-xs font-medium text-[var(--tb-ink)] transition hover:border-[var(--tb-green)] hover:text-[var(--tb-green-deep)] dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Chat messages */}
      {messages.length > 0 && (
        <div className="mb-4 max-h-[480px] space-y-4 overflow-y-auto rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] p-4 dark:border-slate-800 dark:bg-slate-900">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-[var(--tb-green)] text-white"
                    : "border border-[var(--tb-line)] bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="rounded-2xl border border-[var(--tb-line)] bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-950">
                <span className="inline-flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--tb-green)] [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--tb-green)] [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--tb-green)] [animation-delay:300ms]" />
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {error && (
        <div className="mb-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
          {error}
        </div>
      )}

      {/* Input area */}
      <div className="flex gap-3">
        <textarea
          ref={textareaRef}
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("contractChat.placeholder")}
          disabled={loading}
          className="flex-1 resize-none rounded-xl border border-[var(--tb-line)] bg-[var(--tb-sand)] px-4 py-3 text-sm text-[var(--tb-ink)] placeholder-slate-400 focus:border-[var(--tb-green)] focus:outline-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
        />
        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={loading || !input.trim()}
          className="self-end rounded-xl bg-[var(--tb-green)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)] disabled:opacity-40"
        >
          {loading ? "…" : t("contractChat.send")}
        </button>
      </div>
      <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
        {t("contractChat.hint")}
      </p>
    </section>
  );
}
