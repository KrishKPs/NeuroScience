import * as THREE from "three";
import { diverging } from "./colorScale.js";

const BACKGROUND_COLOR = [0.55, 0.55, 0.55]; // neutral gray for medial-wall / unlabeled vertices (region id 0)

export async function loadMesh() {
  const res = await fetch("/data/mesh.json");
  const data = await res.json();
  return {
    vertices: new Float32Array(data.vertices),
    faces: new Uint32Array(data.faces),
    vertexRegionId: new Int32Array(data.vertex_region_id),
    nVerticesPerHemi: data._provenance.n_vertices_per_hemi,
  };
}

/** max(abs(score)) across all 83 regions for `disease` — symmetric color
 * scale around zero, same convention as src/figures.py::plot_hero_figure. */
export function computeVmax(regionsData, disease) {
  let vmax = 0;
  for (const region of Object.values(regionsData.regions)) {
    const v = Math.abs(region.scores[disease]);
    if (v > vmax) vmax = v;
  }
  return vmax || 1;
}

function computeVertexColors(meshData, regionsData, disease) {
  const vmax = computeVmax(regionsData, disease);
  const n = meshData.vertexRegionId.length;
  const colors = new Float32Array(n * 3);

  for (let i = 0; i < n; i++) {
    const regionId = meshData.vertexRegionId[i];
    const region = regionsData.regions[String(regionId)];
    const rgb = region ? diverging(region.scores[disease], vmax) : BACKGROUND_COLOR;
    colors[i * 3] = rgb[0];
    colors[i * 3 + 1] = rgb[1];
    colors[i * 3 + 2] = rgb[2];
  }
  return colors;
}

export function buildCorticalMesh(meshData, regionsData, disease) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(meshData.vertices, 3));
  geometry.setIndex(new THREE.BufferAttribute(meshData.faces, 1));
  geometry.setAttribute(
    "color",
    new THREE.BufferAttribute(computeVertexColors(meshData, regionsData, disease), 3),
  );
  geometry.computeVertexNormals();

  const material = new THREE.MeshStandardMaterial({
    vertexColors: true,
    side: THREE.DoubleSide,
    roughness: 0.85,
    metalness: 0.0,
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = "corticalMesh";
  // Recenter roughly (fsaverage5 is already near-origin, but this keeps
  // OrbitControls' default target sane regardless of atlas quirks).
  geometry.computeBoundingSphere();
  return mesh;
}

/** Recolor in place on disease toggle — no geometry rebuild. */
export function updateCorticalMeshColors(mesh, meshData, regionsData, disease) {
  const colors = computeVertexColors(meshData, regionsData, disease);
  mesh.geometry.attributes.color.set(colors);
  mesh.geometry.attributes.color.needsUpdate = true;
}
