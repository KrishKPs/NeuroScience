import { useAppStore, type OverlayMode, type ViewPreset, type Hemisphere, type Surface } from "../store";
import type { SignatureData } from "../data/schema";
import Panel from "../ui/Panel";

const OVERLAY_LABELS: Record<OverlayMode, string> = { signature: "Signature", atrophy: "Atrophy", diff: "Difference" };
const VIEW_LABELS: Record<ViewPreset, string> = {
  lateralL: "Lateral L", lateralR: "Lateral R", superior: "Superior", anterior: "Anterior", medial: "Medial",
};
const HEMI_LABELS: Record<Hemisphere, string> = { both: "Both", left: "Left", right: "Right" };

function SegButton<T extends string>({ value, active, onClick, children }: { value: T; active: boolean; onClick: (v: T) => void; children: React.ReactNode }) {
  return (
    <button
      onClick={() => onClick(value)}
      aria-pressed={active}
      className={`rounded px-2 py-1 text-[12px] ${active ? "bg-accent text-white" : "text-ink-muted hover:text-ink"}`}
    >
      {children}
    </button>
  );
}

/** Frontend.md §5.3/§6 left rail — overlay/opacity/hemisphere/surface/view
 * controls. AD has no atrophy/diff overlay (no continuous ENIGMA ground
 * truth), so those two options are disabled rather than hidden when AD is
 * selected — a visible, explained constraint beats a control that silently
 * does nothing.
 */
export default function Controls({ data }: { data: SignatureData }) {
  const disease = useAppStore((s) => s.selectedDisease);
  const overlayMode = useAppStore((s) => s.overlayMode);
  const setOverlayMode = useAppStore((s) => s.setOverlayMode);
  const opacity = useAppStore((s) => s.opacity);
  const setOpacity = useAppStore((s) => s.setOpacity);
  const hemisphere = useAppStore((s) => s.hemisphere);
  const setHemisphere = useAppStore((s) => s.setHemisphere);
  const surface = useAppStore((s) => s.surface);
  const setSurface = useAppStore((s) => s.setSurface);
  const viewPreset = useAppStore((s) => s.viewPreset);
  const setViewPreset = useAppStore((s) => s.setViewPreset);

  const hasGroundTruth = data.assets.overlays[disease].atrophy !== null;

  return (
    <Panel title="Controls" className="border-t-0">
      <div className="mb-3">
        <p className="mb-1 text-[11px] text-ink-muted">Overlay</p>
        <div className="flex flex-wrap gap-1">
          {(Object.keys(OVERLAY_LABELS) as OverlayMode[]).map((m) => (
            <SegButton
              key={m}
              value={m}
              active={overlayMode === m}
              onClick={(v) => hasGroundTruth || v === "signature" ? setOverlayMode(v) : undefined}
            >
              <span className={!hasGroundTruth && m !== "signature" ? "opacity-40" : ""}>{OVERLAY_LABELS[m]}</span>
            </SegButton>
          ))}
        </div>
        {!hasGroundTruth && (
          <p className="mt-1 text-[11px] text-ink-muted opacity-70">
            No continuous ground truth for {data.diseases[disease].label} — signature only.
          </p>
        )}
      </div>

      <div className="mb-3">
        <label htmlFor="opacity-slider" className="mb-1 block text-[11px] text-ink-muted">
          Opacity
        </label>
        <input
          id="opacity-slider"
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={opacity}
          onChange={(e) => setOpacity(Number(e.target.value))}
          className="w-full accent-[var(--color-accent)]"
        />
      </div>

      <div className="mb-3">
        <p className="mb-1 text-[11px] text-ink-muted">Hemisphere</p>
        <div className="flex gap-1">
          {(Object.keys(HEMI_LABELS) as Hemisphere[]).map((h) => (
            <SegButton key={h} value={h} active={hemisphere === h} onClick={setHemisphere}>
              {HEMI_LABELS[h]}
            </SegButton>
          ))}
        </div>
      </div>

      <div className="mb-3">
        <p className="mb-1 text-[11px] text-ink-muted">Surface</p>
        <div className="flex gap-1">
          <SegButton value={"pial" as Surface} active={surface === "pial"} onClick={setSurface}>
            Pial
          </SegButton>
          <SegButton value={"inflated" as Surface} active={surface === "inflated"} onClick={setSurface}>
            Inflated
          </SegButton>
        </div>
      </div>

      <div>
        <p className="mb-1 text-[11px] text-ink-muted">View</p>
        <div className="flex flex-wrap gap-1">
          {(Object.keys(VIEW_LABELS) as ViewPreset[]).map((v) => (
            <SegButton key={v} value={v} active={viewPreset === v} onClick={setViewPreset}>
              {VIEW_LABELS[v]}
            </SegButton>
          ))}
        </div>
      </div>
    </Panel>
  );
}
