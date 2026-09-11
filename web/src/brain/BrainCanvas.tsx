import { useEffect, useRef, useState } from "react";
import { Niivue } from "@niivue/niivue";
import { useAppStore, type ViewPreset } from "../store";
import type { SignatureData, RegionIndex } from "../data/schema";
import { registerColormaps, DIVERGING_COLORMAP_NAME } from "./colormaps";

// @niivue/niivue's package root doesn't export the NVMeshLayer type itself
// (only NVMeshLayerDefaults, a value) despite loadMeshes()'s `layers` param
// requiring that shape -- redeclared locally from the library's own
// nvdocument .d.ts (not guessed). Its fields are non-optional there even
// though NVMeshLayerDefaults implies runtime defaults exist; supplying them
// explicitly satisfies the type checker and removes any doubt about
// whether default-merging actually happens (Frontend.md §16: verify, don't
// assume, for anything untestable live in this session).
interface MeshLayerInput {
  name?: string;
  url?: string;
  opacity: number;
  colormap: string;
  cal_min: number;
  cal_max: number;
  cal_minNeg: number;
  cal_maxNeg: number;
  frame4D: number;
  nFrame4D: number;
  values: number[];
  useNegativeCmap: boolean;
  showLegend: boolean;
  outlineBorder: number;
  colorbarVisible?: boolean;
  colormapType?: number;
}

function meshLayer(overrides: Partial<MeshLayerInput> & { url: string }): MeshLayerInput {
  return {
    opacity: 1,
    colormap: "gray",
    cal_min: 0,
    cal_max: 1,
    cal_minNeg: 0,
    cal_maxNeg: 0,
    frame4D: 0,
    nFrame4D: 1,
    values: [],
    useNegativeCmap: false,
    showLegend: false,
    outlineBorder: 0,
    ...overrides,
  };
}

// Camera angles are best-effort per standard neuroimaging convention
// (azimuth around the vertical axis, elevation above/below the horizontal
// plane) and have NOT been visually confirmed against NiiVue's own azimuth=0
// reference direction (this session could not render WebGL to check —
// Frontend.md §16). "Medial" reuses the lateral-R angle: a medial view only
// reads correctly when paired with hemisphere="left" (hiding the right
// hemisphere so you're looking at the left hemisphere's inner/medial
// surface) — that pairing isn't enforced here, just documented.
const VIEW_PRESETS: Record<ViewPreset, { azimuth: number; elevation: number }> = {
  lateralL: { azimuth: 270, elevation: 0 },
  lateralR: { azimuth: 90, elevation: 0 },
  superior: { azimuth: 0, elevation: 90 },
  anterior: { azimuth: 0, elevation: 0 },
  medial: { azimuth: 90, elevation: 0 },
};

interface Props {
  data: SignatureData;
  regionIndex: RegionIndex;
  onNiivueError: (message: string) => void;
}

/** The hero — NiiVue-driven 3D brain (Frontend.md §5). Loads the DK
 * cortical mesh (pial/inflated toggle), a low-opacity discrete atlas layer
 * for structural context, and the selected disease's signature/atrophy
 * overlay. Disease/overlay/surface changes reload the mesh+layers (a full
 * reload, not an in-place value mutation — NiiVue's public API doesn't
 * clearly document a supported way to mutate an already-loaded mesh
 * layer's values in place, so the well-documented `loadMeshes` path is used
 * instead; see Frontend.md §16 for the reasoning). Region hover/click is
 * read from `onLocationChange`'s per-layer `values` array, matching the
 * atlas layer's raw label id back to a region via `regionIndex`.
 */
export default function BrainCanvas({ data, regionIndex, onNiivueError }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nvRef = useRef<Niivue | null>(null);
  const [ready, setReady] = useState(false);

  const disease = useAppStore((s) => s.selectedDisease);
  const overlayMode = useAppStore((s) => s.overlayMode);
  const opacity = useAppStore((s) => s.opacity);
  const surface = useAppStore((s) => s.surface);
  const viewPreset = useAppStore((s) => s.viewPreset);
  const setHoveredRegion = useAppStore((s) => s.setHoveredRegion);
  const setPinnedRegion = useAppStore((s) => s.setPinnedRegion);

  const labelIdToRegionId = useRef<Map<number, string>>(new Map());

  // Mount once.
  useEffect(() => {
    if (!canvasRef.current) return;
    let cancelled = false;

    const nv = new Niivue({
      backColor: [0.047, 0.063, 0.082, 1], // --bg #0C1015
      show3Dcrosshair: false,
      isColorbar: false, // we render our own colorbar (Region/Validation panels), not NiiVue's
      meshXRay: 0,
    });
    nvRef.current = nv;

    for (const [rid, labelId] of Object.entries(regionIndex)) {
      labelIdToRegionId.current.set(labelId, rid);
    }

    nv.attachToCanvas(canvasRef.current).then(() => {
      if (cancelled) return;
      registerColormaps(nv);
      nv.setSliceType(nv.sliceTypeRender);
      nv.onLocationChange = (raw: unknown) => {
        const loc = raw as { values?: Array<{ name: string; value: number }> };
        const atlasReading = loc.values?.find((v) => v.name === "atlas");
        if (atlasReading && atlasReading.value > 0) {
          const rid = labelIdToRegionId.current.get(Math.round(atlasReading.value));
          setHoveredRegion(rid ?? null);
        } else {
          setHoveredRegion(null);
        }
      };
      nv.onMouseUp = () => {
        const current = useAppStore.getState().hoveredRegionId;
        if (current) setPinnedRegion(current);
      };
      setReady(true);
    }).catch((err: unknown) => {
      onNiivueError(err instanceof Error ? err.message : "Failed to attach NiiVue to canvas");
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load/reload mesh + layers whenever disease, overlay mode, or surface changes.
  useEffect(() => {
    const nv = nvRef.current;
    if (!nv || !ready) return;

    const meshPaths = surface === "pial" ? data.assets.mesh_pial : data.assets.mesh_inflated;
    const atlasPaths = data.assets.atlas_labels;
    const overlayPaths =
      overlayMode === "atrophy" ? data.assets.overlays[disease].atrophy : data.assets.overlays[disease].signature;

    if (!overlayPaths) {
      // AD has no atrophy overlay (Frontend.md §16 / CLAUDE.md §16) — caller
      // (OverlayToggle) should already prevent selecting "atrophy" for AD,
      // this is a defensive no-op rather than a crash.
      return;
    }

    const domain = data.colormaps[overlayMode === "atrophy" ? "atrophy" : "signature"].domain;

    let cancelled = false;
    nv.loadMeshes([
      {
        url: meshPaths[0],
        name: "cortex-lh",
        layers: [
          meshLayer({ url: atlasPaths[0], name: "atlas", colormap: "actc", opacity: 0.25, cal_max: 83 }),
          meshLayer({
            url: overlayPaths[0], name: "signature", colormap: DIVERGING_COLORMAP_NAME,
            cal_min: domain[0], cal_max: domain[1], opacity, colorbarVisible: false,
          }),
        ],
      },
      {
        url: meshPaths[1],
        name: "cortex-rh",
        layers: [
          meshLayer({ url: atlasPaths[1], name: "atlas", colormap: "actc", opacity: 0.25, cal_max: 83 }),
          meshLayer({
            url: overlayPaths[1], name: "signature", colormap: DIVERGING_COLORMAP_NAME,
            cal_min: domain[0], cal_max: domain[1], opacity, colorbarVisible: false,
          }),
        ],
      },
    ]).catch((err: unknown) => {
      if (!cancelled) {
        onNiivueError(err instanceof Error ? err.message : "Failed to load brain mesh");
      }
    });

    return () => {
      cancelled = true;
    };
  }, [ready, disease, overlayMode, surface, opacity, data, onNiivueError]);

  // Camera presets.
  useEffect(() => {
    const nv = nvRef.current;
    if (!nv || !ready) return;
    const { azimuth, elevation } = VIEW_PRESETS[viewPreset];
    nv.setRenderAzimuthElevation(azimuth, elevation);
  }, [ready, viewPreset]);

  return <canvas ref={canvasRef} className="h-full w-full" aria-label="3D brain viewer" />;
}
