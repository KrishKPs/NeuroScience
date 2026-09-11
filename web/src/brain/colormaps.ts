import type { Niivue } from "@niivue/niivue";

// Frontend.md §3.4 — a hand-defined diverging colormap matching the exact
// stops (not a built-in NiiVue name, so the palette matches the spec
// precisely rather than approximating a Crameri vik/cork with whatever
// NiiVue ships under a similar name).
const DIVERGING_STOPS = [
  { i: 0, hex: "#2A788E" }, // negative
  { i: 128, hex: "#EDE7E1" }, // neutral
  { i: 255, hex: "#B23A5B" }, // positive
];

export const DIVERGING_COLORMAP_NAME = "signature_diverging";

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function buildDivergingColormap() {
  const R: number[] = [];
  const G: number[] = [];
  const B: number[] = [];
  const A: number[] = [];
  const I: number[] = [];

  for (let i = 0; i <= 255; i++) {
    let lo = DIVERGING_STOPS[0];
    let hi = DIVERGING_STOPS[DIVERGING_STOPS.length - 1];
    for (let s = 0; s < DIVERGING_STOPS.length - 1; s++) {
      if (i >= DIVERGING_STOPS[s].i && i <= DIVERGING_STOPS[s + 1].i) {
        lo = DIVERGING_STOPS[s];
        hi = DIVERGING_STOPS[s + 1];
        break;
      }
    }
    const span = hi.i - lo.i || 1;
    const t = (i - lo.i) / span;
    const [lr, lg, lb] = hexToRgb(lo.hex);
    const [hr, hg, hb] = hexToRgb(hi.hex);
    R.push(Math.round(lerp(lr, hr, t)));
    G.push(Math.round(lerp(lg, hg, t)));
    B.push(Math.round(lerp(lb, hb, t)));
    A.push(255);
    I.push(i);
  }

  return { R, G, B, A, I };
}

/** Registers the Frontend.md §3.4 diverging colormap with a NiiVue instance.
 * Call once after the instance is created, before loading meshes that
 * reference `DIVERGING_COLORMAP_NAME`. */
export function registerColormaps(nv: Niivue): void {
  nv.addColormap(DIVERGING_COLORMAP_NAME, buildDivergingColormap());
}
