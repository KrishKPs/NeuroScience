import * as THREE from "three";
import { diverging } from "./colorScale.js";
import { computeVmax } from "./corticalMesh.js";

const SPHERE_RADIUS = 4; // mm-scale, visually reasonable against the ~70mm-radius cortical mesh

/** 15 subcortical/brainstem structures (caudate/putamen/pallidum/thalamus/
 * accumbens/hippocampus/amygdala x2 hemispheres + brainstem), one THREE.Mesh
 * sphere each, at their real MNI centroid coordinates (src/data_load.py::
 * get_region_centroids). Plain Mesh objects, not InstancedMesh — 15 is
 * trivial for the GPU and keeping them separate makes per-region raycast
 * hits and color updates simpler to reason about (CLAUDE.md §17).
 */
export function buildSubcorticalSpheres(regionsData, disease) {
  const vmax = computeVmax(regionsData, disease);
  const group = new THREE.Group();
  group.name = "subcorticalSpheres";

  for (const region of Object.values(regionsData.regions)) {
    if (region.is_cortical) continue;

    const rgb = diverging(region.scores[disease], vmax);
    const geometry = new THREE.SphereGeometry(SPHERE_RADIUS, 16, 16);
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(...rgb),
      roughness: 0.6,
    });
    const sphere = new THREE.Mesh(geometry, material);
    sphere.position.set(region.x, region.y, region.z);
    sphere.userData.regionId = region.id;
    sphere.name = `subcortical-${region.id}`;
    group.add(sphere);
  }

  return group;
}

export function updateSubcorticalSphereColors(group, regionsData, disease) {
  const vmax = computeVmax(regionsData, disease);
  for (const sphere of group.children) {
    const region = regionsData.regions[String(sphere.userData.regionId)];
    const rgb = diverging(region.scores[disease], vmax);
    sphere.material.color.setRGB(...rgb);
  }
}
