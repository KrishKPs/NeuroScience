// Hand-rolled diverging colormap mirroring matplotlib's RdBu_r (blue = low/
// negative score, white = zero, red = high/positive) — the same colormap
// used in the static figures (src/figures.py), so the interactive viewer and
// the "proof of rigor" static figures read consistently. See CLAUDE.md §17
// for why this isn't a JS colormap library: three stops and linear
// interpolation is the entire implementation, not worth a dependency.

const STOPS = [
  { t: 0.0, r: 0x05, g: 0x30, b: 0x61 }, // dark blue
  { t: 0.5, r: 0xf7, g: 0xf7, b: 0xf7 }, // white
  { t: 1.0, r: 0x67, g: 0x00, b: 0x1f }, // dark red
];

function lerp(a, b, t) {
  return a + (b - a) * t;
}

/** value in [-vmax, vmax] -> [r, g, b] each in [0, 1]. */
export function diverging(value, vmax) {
  const t = vmax === 0 ? 0.5 : (value / vmax + 1) / 2;
  const clamped = Math.max(0, Math.min(1, t));

  let lo = STOPS[0];
  let hi = STOPS[STOPS.length - 1];
  for (let i = 0; i < STOPS.length - 1; i++) {
    if (clamped >= STOPS[i].t && clamped <= STOPS[i + 1].t) {
      lo = STOPS[i];
      hi = STOPS[i + 1];
      break;
    }
  }
  const span = hi.t - lo.t || 1;
  const localT = (clamped - lo.t) / span;

  return [
    lerp(lo.r, hi.r, localT) / 255,
    lerp(lo.g, hi.g, localT) / 255,
    lerp(lo.b, hi.b, localT) / 255,
  ];
}

export function toCssHex([r, g, b]) {
  const toHex = (v) => Math.round(v * 255).toString(16).padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}
