import { create } from "zustand";
import type { DiseaseCode } from "./data/schema";

export type OverlayMode = "signature" | "atrophy" | "diff";
export type Surface = "pial" | "inflated";
export type Hemisphere = "both" | "left" | "right";
export type ViewPreset = "lateralL" | "lateralR" | "superior" | "anterior" | "medial";

interface AppState {
  selectedDisease: DiseaseCode;
  overlayMode: OverlayMode;
  opacity: number; // data layer over atlas layer, 0-1
  hemisphere: Hemisphere;
  surface: Surface;
  viewPreset: ViewPreset;
  hoveredRegionId: string | null;
  pinnedRegionId: string | null;

  setDisease: (d: DiseaseCode) => void;
  setOverlayMode: (m: OverlayMode) => void;
  setOpacity: (v: number) => void;
  setHemisphere: (h: Hemisphere) => void;
  setSurface: (s: Surface) => void;
  setViewPreset: (v: ViewPreset) => void;
  setHoveredRegion: (id: string | null) => void;
  setPinnedRegion: (id: string | null) => void;
}

/** One store so any component reads/sets linked-brushing
 * state without prop-drilling. Region hover/pin is shared across
 * brain <-> region panel <-> scatter. */
export const useAppStore = create<AppState>((set) => ({
  selectedDisease: "PD",
  overlayMode: "signature",
  opacity: 1,
  hemisphere: "both",
  surface: "pial",
  viewPreset: "lateralL",
  hoveredRegionId: null,
  pinnedRegionId: null,

  setDisease: (d) => set({ selectedDisease: d }),
  setOverlayMode: (m) => set({ overlayMode: m }),
  setOpacity: (v) => set({ opacity: v }),
  setHemisphere: (h) => set({ hemisphere: h }),
  setSurface: (s) => set({ surface: s }),
  setViewPreset: (v) => set({ viewPreset: v }),
  setHoveredRegion: (id) => set({ hoveredRegionId: id }),
  setPinnedRegion: (id) => set({ pinnedRegionId: id }),
}));
