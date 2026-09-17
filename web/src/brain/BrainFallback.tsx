import type { SignatureData } from "../data/schema";
import { useAppStore } from "../store";

interface Props {
  data: SignatureData;
  reason: string;
}

/** No-WebGL fallback: "a designed 2D experience, not a
 * banner." Shows the selected disease's pre-rendered lateral+superior
 * schematic (src/figures.py::plot_2d_fallback_schematic — same colormap,
 * same data). Region-level hover linking isn't available here: a static
 * PNG can't support pixel-accurate hit-testing without shipping a separate
 * per-pixel region map for the fallback images specifically, which wasn't
 * built for v1 — an honest simplification, not a silent gap (the message
 * below says so).
 */
export default function BrainFallback({ data, reason }: Props) {
  const disease = useAppStore((s) => s.selectedDisease);
  const src = data.assets.fallback_2d[disease];

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
      <img
        src={src}
        alt={`2D lateral and superior brain schematic for ${data.diseases[disease].label}`}
        className="max-h-[70%] max-w-full"
      />
      <p className="max-w-md text-sm text-ink-muted">
        WebGL isn&apos;t available in this browser — showing 2D brain views. The data and all
        panels are fully interactive; region hover-to-inspect isn&apos;t available on this static
        view.
      </p>
      <p className="text-xs text-ink-muted opacity-60">{reason}</p>
    </div>
  );
}
