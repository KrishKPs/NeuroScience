function row(label, value) {
  return `<div class="stat-row"><span class="label">${label}</span><span>${value}</span></div>`;
}

export function setupInfoPanel(container) {
  container.classList.add("panel");
  container.innerHTML = `<h3>Region</h3><div id="info-body" style="color:#9aa0ac">Hover a region</div>`;
  const body = container.querySelector("#info-body");

  function show(region, genes, disease) {
    let html = "";
    html += row("Region", `${region.label} (${region.hemisphere})`);
    html += row("Structure", region.structure);
    html += row("Score", region.scores[disease].toFixed(3));
    if (region.atrophy[disease] !== null && region.atrophy[disease] !== undefined) {
      html += row("Atrophy (d)", region.atrophy[disease].toFixed(3));
    }

    if (genes && genes.length > 0) {
      html += `<div style="margin-top:8px;font-size:12px;color:#9aa0ac">Top contributing genes</div>`;
      for (const g of genes) {
        html += `<div class="stat-row"><span>${g.gene}${g.in_ml_nonzero ? '<span class="badge-ml">ML</span>' : ""}</span><span>${g.z.toFixed(2)}</span></div>`;
      }
    }

    body.innerHTML = html;
  }

  function hide() {
    body.innerHTML = `<span style="color:#9aa0ac">Hover a region</span>`;
  }

  return { show, hide };
}
