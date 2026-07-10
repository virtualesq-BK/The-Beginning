const ICON_MAP: Record<string, string> = {
  지체상금: "⏱",
  면책: "🛡",
  중재: "⚖",
  하자담보: "🔧",
  "변경명령(Change Order)": "🔄",
  손해배상: "💰",
  불가항력: "🌪",
  계약해지: "✂",
  지급조건: "💳",
  이행보증: "📜",
  준거법: "🏛",
  분쟁해결: "🤝",
  보험: "☂",
  지식재산권: "💡",
  기타: "📄",
};

export function ClauseTypeIcon({ clauseType }: { clauseType: string }) {
  return (
    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-lg dark:bg-blue-950/50">
      {ICON_MAP[clauseType] ?? "📄"}
    </span>
  );
}
