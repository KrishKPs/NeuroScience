"""One-command pipeline: regenerates all processed data / figures from raw
inputs.
Grows week by week; each `run_weekN_*` function is independently callable.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_load import fetch_dk_atlas, get_region_centroids, load_config
from src.validate import (
    validate_pd, validate_scz, validate_ad, ad_vulnerable_region_indicator,
    whole_brain_atrophy_map,
)
from src.specificity import build_specificity_matrix
from src.figures import plot_hero_figure, plot_specificity_matrix, plot_validation_scatter
from src.model import run_elasticnet_cv, genes_overlapping_gwas
from src.export_web_data import export_all as export_web_data

PROJECT_ROOT = Path(__file__).resolve().parent
INTERIM = PROJECT_ROOT / "data" / "interim"
PROCESSED = PROJECT_ROOT / "data" / "processed"
RESULTS_FIGURES = PROJECT_ROOT / "results" / "figures"
RESULTS_TABLES = PROJECT_ROOT / "results" / "tables"


def run_week3_pd_validation(save: bool = True) -> dict:
    """Score map + BOTH null models for the primary disease (Parkinson's).
    the hard gate before Week 4 starts.
    """
    cfg = load_config()
    seed = cfg["seed"]
    n_perm = cfg["nulls"]["spatial_n_perm"]
    method = cfg["scoring"]["method"]

    expr = pd.read_csv(INTERIM / "expression_matrix.csv", index_col=0)
    expr.index = expr.index.astype(int)

    pd_genes = pd.read_csv(INTERIM / "pd_gwas_risk_genes.csv")["gene"].tolist()

    atlas = fetch_dk_atlas()
    atlas_info = pd.read_csv(atlas["info"])
    coords = get_region_centroids(atlas)
    enigma_subvol = pd.read_csv(INTERIM / "enigma_pd_Subvol_PDvsCN.csv")

    result = validate_pd(
        expression=expr, pd_risk_genes=pd_genes, enigma_subvol_pdvscn=enigma_subvol,
        atlas_info=atlas_info, coords=coords, method=method, n_perm=n_perm, seed=seed,
    )

    if save:
        PROCESSED.mkdir(parents=True, exist_ok=True)
        result["score_map_full"].to_csv(PROCESSED / "pd_score_map_full.csv", header=["score"])
        result["atrophy_map"].to_csv(PROCESSED / "pd_subcortex_atrophy_map.csv", header=["atrophy_d"])
        np.save(PROCESSED / "pd_gene_set_null_distribution.npy", result["gene_set_null"]["null_r"])
        np.save(PROCESSED / "pd_spatial_null_distribution.npy", result["spatial_null"]["null_r"])

        summary = {
            "disease": "parkinsons",
            "method": result["method"],
            "n_perm": result["n_perm"],
            "seed": result["seed"],
            "real_r_subcortex_n14": float(result["real_r"]),
            "basal_ganglia_proxy_r_n6_descriptive_only": float(result["basal_ganglia_proxy_r_descriptive_only"]),
            "gene_set_null_p": float(result["gene_set_null"]["p_value"]),
            "gene_set_null_gene_set_size": result["gene_set_null"]["gene_set_size"],
            "spatial_null_p": float(result["spatial_null"]["p_value"]),
            "spatial_null_type": "burt2020_variogram_subcortex_n14",
            "n_regions": result["gene_set_null"]["n_regions"],
        }
        with open(PROCESSED / "pd_validation_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("Saved Week 3 PD validation outputs to", PROCESSED)
        print(json.dumps(summary, indent=2))

    return result


def run_week4_scz_validation(save: bool = True) -> dict:
    """Score map + gene-set null + cortical spin test for schizophrenia.
    Cortical target -> spin test.
    """
    cfg = load_config()
    seed = cfg["seed"]
    n_perm = cfg["nulls"]["spatial_n_perm"]
    method = cfg["scoring"]["method"]

    expr = pd.read_csv(INTERIM / "expression_matrix.csv", index_col=0)
    expr.index = expr.index.astype(int)
    scz_genes = pd.read_csv(INTERIM / "scz_gwas_risk_genes.csv")["gene"].tolist()

    atlas = fetch_dk_atlas()
    atlas_info = pd.read_csv(atlas["info"])
    atlas_surf = fetch_dk_atlas(surface=True)
    lh_annot, rh_annot = atlas_surf["image"]
    enigma_ct = pd.read_csv(INTERIM / "enigma_scz_CortThick_case_vs_controls.csv")

    result = validate_scz(
        expression=expr, scz_risk_genes=scz_genes, enigma_cortthick_df=enigma_ct,
        atlas_info=atlas_info, lh_annot=lh_annot, rh_annot=rh_annot,
        method=method, n_perm=n_perm, seed=seed,
    )

    if save:
        PROCESSED.mkdir(parents=True, exist_ok=True)
        result["score_map_full"].to_csv(PROCESSED / "scz_score_map_full.csv", header=["score"])
        result["atrophy_map"].to_csv(PROCESSED / "scz_cortex_atrophy_map.csv", header=["atrophy_d"])
        np.save(PROCESSED / "scz_gene_set_null_distribution.npy", result["gene_set_null"]["null_r"])
        np.save(PROCESSED / "scz_spatial_null_distribution.npy", result["spatial_null"]["null_r"])

        summary = {
            "disease": "schizophrenia",
            "method": result["method"],
            "n_perm": result["n_perm"],
            "seed": result["seed"],
            "real_r_cortex_n68": float(result["real_r"]),
            "gene_set_null_p": float(result["gene_set_null"]["p_value"]),
            "gene_set_null_gene_set_size": result["gene_set_null"]["gene_set_size"],
            "spatial_null_p": float(result["spatial_null"]["p_value"]),
            "spatial_null_type": "alexander_bloch_spin_cortex_n68",
            "n_regions": result["gene_set_null"]["n_regions"],
        }
        with open(PROCESSED / "scz_validation_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("Saved Week 4 SCZ validation outputs to", PROCESSED)
        print(json.dumps(summary, indent=2))

    return result


def run_week4_ad_validation(save: bool = True) -> dict:
    """Score map + fallback ROI-based validation for Alzheimer's (no ENIGMA
    ground truth available — see src/validate.py docstrings).
    """
    cfg = load_config()
    seed = cfg["seed"]
    n_perm = cfg["nulls"]["spatial_n_perm"]
    method = cfg["scoring"]["method"]

    expr = pd.read_csv(INTERIM / "expression_matrix.csv", index_col=0)
    expr.index = expr.index.astype(int)
    ad_genes = pd.read_csv(INTERIM / "ad_gwas_risk_genes.csv")["gene"].tolist()

    atlas = fetch_dk_atlas()
    atlas_info = pd.read_csv(atlas["info"])
    coords = get_region_centroids(atlas)

    result = validate_ad(
        expression=expr, ad_risk_genes=ad_genes, atlas_info=atlas_info, coords=coords,
        method=method, n_perm=n_perm, seed=seed,
    )

    if save:
        PROCESSED.mkdir(parents=True, exist_ok=True)
        result["score_map_full"].to_csv(PROCESSED / "ad_score_map_full.csv", header=["score"])
        np.save(PROCESSED / "ad_gene_set_null_distribution.npy", result["gene_set_null"]["null_r"])
        np.save(
            PROCESSED / "ad_approx_spatial_null_distribution.npy",
            result["approx_whole_brain_spatial_null"]["null_r"],
        )

        summary = {
            "disease": "alzheimers",
            "method": result["method"],
            "n_perm": result["n_perm"],
            "seed": result["seed"],
            "ground_truth": "fallback_canonical_roi_list (no ENIGMA AD map available)",
            "real_r_vs_vulnerable_roi_n83": float(result["real_r"]),
            "gene_set_null_p": float(result["gene_set_null"]["p_value"]),
            "gene_set_null_gene_set_size": result["gene_set_null"]["gene_set_size"],
            "approx_spatial_null_p": float(result["approx_whole_brain_spatial_null"]["p_value"]),
            "approx_spatial_null_type": "brainsmash_variogram_whole_brain_n83_APPROXIMATE",
            "n_regions": result["gene_set_null"]["n_regions"],
            "note": "not significant at alpha=0.05 under either null; reported honestly",
        }
        with open(PROCESSED / "ad_validation_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("Saved Week 4 AD validation outputs to", PROCESSED)
        print(json.dumps(summary, indent=2))

    return result


def run_week4_figures(pd_result: dict, scz_result: dict, ad_result: dict, save: bool = True) -> dict:
    """Hero figure (3 signature maps) + specificity matrix."""
    RESULTS_FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS_TABLES.mkdir(parents=True, exist_ok=True)

    atlas_surf = fetch_dk_atlas(surface=True)
    lh_annot, rh_annot = atlas_surf["image"]

    score_maps = {
        "parkinsons": pd_result["score_map_full"],
        "schizophrenia": scz_result["score_map_full"],
        "alzheimers": ad_result["score_map_full"],
    }
    hero_fig = plot_hero_figure(
        score_maps, lh_annot, rh_annot,
        save_path=RESULTS_FIGURES / "hero_signature_maps.png" if save else None,
    )

    atlas = fetch_dk_atlas()
    atlas_info = pd.read_csv(atlas["info"])
    atrophy_maps = {
        "parkinsons": pd_result["atrophy_map"],
        "schizophrenia": scz_result["atrophy_map"],
        "alzheimers": ad_vulnerable_region_indicator(atlas_info),
    }
    corr_matrix = build_specificity_matrix(score_maps, atrophy_maps)
    spec_fig = plot_specificity_matrix(
        corr_matrix, save_path=RESULTS_FIGURES / "specificity_matrix.png" if save else None,
    )

    if save:
        corr_matrix.to_csv(RESULTS_TABLES / "specificity_matrix.csv")
        print("Saved hero + specificity figures to", RESULTS_FIGURES)
        print("Specificity matrix:")
        print(corr_matrix.round(3))

    return {"hero_fig": hero_fig, "spec_fig": spec_fig, "corr_matrix": corr_matrix}


def run_week5_ml_layer(save: bool = True) -> dict:
    """ElasticNet regression predicting PD's whole-brain atrophy map from
    regional expression, plus GWAS-overlap check."""
    cfg = load_config()
    seed = cfg["seed"]

    expr = pd.read_csv(INTERIM / "expression_matrix.csv", index_col=0)
    expr.index = expr.index.astype(int)

    atlas = fetch_dk_atlas()
    atlas_info = pd.read_csv(atlas["info"])
    enigma_ct = pd.read_csv(INTERIM / "enigma_pd_CortThick_PDvsCN.csv")
    enigma_sv = pd.read_csv(INTERIM / "enigma_pd_Subvol_PDvsCN.csv")
    atrophy = whole_brain_atrophy_map(enigma_ct, enigma_sv, atlas_info)

    result = run_elasticnet_cv(expr, atrophy, n_folds=5, seed=seed)

    pd_genes = pd.read_csv(INTERIM / "pd_gwas_risk_genes.csv")["gene"].tolist()
    overlap = genes_overlapping_gwas(result["nonzero_genes"], pd_genes)

    if save:
        PROCESSED.mkdir(parents=True, exist_ok=True)
        result["nonzero_genes"].to_csv(PROCESSED / "pd_ml_nonzero_genes.csv", header=["coef"])
        overlap.to_csv(PROCESSED / "pd_ml_genes_overlapping_gwas.csv", header=["coef"])
        pd.DataFrame({
            "region_id": result["y_true"].index,
            "atrophy_true": result["y_true"].to_numpy(),
            "atrophy_pred_cv": result["y_pred_cv"].to_numpy(),
        }).to_csv(PROCESSED / "pd_ml_cv_predictions.csv", index=False)

        summary = {
            "disease": "parkinsons",
            "n_regions": result["n_regions"],
            "n_folds": result["n_folds"],
            "cv_r2_pooled": result["cv_r2_pooled"],
            "cv_r2_per_fold": result["cv_r2_per_fold"],
            "final_model_alpha": result["final_model_alpha"],
            "final_model_l1_ratio": result["final_model_l1_ratio"],
            "n_nonzero_genes": result["n_nonzero_genes"],
            "n_genes_overlapping_gwas": len(overlap),
            "note": "83 samples (here 82) x ~15,600 features — exploratory/interpretability framing, not an accuracy claim",
        }
        with open(PROCESSED / "pd_ml_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("Saved Week 5 ML layer outputs to", PROCESSED)
        print(json.dumps(summary, indent=2))
        print("Genes overlapping GWAS risk set:")
        print(overlap)

    return {**result, "genes_overlapping_gwas": overlap}


def run_week5_validation_figures(pd_result: dict, scz_result: dict, save: bool = True) -> dict:
    """Validation figure: score vs. ENIGMA atrophy scatter
    with the spatial null's p-value annotated, for PD and SCZ (both have real
    continuous ENIGMA ground truth; AD's fallback ROI indicator isn't a
    continuous atrophy map, so it doesn't get this scatter)."""
    RESULTS_FIGURES.mkdir(parents=True, exist_ok=True)

    pd_summary_path = PROCESSED / "pd_validation_summary.json"
    scz_summary_path = PROCESSED / "scz_validation_summary.json"
    with open(pd_summary_path) as f:
        pd_summary = json.load(f)
    with open(scz_summary_path) as f:
        scz_summary = json.load(f)

    pd_fig = plot_validation_scatter(
        pd_result["score_map_subcortex"], pd_result["atrophy_map"],
        title="Parkinson's: expression signature vs. subcortical atrophy",
        p_value=pd_summary["spatial_null_p"], null_type="variogram",
        save_path=RESULTS_FIGURES / "validation_pd.png" if save else None,
    )
    scz_fig = plot_validation_scatter(
        scz_result["score_map_cortex"], scz_result["atrophy_map"],
        title="Schizophrenia: expression signature vs. cortical atrophy",
        p_value=scz_summary["spatial_null_p"], null_type="spin",
        save_path=RESULTS_FIGURES / "validation_scz.png" if save else None,
    )

    if save:
        print("Saved validation figures to", RESULTS_FIGURES)

    return {"pd_fig": pd_fig, "scz_fig": scz_fig}


def run_week7_export_web_data(save: bool = True) -> dict:
    """Export the finished analysis to web/public/{data,assets}/ per the
    frontend's data contract.
    Requires Weeks 3-5's outputs to already exist in data/processed/ and
    results/tables/."""
    result = export_web_data(save=save)
    if save:
        print("Exported web viewer data to web/public/data/ and web/public/assets/")
    return result


if __name__ == "__main__":
    pd_result = run_week3_pd_validation()
    scz_result = run_week4_scz_validation()
    ad_result = run_week4_ad_validation()
    run_week4_figures(pd_result, scz_result, ad_result)
    run_week5_ml_layer()
    run_week5_validation_figures(pd_result, scz_result)
    run_week7_export_web_data()
