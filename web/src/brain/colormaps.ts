import type { Niivue } from "@niivue/niivue";
import { diverging } from "../lib/colorScale";

export const DIVERGING_COLORMAP_NAME = "signature_diverging";

function buildDivergingColormap() {
  const R: number[] = [];
  const G: number[] = [];
  const B: number[] = [];
  const A: number[] = [];
  const I: number[] = [];

  for (let i = 0; i <= 255; i++) {
    // diverging() takes a value in [-vmax, vmax]; feed it i in [-128, 127]
    // against vmax=128 to sample the same palette lib/colorScale.ts defines.
    const [r, g, b] = diverging(i - 128, 128);
    R.push(Math.round(r * 255));
    G.push(Math.round(g * 255));
    B.push(Math.round(b * 255));
    A.push(255);
    I.push(i);
  }

  return { R, G, B, A, I };
}

/** Registers the diverging colormap (lib/colorScale.ts —
 * the single source of truth also used by the visx panels) with a NiiVue
 * instance. Call once after the instance is created, before loading meshes
 * that reference `DIVERGING_COLORMAP_NAME`. */
export function registerColormaps(nv: Niivue): void {
  nv.addColormap(DIVERGING_COLORMAP_NAME, buildDivergingColormap());
}
