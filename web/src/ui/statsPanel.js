// Field names differ slightly per disease in validation_summary.json because
// each disease's validation is a genuinely different test (PD: subcortical
// variogram null; SCZ: cortical spin test; AD: approximate whole-brain
// fallback, non-significant) — see CLAUDE.md §16. This map is the one place
// that reconciles those differences into a uniform display.
const FIELD_MAP = {
  parkinsons: {
    r: "real_r_subcortex_n14",
    spatialP: "spatial_null_p",
    spatialLabel: "variogram (subcortex)",
  },
  schizophrenia: {
    r: "real_r_cortex_n68",
    spatialP: "spatial_null_p",
    spatialLabel: "spin test (cortex)",
  },
  alzheimers: {
    r: "real_r_vs_vulnerable_roi_n83",
    spatialP: "approx_spatial_null_p",
    spatialLabel: "approx. whole-brain variogram",
  },
};

function fmtP(p) {
  if (p === undefined || p === null) return "—";
  return p < 0.001 ? "< 0.001" : p.toFixed(4);
}

function row(label, value) {
  return `<div class="stat-row"><span class="label">${label}</span><span>${value}</span></div>`;
}

export function setupStatsPanel(container, validationSummary) {
  container.classList.add("panel");

  function update(disease) {
    const d = validationSummary[disease];
    const map = FIELD_MAP[disease];
    const r = d[map.r];
    const geneSetP = d.gene_set_null_p;
    const spatialP = d[map.spatialP];
    const significant = geneSetP < 0.05 && spatialP < 0.05;

    let html = `<h3>Validation</h3>`;
    html += row("r", r.toFixed(2));
    html += row("N regions", d.n_regions);
    html += row("Gene-set null p", fmtP(geneSetP));
    html += row(`Spatial null p<br><span style="font-size:11px;color:#9aa0ac">(${map.spatialLabel})</span>`, fmtP(spatialP));
    html += `<div style="margin-top:8px;font-weight:600;color:${significant ? "#5ec26a" : "#e0a13a"}">
      ${significant ? "Survives both null models" : "Not significant under both nulls"}
    </div>`;

    if (d.ml_layer) {
      html += `<hr style="border-color:rgba(255,255,255,0.1);margin:10px 0" />`;
      html += `<h3>ElasticNet layer</h3>`;
      html += row("CV R² (pooled)", d.ml_layer.cv_r2_pooled.toFixed(2));
      html += row("Non-zero genes", d.ml_layer.n_nonzero_genes);
      html += row("Overlapping GWAS", d.ml_layer.n_genes_overlapping_gwas);
    }

    if (d.note) {
      html += `<div style="margin-top:8px;font-size:12px;color:#9aa0ac;font-style:italic">${d.note}</div>`;
    }

    container.innerHTML = html;
  }

  return { update };
}
