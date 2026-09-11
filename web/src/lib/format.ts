/** Tabular-figure number formatting (Frontend.md §3.5 — "critical for a
 * data panel" that columns of values align). */
export function fmtNum(v: number, decimals = 2): string {
  return v.toFixed(decimals);
}

export function fmtP(p: number): string {
  return p < 0.001 ? "< 0.001" : p.toFixed(4);
}

export function fmtSigned(v: number, decimals = 2): string {
  const s = v.toFixed(decimals);
  return v > 0 ? `+${s}` : s;
}
