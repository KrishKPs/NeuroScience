import type { ReactNode } from "react";

interface Props {
  label: ReactNode;
  value: ReactNode;
}

/** Label left, value right-aligned with tabular figures — Frontend.md §3.6:
 * "numeric values right-aligned within their rows so they form a clean
 * column." */
export default function Value({ label, value }: Props) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-0.5 text-[13px]">
      <span className="text-ink-muted">{label}</span>
      <span className="text-right tabular-nums">{value}</span>
    </div>
  );
}
