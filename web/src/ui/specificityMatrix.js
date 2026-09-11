import { diverging, toCssHex } from "../colorScale.js";

const LABELS = { parkinsons: "PD", schizophrenia: "SCZ", alzheimers: "AD" };

export function setupSpecificityMatrix(container, specificityMatrix) {
  container.classList.add("panel");

  const { diseases, atrophy_maps, matrix } = specificityMatrix;
  const cell = 44;
  const labelW = 50;
  const size = diseases.length;
  const svgW = labelW + cell * size;
  const svgH = labelW + cell * size;

  let svg = `<h3>Specificity matrix</h3>`;
  svg += `<svg width="${svgW}" height="${svgH}" style="overflow:visible">`;

  // Column labels (atrophy maps).
  atrophy_maps.forEach((d, j) => {
    svg += `<text x="${labelW + j * cell + cell / 2}" y="${labelW - 8}" font-size="10" fill="#9aa0ac" text-anchor="middle">${LABELS[d]}</text>`;
  });
  // Row labels (signatures).
  diseases.forEach((d, i) => {
    svg += `<text x="${labelW - 8}" y="${labelW + i * cell + cell / 2 + 4}" font-size="10" fill="#9aa0ac" text-anchor="end">${LABELS[d]}</text>`;
  });

  matrix.forEach((rowVals, i) => {
    rowVals.forEach((val, j) => {
      const [r, g, b] = diverging(val, 1);
      const hex = toCssHex([r, g, b]);
      const textColor = Math.abs(val) > 0.5 ? "#fff" : "#111";
      svg += `<rect x="${labelW + j * cell}" y="${labelW + i * cell}" width="${cell - 2}" height="${cell - 2}" fill="${hex}" rx="3" />`;
      svg += `<text x="${labelW + j * cell + cell / 2}" y="${labelW + i * cell + cell / 2 + 4}" font-size="11" fill="${textColor}" text-anchor="middle">${val.toFixed(2)}</text>`;
    });
  });

  svg += `</svg>`;
  svg += `<div style="font-size:11px;color:#9aa0ac;margin-top:6px">row = signature, column = atrophy map; diagonal = each disease vs. its own ground truth</div>`;

  container.innerHTML = svg;
}
