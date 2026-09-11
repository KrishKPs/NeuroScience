import { createScene } from "./scene.js";
import { loadMesh, buildCorticalMesh, updateCorticalMeshColors } from "./corticalMesh.js";
import { buildSubcorticalSpheres, updateSubcorticalSphereColors } from "./subcorticalSpheres.js";
import { setupDiseaseSelector } from "./ui/diseaseSelector.js";
import { setupRaycastPicker } from "./raycastPicker.js";
import { setupInfoPanel } from "./ui/infoPanel.js";
import { setupStatsPanel } from "./ui/statsPanel.js";
import { setupSpecificityMatrix } from "./ui/specificityMatrix.js";
import { setupValidationScatter } from "./ui/validationScatter.js";

const DEFAULT_DISEASE = "parkinsons";

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
  return res.json();
}

async function loadAllData() {
  const [meshData, regionsData, validationSummary, specificityMatrix, genesTopContributors] =
    await Promise.all([
      loadMesh(),
      loadJson("/data/regions.json"),
      loadJson("/data/validation_summary.json"),
      loadJson("/data/specificity_matrix.json"),
      loadJson("/data/genes_top_contributors.json"),
    ]);
  return { meshData, regionsData, validationSummary, specificityMatrix, genesTopContributors };
}

/** Data loading + non-WebGL UI panels (stats/info/specificity/validation) —
 * kept independent of the 3D scene so a WebGL failure (unsupported browser,
 * hardware acceleration disabled) doesn't also take down panels that don't
 * need it. Returns hooks the 3D-scene setup uses to stay in sync.
 */
function setupUiPanels(data) {
  const state = { disease: DEFAULT_DISEASE };

  const statsPanel = setupStatsPanel(document.getElementById("stats-panel"), data.validationSummary);
  const infoPanel = setupInfoPanel(document.getElementById("info-panel"));
  setupSpecificityMatrix(document.getElementById("specificity-matrix"), data.specificityMatrix);
  const validationScatter = setupValidationScatter(
    document.getElementById("validation-scatter"),
    data.regionsData,
  );

  const onDiseaseChangeCallbacks = [];
  setupDiseaseSelector(document.getElementById("disease-selector"), DEFAULT_DISEASE, (disease) => {
    state.disease = disease;
    statsPanel.update(disease);
    validationScatter.update(disease);
    for (const cb of onDiseaseChangeCallbacks) cb(disease);
  });

  statsPanel.update(state.disease);
  validationScatter.update(state.disease);

  return {
    state,
    infoPanel,
    onDiseaseChange: (cb) => onDiseaseChangeCallbacks.push(cb),
  };
}

function setupThreeScene(data, ui) {
  const container = document.getElementById("scene-container");
  const { scene, camera, renderer } = createScene(container);

  const corticalMesh = buildCorticalMesh(data.meshData, data.regionsData, ui.state.disease);
  scene.add(corticalMesh);

  const subcorticalSpheres = buildSubcorticalSpheres(data.regionsData, ui.state.disease);
  scene.add(subcorticalSpheres);

  ui.onDiseaseChange((disease) => {
    updateCorticalMeshColors(corticalMesh, data.meshData, data.regionsData, disease);
    updateSubcorticalSphereColors(subcorticalSpheres, data.regionsData, disease);
  });

  setupRaycastPicker({
    camera,
    renderer,
    pickables: [corticalMesh, ...subcorticalSpheres.children],
    meshData: data.meshData,
    regionsData: data.regionsData,
    genesTopContributors: data.genesTopContributors,
    getDisease: () => ui.state.disease,
    onHover: (region, genes) => ui.infoPanel.show(region, genes, ui.state.disease),
    onLeave: () => ui.infoPanel.hide(),
  });
}

async function main() {
  const data = await loadAllData();
  const ui = setupUiPanels(data);

  try {
    setupThreeScene(data, ui);
  } catch (err) {
    console.error("3D scene failed to initialize:", err);
    const isWebglError = /webgl/i.test(err.message ?? "");
    document.getElementById("scene-container").innerText = isWebglError
      ? "WebGL is unavailable in this browser/session (hardware acceleration disabled or sandboxed) — the 3D scene can't render here. Data and the panels around it are unaffected; try a normal desktop browser with hardware acceleration enabled."
      : `3D scene failed to load: ${err.message}`;
  }
}

main().catch((err) => {
  console.error("Failed to initialize viewer:", err);
  document.getElementById("scene-container").innerText =
    "Failed to load. Check the console — likely a missing /data/*.json file (run `python run_pipeline.py` first).";
});
