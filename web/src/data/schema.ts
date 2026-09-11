// Mirrors src/export_web_data.py's output exactly (Frontend.md §9). The UI
// only ever consumes this — never computes stats itself (rule 5).

export type DiseaseCode = "PD" | "SCZ" | "AD";

export interface Region {
  id: string; // "L_putamen"
  name: string; // "putamen (L)"
  hemi: "L" | "R" | "B";
  structure: "cortical" | "subcortical";
  signature: number;
  atrophy: number | null;
}

export interface Validation {
  r: number;
  n_regions: number;
  geneset_p: number;
  spatial_p: number;
  spatial_method: string;
  significant: boolean;
  ground_truth?: string;
  note?: string;
}

export interface TopGene {
  symbol: string;
  weight: number;
  is_gwas: boolean;
}

export interface Model {
  cv_r2: number;
  nonzero_genes: number;
  overlap_gwas: number;
  top_genes: TopGene[];
}

export interface DiseasePayload {
  label: string;
  regions: Region[];
  validation: Validation;
  model?: Model;
}

export interface ColormapSpec {
  type: "diverging";
  domain: [number, number];
  units: string;
}

export interface Specificity {
  rows: DiseaseCode[];
  cols: DiseaseCode[];
  matrix: number[][];
}

export interface Assets {
  mesh_pial: [string, string];
  mesh_inflated: [string, string];
  atlas_labels: [string, string];
  region_index: string;
  overlays: Record<DiseaseCode, { signature: [string, string]; atrophy: [string, string] | null }>;
  fallback_2d: Record<DiseaseCode, string>;
}

export interface SignatureData {
  meta: { atlas: string; n_regions: number; generated: string };
  colormaps: { signature: ColormapSpec; atrophy: ColormapSpec };
  diseases: Record<DiseaseCode, DiseasePayload>;
  specificity: Specificity;
  assets: Assets;
}

export type RegionIndex = Record<string, number>; // "L_putamen" -> mesh label id (37)
