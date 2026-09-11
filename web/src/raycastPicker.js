import * as THREE from "three";

/** One THREE.Raycaster on pointermove/click against the cortical mesh +
 * subcortical spheres. Mesh hit -> intersection.face.a (a vertex index) ->
 * meshData.vertexRegionId[idx] -> region id. Sphere hit -> userData.regionId
 * directly. Region id 0 (medial wall / background) or no hit -> onLeave.
 */
export function setupRaycastPicker({
  camera,
  renderer,
  pickables,
  meshData,
  regionsData,
  genesTopContributors,
  getDisease,
  onHover,
  onLeave,
}) {
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function resolveRegionId(intersection) {
    if (intersection.object.name === "corticalMesh") {
      const vertexIndex = intersection.face.a;
      return meshData.vertexRegionId[vertexIndex];
    }
    return intersection.object.userData.regionId;
  }

  function handlePointer(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(pointer, camera);
    const intersections = raycaster.intersectObjects(pickables, false);

    if (intersections.length === 0) {
      onLeave();
      return;
    }

    const regionId = resolveRegionId(intersections[0]);
    const region = regionsData.regions[String(regionId)];
    if (!region) {
      onLeave();
      return;
    }

    const disease = getDisease();
    const genes = genesTopContributors[disease]?.[String(regionId)] ?? [];
    onHover(region, genes);
  }

  renderer.domElement.addEventListener("pointermove", handlePointer);
  renderer.domElement.addEventListener("pointerleave", onLeave);
}
