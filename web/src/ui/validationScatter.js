const W = 260;
const H = 180;
const PAD = 30;

export function setupValidationScatter(container, regionsData) {
  container.classList.add("panel");

  function update(disease) {
    const points = Object.values(regionsData.regions)
      .filter((r) => r.atrophy[disease] !== null && r.atrophy[disease] !== undefined)
      .map((r) => ({ x: r.scores[disease], y: r.atrophy[disease] }));

    if (points.length === 0) {
      container.innerHTML = `<h3>Validation scatter</h3>
        <div style="font-size:12px;color:#9aa0ac;font-style:italic">
          No continuous ENIGMA ground truth for this disease (fallback ROI
          test used instead — see the validation panel; result not
          significant under either null).
        </div>`;
      return;
    }

    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(...ys), yMax = Math.max(...ys);

    const sx = (x) => PAD + ((x - xMin) / (xMax - xMin || 1)) * (W - 2 * PAD);
    const sy = (y) => H - PAD - ((y - yMin) / (yMax - yMin || 1)) * (H - 2 * PAD);

    let svg = `<h3>Validation scatter</h3>`;
    svg += `<svg width="${W}" height="${H}">`;
    svg += `<line x1="${PAD}" y1="${H - PAD}" x2="${W - PAD}" y2="${H - PAD}" stroke="#444" />`;
    svg += `<line x1="${PAD}" y1="${PAD}" x2="${PAD}" y2="${H - PAD}" stroke="#444" />`;
    for (const p of points) {
      svg += `<circle cx="${sx(p.x)}" cy="${sy(p.y)}" r="3" fill="#3a6fd8" opacity="0.8" />`;
    }
    svg += `<text x="${W / 2}" y="${H - 6}" font-size="10" fill="#9aa0ac" text-anchor="middle">score</text>`;
    svg += `<text x="10" y="${H / 2}" font-size="10" fill="#9aa0ac" text-anchor="middle" transform="rotate(-90 10 ${H / 2})">atrophy (d)</text>`;
    svg += `</svg>`;

    container.innerHTML = svg;
  }

  return { update };
}
