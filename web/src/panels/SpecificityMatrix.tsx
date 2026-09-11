import { useState } from "react";
import { Group } from "@visx/group";
import { useAppStore } from "../store";
import type { SignatureData } from "../data/schema";
import Panel from "../ui/Panel";
import { diverging, toCssHex } from "../lib/colorScale";

interface Props {
  data: SignatureData;
}

const CELL = 44;
const LABEL_W = 46;

/** Frontend.md §6.4 — 3x3 heatmap, visx. "The diagonal being strongest is
 * the headline" — diagonal cells get a subtle ring. Hovering a cell
 * highlights its row/col; the selected disease's row is echoed via a
 * slightly brighter background even without hover, so the connection to
 * the current brain view is visible at rest, not just on interaction. */
export default function SpecificityMatrix({ data }: Props) {
  const { rows, cols, matrix } = data.specificity;
  const selectedDisease = useAppStore((s) => s.selectedDisease);
  const [hover, setHover] = useState<{ i: number; j: number } | null>(null);

  const size = rows.length;
  const w = LABEL_W + CELL * size;
  const h = LABEL_W + CELL * size;

  return (
    <Panel title="Specificity">
      <svg width={w} height={h} role="img" aria-label="Disease specificity matrix">
        <Group>
          {cols.map((c, j) => (
            <text
              key={c}
              x={LABEL_W + j * CELL + CELL / 2}
              y={LABEL_W - 8}
              fontSize={10}
              fill="var(--color-ink-muted)"
              textAnchor="middle"
            >
              {c}
            </text>
          ))}
          {rows.map((r, i) => (
            <text
              key={r}
              x={LABEL_W - 8}
              y={LABEL_W + i * CELL + CELL / 2 + 4}
              fontSize={10}
              fill="var(--color-ink-muted)"
              textAnchor="end"
            >
              {r}
            </text>
          ))}

          {matrix.map((rowVals, i) =>
            rowVals.map((val, j) => {
              const isDiagonal = i === j;
              const isSelectedRow = rows[i] === selectedDisease;
              const isHovered = hover?.i === i && hover?.j === j;
              const isHighlighted = hover ? hover.i === i || hover.j === j : false;
              const [r, g, b] = diverging(val, 1);
              const fill = toCssHex([r, g, b]);
              const textColor = Math.abs(val) > 0.5 ? "#fff" : "#111";

              return (
                <g
                  key={`${i}-${j}`}
                  onMouseEnter={() => setHover({ i, j })}
                  onMouseLeave={() => setHover(null)}
                  tabIndex={0}
                  role="button"
                  aria-label={`${rows[i]} signature vs ${cols[j]} atrophy: r=${val.toFixed(2)}`}
                >
                  <rect
                    x={LABEL_W + j * CELL}
                    y={LABEL_W + i * CELL}
                    width={CELL - 2}
                    height={CELL - 2}
                    rx={3}
                    fill={fill}
                    opacity={!hover || isHighlighted ? 1 : 0.45}
                    stroke={isDiagonal ? "var(--color-ink)" : isSelectedRow ? "var(--color-accent)" : "none"}
                    strokeWidth={isDiagonal ? 1.5 : 1}
                    strokeOpacity={isDiagonal ? 0.5 : 0.4}
                  />
                  <text
                    x={LABEL_W + j * CELL + CELL / 2}
                    y={LABEL_W + i * CELL + CELL / 2 + 4}
                    fontSize={11}
                    fill={textColor}
                    textAnchor="middle"
                    opacity={!hover || isHighlighted ? 1 : 0.45}
                  >
                    {val.toFixed(2)}
                  </text>
                  {isHovered && (
                    <title>{`${rows[i]} signature vs. ${cols[j]} atrophy map: r = ${val.toFixed(2)}`}</title>
                  )}
                </g>
              );
            }),
          )}
        </Group>
      </svg>
      <p className="mt-1 text-[11px] text-ink-muted">
        row = signature, column = atrophy map; diagonal = each disease vs. its own ground truth
      </p>
    </Panel>
  );
}
