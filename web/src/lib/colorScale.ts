// The exact diverging stops — the single source of truth,
// used by both brain/colormaps.ts (registered with NiiVue for the 3D
// overlay) and the visx panels (specificity matrix, validation scatter), so
// the 3D view and the 2D charts never drift into different palettes.
export const DIVERGING_STOPS: { t: number; hex: string }[] = [
  { t: 0, hex: "#2A788E" }, // negative
  { t: 0.5, hex: "#EDE7E1" }, // neutral
  { t: 1, hex: "#B23A5B" }, // positive
];

function hexToRgb01(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** value in [-vmax, vmax] -> [r, g, b] each in [0, 1]. */
export function diverging(value: number, vmax: number): [number, number, number] {
  const t = vmax === 0 ? 0.5 : (value / vmax + 1) / 2;
  const clamped = Math.max(0, Math.min(1, t));

  let lo = DIVERGING_STOPS[0];
  let hi = DIVERGING_STOPS[DIVERGING_STOPS.length - 1];
  for (let i = 0; i < DIVERGING_STOPS.length - 1; i++) {
    if (clamped >= DIVERGING_STOPS[i].t && clamped <= DIVERGING_STOPS[i + 1].t) {
      lo = DIVERGING_STOPS[i];
      hi = DIVERGING_STOPS[i + 1];
      break;
    }
  }
  const span = hi.t - lo.t || 1;
  const localT = (clamped - lo.t) / span;
  const [lr, lg, lb] = hexToRgb01(lo.hex);
  const [hr, hg, hb] = hexToRgb01(hi.hex);
  return [lerp(lr, hr, localT), lerp(lg, hg, localT), lerp(lb, hb, localT)];
}

export function toCssHex([r, g, b]: [number, number, number]): string {
  const toHex = (v: number) => Math.round(v * 255).toString(16).padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}
