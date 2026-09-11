import { useAppStore } from "../store";
import type { SignatureData } from "../data/schema";
import Panel from "../ui/Panel";
import Value from "../ui/Value";
import { fmtNum } from "../lib/format";

interface Props {
  data: SignatureData;
}

/** Frontend.md §6.5. Only Parkinson's has an ElasticNet model (CLAUDE.md's
 * pipeline only built one, for the primary disease) — SCZ/AD render an
 * honest "not built for this disease" note instead of hiding the panel
 * entirely, so its absence isn't mistaken for a loading/data bug. */
export default function ModelPanel({ data }: Props) {
  const disease = useAppStore((s) => s.selectedDisease);
  const model = data.diseases[disease].model;

  return (
    <Panel title="Model (ElasticNet)">
      {!model ? (
        <p className="text-[13px] text-ink-muted">
          Not built for this disease — see CLAUDE.md §7.7 (primary disease only).
        </p>
      ) : (
        <div>
          <Value label="CV R² (pooled)" value={fmtNum(model.cv_r2)} />
          <Value label="non-zero genes" value={model.nonzero_genes} />
          <Value label="overlapping GWAS" value={model.overlap_gwas} />

          <div className="mt-2 flex flex-wrap gap-1">
            {model.top_genes.map((g) => (
              <span
                key={g.symbol}
                className="rounded border border-hairline px-1.5 py-0.5 font-mono text-[11px]"
                title={`weight ${g.weight.toFixed(4)}`}
              >
                {g.symbol}
                {g.is_gwas && <span className="ml-1 text-accent">•</span>}
              </span>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}
