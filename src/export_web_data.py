"""Export the finished analysis to the web frontend's data contract
(src/Frontend.md §9) and prepare its static mesh assets (§13). Pure read +
reshape of already-committed pipeline outputs — the one new computation
(top_genes) reuses score.zscore_genes directly so those numbers stay
consistent with the score already shown elsewhere.
"""
from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import pandas as pd

from src.data_load import fetch_dk_atlas
from src.figures import plot_2d_fallback_schematic
from src.harmonize import reconcile_genes
from src.score import zscore_genes

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTERIM = PROJECT_ROOT / "data" / "interim"
PROCESSED = PROJECT_ROOT / "data" / "processed"
WEB_PUBLIC = PROJECT_ROOT / "web" / "public"
WEB_ASSETS = WEB_PUBLIC / "assets"
WEB_DATA = WEB_PUBLIC / "data"

# Frontend.md uses short disease codes; the rest of the pipeline (CLAUDE.md,
# run_pipeline.py) uses full names — this is the one place that maps between them.
DISEASE_CODES = {"parkinsons": "PD", "schizophrenia": "SCZ", "alzheimers": "AD"}
DISEASE_CODES_REVERSE = {v: k for k, v in DISEASE_CODES.items()}
DISEASE_LABELS = {"PD": "Parkinson's", "SCZ": "Schizophrenia", "AD": "Alzheimer's"}
DISEASE_PREFIX = {"parkinsons": "pd", "schizophrenia": "scz", "alzheimers": "ad"}


def _region_string_id(hemi: str, label: str) -> str:
    return f"{hemi}_{label}"


def _region_display_name(hemi: str, label: str) -> str:
    words = label.replace("_", " ")
    # Split DK's concatenated labels (e.g. "caudalanteriorcingulate") is not
    # attempted — these are atlas-standard identifiers, shown as-is; only
    # hemisphere gets a readable suffix.
    hemi_suffix = {"L": " (L)", "R": " (R)", "B": ""}[hemi]
    return f"{words}{hemi_suffix}"


def prepare_mesh_assets(save: bool = True) -> dict:
    """Copy the DK surface + label GIfTI files NiiVue will load directly
    (Frontend.md §16: GIfTI, not .mz3 — NiiVue supports GIfTI natively for
    both mesh geometry and overlays, so the files abagen already ships and
    CLAUDE.md's pipeline already uses are reused with zero conversion).

    Pial: abagen's bundled fsaverage5-pial-{lh,rh}.surf.gii.gz.
    Inflated: neuromaps' cached fsaverage 10k density surface — verified
    vertex-for-vertex identical to abagen's pial mesh (same underlying
    fsaverage5 topology, confirmed 2026-09-11, max abs coordinate diff 0.0),
    so it aligns with the same DK vertex labels with no remapping needed.
    Labels: abagen's bundled atlas-desikankilliany-{lh,rh}.label.gii.gz.

    Ships as plain .gii (decompressed) rather than .gii.gz — avoids any
    doubt about whether the browser-side GIfTI loader handles gzip.
    """
    abagen_data = Path(__import__("abagen").__file__).parent / "data"
    neuromaps_fsaverage = Path.home() / "neuromaps-data" / "atlases" / "fsaverage"

    sources = {
        "dk_pial_lh.gii": abagen_data / "fsaverage5-pial-lh.surf.gii.gz",
        "dk_pial_rh.gii": abagen_data / "fsaverage5-pial-rh.surf.gii.gz",
        "dk_labels_lh.gii": abagen_data / "atlas-desikankilliany-lh.label.gii.gz",
        "dk_labels_rh.gii": abagen_data / "atlas-desikankilliany-rh.label.gii.gz",
    }
    inflated_sources = {
        "dk_inflated_lh.gii": neuromaps_fsaverage / "tpl-fsaverage_den-10k_hemi-L_inflated.surf.gii",
        "dk_inflated_rh.gii": neuromaps_fsaverage / "tpl-fsaverage_den-10k_hemi-R_inflated.surf.gii",
    }

    if save:
        WEB_ASSETS.mkdir(parents=True, exist_ok=True)
        for dest_name, src_path in sources.items():
            with gzip.open(src_path, "rb") as f_in:
                with open(WEB_ASSETS / dest_name, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        for dest_name, src_path in inflated_sources.items():
            shutil.copyfile(src_path, WEB_ASSETS / dest_name)  # already uncompressed .gii
        print(f"Saved {len(sources) + len(inflated_sources)} mesh/atlas assets to {WEB_ASSETS}")

    return {"pial": sources, "inflated": inflated_sources}


def build_region_index(atlas_info: pd.DataFrame) -> dict:
    """Maps our string region ids ('L_putamen') to the mesh's integer DK
    label ids (37) — the join key the frontend needs to color vertices from
    region-level data (Frontend.md §9's `region_index` asset)."""
    index = {}
    for _, row in atlas_info.iterrows():
        rid = _region_string_id(row["hemisphere"], row["label"])
        index[rid] = int(row["id"])
    return index


def _matched_genes_for(disease: str, expression: pd.DataFrame) -> list[str]:
    prefix = DISEASE_PREFIX[disease]
    if disease == "parkinsons":
        return pd.read_csv(INTERIM / "pd_matched_genes.csv")["gene"].tolist()
    risk_genes = pd.read_csv(INTERIM / f"{prefix}_gwas_risk_genes.csv")
    return reconcile_genes(risk_genes, expression)["matched"]


def build_disease_payload(
    disease: str,
    atlas_info: pd.DataFrame,
    expression: pd.DataFrame,
) -> dict:
    prefix = DISEASE_PREFIX[disease]
    score = pd.read_csv(PROCESSED / f"{prefix}_score_map_full.csv", index_col=0)["score"]

    atrophy_by_id: dict[int, float] = {}
    if disease == "parkinsons":
        atrophy_by_id = pd.read_csv(PROCESSED / "pd_subcortex_atrophy_map.csv", index_col=0)["atrophy_d"].to_dict()
    elif disease == "schizophrenia":
        atrophy_by_id = pd.read_csv(PROCESSED / "scz_cortex_atrophy_map.csv", index_col=0)["atrophy_d"].to_dict()
    # Alzheimer's: no continuous ENIGMA ground truth exists (CLAUDE.md §16) — atrophy_by_id stays empty.

    regions = []
    for _, row in atlas_info.iterrows():
        rid = int(row["id"])
        regions.append({
            "id": _region_string_id(row["hemisphere"], row["label"]),
            "name": _region_display_name(row["hemisphere"], row["label"]),
            "hemi": row["hemisphere"],
            "structure": "cortical" if row["structure"] == "cortex" else "subcortical",
            "signature": float(score.get(rid, float("nan"))),
            "atrophy": atrophy_by_id.get(rid),  # None (-> JSON null) where no ground truth exists
        })

    with open(PROCESSED / f"{prefix}_validation_summary.json") as f:
        vs = json.load(f)

    r_field = {
        "parkinsons": "real_r_subcortex_n14",
        "schizophrenia": "real_r_cortex_n68",
        "alzheimers": "real_r_vs_vulnerable_roi_n83",
    }[disease]
    spatial_p_field = "approx_spatial_null_p" if disease == "alzheimers" else "spatial_null_p"
    spatial_method = {
        "parkinsons": "variogram (subcortex)",
        "schizophrenia": "spin (cortex)",
        "alzheimers": "approx. whole-brain variogram",
    }[disease]

    validation = {
        "r": vs[r_field],
        "n_regions": vs["n_regions"],
        "geneset_p": vs["gene_set_null_p"],
        "spatial_p": vs[spatial_p_field],
        "spatial_method": spatial_method,
        "significant": vs["gene_set_null_p"] < 0.05 and vs[spatial_p_field] < 0.05,
    }
    if disease == "alzheimers":
        validation["ground_truth"] = "fallback canonical ROI list (no ENIGMA AD map available)"
        validation["note"] = vs["note"]

    payload = {
        "label": DISEASE_LABELS[DISEASE_CODES[disease]],
        "regions": regions,
        "validation": validation,
    }

    if disease == "parkinsons":
        with open(PROCESSED / "pd_ml_summary.json") as f:
            ml = json.load(f)
        nonzero = pd.read_csv(PROCESSED / "pd_ml_nonzero_genes.csv", index_col=0)
        gwas_overlap = set(pd.read_csv(PROCESSED / "pd_ml_genes_overlapping_gwas.csv", index_col=0).index)
        top_genes = [
            {"symbol": gene, "weight": float(row["coef"]), "is_gwas": gene in gwas_overlap}
            for gene, row in nonzero.iterrows()
        ]
        payload["model"] = {
            "cv_r2": ml["cv_r2_pooled"],
            "nonzero_genes": ml["n_nonzero_genes"],
            "overlap_gwas": ml["n_genes_overlapping_gwas"],
            "top_genes": top_genes,
        }

    return payload


def build_specificity(disease_codes: list[str]) -> dict:
    matrix_df = pd.read_csv(PROJECT_ROOT / "results" / "tables" / "specificity_matrix.csv", index_col=0)
    full_name_order = [DISEASE_CODES_REVERSE[c] for c in disease_codes]
    return {
        "rows": disease_codes,
        "cols": disease_codes,
        "matrix": matrix_df.loc[full_name_order, full_name_order].to_numpy().tolist(),
    }


def build_colormap_domains(diseases: dict) -> dict:
    """Symmetric domains computed from the REAL data range, not the
    illustrative placeholder numbers in Frontend.md §9's example ([-2.5,2.5]
    for signature) — our score is a MEAN of z-scored genes (CLAUDE.md §7.3),
    which has a far tighter real range (~+/-0.35) than a single gene's raw
    z-score. Using the example's literal domain would wash the colormap out
    to near-white for every real value. Computed 2026-09-11: max abs
    signature across all 3 diseases = 0.355 -> domain +/-0.4; max abs
    atrophy across PD+SCZ (AD has none) = 0.536 -> domain +/-0.6.
    """
    max_sig = max(max(abs(r["signature"]) for r in d["regions"]) for d in diseases.values())
    max_atr = max(
        (abs(r["atrophy"]) for d in diseases.values() for r in d["regions"] if r["atrophy"] is not None),
        default=0.1,
    )
    sig_domain = round(max_sig + 0.05, 1)
    atr_domain = round(max_atr + 0.05, 1)
    return {
        "signature": {"type": "diverging", "domain": [-sig_domain, sig_domain], "units": "mean z"},
        "atrophy": {"type": "diverging", "domain": [-atr_domain, atr_domain], "units": "Cohen's d"},
    }


def export_fallback_schematics(sig_domain: float, save: bool = True) -> None:
    """Per-disease 2D lateral+superior PNGs for the no-WebGL fallback state
    (Frontend.md §12 — "a designed 2D experience, not a banner")."""
    atlas_surf = fetch_dk_atlas(surface=True)
    lh_annot, rh_annot = atlas_surf["image"]

    for disease, prefix in DISEASE_PREFIX.items():
        score = pd.read_csv(PROCESSED / f"{prefix}_score_map_full.csv", index_col=0)["score"]
        code = DISEASE_CODES[disease].lower()
        plot_2d_fallback_schematic(
            score, lh_annot, rh_annot, DISEASE_LABELS[DISEASE_CODES[disease]], vmax=sig_domain,
            save_path=WEB_ASSETS / f"fallback_{code}.png" if save else None,
        )
    if save:
        print(f"Saved 3 fallback schematics to {WEB_ASSETS}")


def export_all(save: bool = True) -> dict:
    atlas = fetch_dk_atlas()
    atlas_info = pd.read_csv(atlas["info"])
    expression = pd.read_csv(INTERIM / "expression_matrix.csv", index_col=0)
    expression.index = expression.index.astype(int)

    diseases = {
        DISEASE_CODES[d]: build_disease_payload(d, atlas_info, expression)
        for d in ["parkinsons", "schizophrenia", "alzheimers"]
    }

    colormaps = build_colormap_domains(diseases)

    payload = {
        "meta": {"atlas": "desikan-killiany", "n_regions": len(atlas_info), "generated": "2026-09-11"},
        "colormaps": colormaps,
        "diseases": diseases,
        "specificity": build_specificity(["PD", "SCZ", "AD"]),
        "assets": {
            "mesh_pial": ["/assets/dk_pial_lh.gii", "/assets/dk_pial_rh.gii"],
            "mesh_inflated": ["/assets/dk_inflated_lh.gii", "/assets/dk_inflated_rh.gii"],
            "atlas_labels": ["/assets/dk_labels_lh.gii", "/assets/dk_labels_rh.gii"],
            "region_index": "/assets/dk_region_index.json",
            "fallback_2d": {
                "PD": "/assets/fallback_pd.png",
                "SCZ": "/assets/fallback_scz.png",
                "AD": "/assets/fallback_ad.png",
            },
        },
    }

    region_index = build_region_index(atlas_info)

    if save:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        WEB_ASSETS.mkdir(parents=True, exist_ok=True)
        with open(WEB_DATA / "signature.json", "w") as f:
            json.dump(payload, f)
        with open(WEB_ASSETS / "dk_region_index.json", "w") as f:
            json.dump(region_index, f, indent=2)
        print(f"Saved signature.json ({len(atlas_info)} regions x 3 diseases) and dk_region_index.json")

    prepare_mesh_assets(save=save)
    export_fallback_schematics(sig_domain=colormaps["signature"]["domain"][1], save=save)

    return {"signature": payload, "region_index": region_index}


if __name__ == "__main__":
    export_all()
