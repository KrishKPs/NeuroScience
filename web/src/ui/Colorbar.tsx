import { diverging, toCssHex } from "../lib/colorScale";

interface Props {
  domain: [number, number];
  units: string;
}

/** "Bottom-left colorbar with ticks + units, always
 * visible." Color without a legend is decoration. Positioned over
 * the brain canvas, not competing with the right-rail panels. */
export default function Colorbar({ domain, units }: Props) {
  const [lo, hi] = domain;
  const stops = Array.from({ length: 11 }, (_, i) => {
    const t = i / 10;
    const value = lo + t * (hi - lo);
    const [r, g, b] = diverging(value, Math.max(Math.abs(lo), Math.abs(hi)));
    return { pct: t * 100, color: toCssHex([r, g, b]) };
  });
  const gradient = `linear-gradient(to right, ${stops.map((s) => `${s.color} ${s.pct}%`).join(", ")})`;

  return (
    <div className="absolute bottom-4 left-4 w-48 rounded bg-panel/90 px-3 py-2 text-ink backdrop-blur-sm">
      <div className="h-2 w-full rounded-full" style={{ background: gradient }} aria-hidden="true" />
      <div className="mt-1 flex justify-between text-[10px] text-ink-muted tabular-nums">
        <span>{lo.toFixed(2)}</span>
        <span>0</span>
        <span>{hi.toFixed(2)}</span>
      </div>
      <div className="mt-0.5 text-[10px] text-ink-muted">{units}</div>
    </div>
  );
}
