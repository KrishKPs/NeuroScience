import { useAppStore } from "../store";
import type { SignatureData } from "../data/schema";
import Panel from "../ui/Panel";
import Value from "../ui/Value";
import { fmtSigned } from "../lib/format";

interface Props {
  data: SignatureData;
}

function InlineBar({ value, domain }: { value: number; domain: [number, number] }) {
  const [lo, hi] = domain;
  const pct = Math.max(0, Math.min(100, ((value - lo) / (hi - lo)) * 100));
  return (
    <div className="mt-0.5 h-1 w-full rounded-full bg-hairline">
      <div
        className="h-1 rounded-full bg-accent"
        style={{ width: `${pct}%` }}
        aria-hidden="true"
      />
    </div>
  );
}

/** Frontend.md §6.2 — right rail, top. Region hover/pin is shared state
 * (§5.4 linked brushing): the brain, this panel, and the validation scatter
 * all read the same hoveredRegionId/pinnedRegionId. */
export default function RegionInspector({ data }: Props) {
  const disease = useAppStore((s) => s.selectedDisease);
  const hoveredId = useAppStore((s) => s.hoveredRegionId);
  const pinnedId = useAppStore((s) => s.pinnedRegionId);
  const setPinnedRegion = useAppStore((s) => s.setPinnedRegion);

  const activeId = pinnedId ?? hoveredId;
  const region = activeId ? data.diseases[disease].regions.find((r) => r.id === activeId) : null;

  return (
    <Panel title="Region">
      {!region ? (
        <p className="text-[13px] text-ink-muted">Hover a region to inspect it.</p>
      ) : (
        <div>
          <div className="mb-1 flex items-baseline justify-between">
            <span className="text-[15px] font-medium">{region.name}</span>
            <span className="font-mono text-[11px] text-ink-muted">{region.id}</span>
          </div>
          <Value label="Hemisphere" value={region.hemi} />
          <Value label="Structure" value={region.structure} />

          <div className="mt-2">
            <Value label="Signature (z)" value={fmtSigned(region.signature, 3)} />
            <InlineBar value={region.signature} domain={data.colormaps.signature.domain} />
          </div>

          {region.atrophy !== null && (
            <div className="mt-2">
              <Value label="Atrophy (d)" value={fmtSigned(region.atrophy, 3)} />
              <InlineBar value={region.atrophy} domain={data.colormaps.atrophy.domain} />
            </div>
          )}

          {pinnedId && (
            <button
              onClick={() => setPinnedRegion(null)}
              className="mt-3 text-[12px] text-accent underline decoration-dotted underline-offset-2"
            >
              pinned · clear
            </button>
          )}
        </div>
      )}
    </Panel>
  );
}
