import { motion } from "framer-motion";
import { useAppStore } from "../store";
import type { SignatureData } from "../data/schema";
import Panel from "../ui/Panel";
import Value from "../ui/Value";
import AnimatedNumber from "../ui/AnimatedNumber";
import { fmtP } from "../lib/format";

interface Props {
  data: SignatureData;
}

/** Frontend.md §6.3. The verdict line is the point — readable at a glance —
 * so it's rendered distinctly, not just another row. AD's honest
 * non-significant result gets the same neutral treatment as any other
 * disease that doesn't survive both nulls, per CLAUDE.md rule 6: not
 * hidden, not dramatized either. Content fades on disease switch (§3.7);
 * MotionConfig at the app root makes this respect prefers-reduced-motion
 * automatically.
 */
export default function ValidationPanel({ data }: Props) {
  const disease = useAppStore((s) => s.selectedDisease);
  const v = data.diseases[disease].validation;

  return (
    <Panel title="Validation">
      <motion.div key={disease} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
        <Value label="r (signature vs. atrophy)" value={<AnimatedNumber value={v.r} decimals={2} />} />
        <Value label="regions (N)" value={v.n_regions} />
        <Value label={<span title="10,000 random gene sets of the same size — is this specific gene set special?">gene-set null p</span>} value={fmtP(v.geneset_p)} />
        <Value
          label={<span title="10,000 spatially-structured surrogate maps — does the correlation survive once spatial autocorrelation is accounted for?">spatial null p</span>}
          value={<>{fmtP(v.spatial_p)} <span className="text-[11px] text-ink-muted">({v.spatial_method})</span></>}
        />

        <div className={`mt-2 text-[13px] font-medium ${v.significant ? "text-good" : "text-ink-muted"}`}>
          {v.significant ? "Survives both null models" : "Does not survive both null models"}
        </div>

        {v.ground_truth && (
          <p className="mt-1 text-[11px] text-ink-muted">{v.ground_truth}</p>
        )}
      </motion.div>
    </Panel>
  );
}
