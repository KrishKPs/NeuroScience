import type { ReactNode } from "react";

interface Props {
  title: string;
  children: ReactNode;
  className?: string;
}

/** "Panels separated by --hairline, not shadowed cards."
 * No border-radius-and-shadow SaaS-card look; a flat surface with a
 * hairline top rule reads as an instrument, not a widget. */
export default function Panel({ title, children, className = "" }: Props) {
  return (
    <section className={`border-t border-hairline bg-panel px-4 py-3 ${className}`}>
      <h2 className="mb-2 text-[13px] font-medium text-ink-muted">{title}</h2>
      {children}
    </section>
  );
}
