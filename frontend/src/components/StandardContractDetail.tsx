import { useEffect, useMemo, useState } from "react";
import type { StandardContractItem } from "../lib/api";

type Props = {
  itemId: string;
  onBack: () => void;
};

export function StandardContractDetail({ itemId, onBack }: Props) {
  const [item, setItem] = useState<StandardContractItem | null>(null);

  useEffect(() => {
    fetch(`/api/v1/standard-contracts`)
      .then((res) => res.json())
      .then((body) => {
        const found = (body.items ?? []).find((entry: StandardContractItem) => entry.id === itemId);
        setItem(found ?? null);
      })
      .catch(() => setItem(null));
  }, [itemId]);

  const content = useMemo(() => {
    if (!item) return null;
    return (
      <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--tb-green)]">{item.category}</p>
        <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight text-[var(--tb-ink)]">
          {item.title}
        </h2>
        <p className="mt-4 text-base leading-relaxed text-[var(--tb-muted)]">{item.description}</p>
        <p className="mt-4 text-base leading-relaxed text-[var(--tb-ink)]">{item.detail}</p>
        <div className="mt-6 flex flex-wrap gap-2">
          {item.tags.map((tag) => (
            <span key={tag} className="rounded-full border border-[var(--tb-line)] px-2.5 py-1 text-xs text-[var(--tb-muted)]">
              {tag}
            </span>
          ))}
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-[var(--tb-green)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--tb-green-deep)]"
          >
            원본 자료 열기
          </a>
          <button
            type="button"
            onClick={onBack}
            className="rounded-full border border-[var(--tb-line)] px-4 py-2 text-sm font-semibold text-[var(--tb-ink)]"
          >
            목록으로 돌아가기
          </button>
        </div>
      </div>
    );
  }, [item, onBack]);

  if (!item) {
    return <div className="rounded-2xl border border-[var(--tb-line)] bg-white p-8 text-sm text-[var(--tb-muted)]">자료를 불러오는 중입니다...</div>;
  }

  return content;
}
