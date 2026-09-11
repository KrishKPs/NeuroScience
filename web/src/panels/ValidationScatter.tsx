import { scaleLinear } from "@visx/scale";
import { Group } from "@visx/group";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { useAppStore } from "../store";
import type { SignatureData } from "../data/schema";
import Panel from "../ui/Panel";

interface Props {
  data: SignatureData;
}

const WIDTH = 640;
const HEIGHT = 200;
const MARGIN = { top: 10, right: 20, bottom: 32, left: 48 };

/** Frontend.md §6.6 — bottom, full-width, linked. The quantitative proof
 * the brain colors aren't just pretty. AD has no continuous ENIGMA ground
 * truth (CLAUDE.md §16) — every region.atrophy is null for it, so this
 * shows an honest message instead of an empty or fabricated plot. */
export default function ValidationScatter({ data }: Props) {
  const disease = useAppStore((s) => s.selectedDisease);
  const hoveredId = useAppStore((s) => s.hoveredRegionId);
  const pinnedId = useAppStore((s) => s.pinnedRegionId);
  const setHoveredRegion = useAppStore((s) => s.setHoveredRegion);
  const setPinnedRegion = useAppStore((s) => s.setPinnedRegion);

  const regions = data.diseases[disease].regions.filter((r) => r.atrophy !== null);

  if (regions.length === 0) {
    return (
      <Panel title="Validation scatter">
        <p className="text-[13px] italic text-ink-muted">
          No continuous ENIGMA ground truth for {data.diseases[disease].label} — validated
          against a fallback ROI list instead (see the Validation panel). Not significant under
          either null.
        </p>
      </Panel>
    );
  }

  const xVals = regions.map((r) => r.signature);
  const yVals = regions.map((r) => r.atrophy as number);
  const innerW = WIDTH - MARGIN.left - MARGIN.right;
  const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

  const xScale = scaleLinear({ domain: [Math.min(...xVals), Math.max(...xVals)], range: [0, innerW], nice: true });
  const yScale = scaleLinear({ domain: [Math.min(...yVals), Math.max(...yVals)], range: [innerH, 0], nice: true });

  // Simple least-squares fit line.
  const n = regions.length;
  const meanX = xVals.reduce((a, b) => a + b, 0) / n;
  const meanY = yVals.reduce((a, b) => a + b, 0) / n;
  const slope =
    xVals.reduce((sum, x, i) => sum + (x - meanX) * (yVals[i] - meanY), 0) /
    (xVals.reduce((sum, x) => sum + (x - meanX) ** 2, 0) || 1);
  const intercept = meanY - slope * meanX;

  const activeId = pinnedId ?? hoveredId;

  return (
    <Panel title="Validation scatter">
      <svg width={WIDTH} height={HEIGHT} role="img" aria-label={`Signature vs. atrophy scatter for ${data.diseases[disease].label}`}>
        <Group left={MARGIN.left} top={MARGIN.top}>
          <line
            x1={xScale(xScale.domain()[0])}
            y1={yScale(slope * xScale.domain()[0] + intercept)}
            x2={xScale(xScale.domain()[1])}
            y2={yScale(slope * xScale.domain()[1] + intercept)}
            stroke="var(--color-accent)"
            strokeWidth={1.5}
            opacity={0.6}
          />
          {regions.map((r) => {
            const isActive = r.id === activeId;
            return (
              <circle
                key={r.id}
                cx={xScale(r.signature)}
                cy={yScale(r.atrophy as number)}
                r={isActive ? 5 : 3}
                fill={isActive ? "var(--color-accent)" : "var(--color-ink-muted)"}
                opacity={isActive ? 1 : 0.7}
                onMouseEnter={() => setHoveredRegion(r.id)}
                onMouseLeave={() => setHoveredRegion(null)}
                onClick={() => setPinnedRegion(r.id === pinnedId ? null : r.id)}
                style={{ cursor: "pointer" }}
              >
                <title>{`${r.name}: signature ${r.signature.toFixed(3)}, atrophy ${(r.atrophy as number).toFixed(3)}`}</title>
              </circle>
            );
          })}
          <AxisLeft scale={yScale} stroke="var(--color-hairline)" tickStroke="var(--color-hairline)" tickLabelProps={() => ({ fill: "var(--color-ink-muted)", fontSize: 10 })} label="atrophy (Cohen's d)" labelProps={{ fill: "var(--color-ink-muted)", fontSize: 11 }} />
          <AxisBottom top={innerH} scale={xScale} stroke="var(--color-hairline)" tickStroke="var(--color-hairline)" tickLabelProps={() => ({ fill: "var(--color-ink-muted)", fontSize: 10 })} label="signature (mean z)" labelProps={{ fill: "var(--color-ink-muted)", fontSize: 11, textAnchor: "middle" }} />
        </Group>
      </svg>
    </Panel>
  );
}
