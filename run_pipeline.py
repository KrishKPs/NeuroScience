"""One-command pipeline: regenerates all processed data / figures from raw
inputs. See CLAUDE.md §8 (deliverable 5) and §11 ("one-command reproduce").
Grows week by week; each `run_weekN_*` function is independently callable.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_load import fetch_dk_atlas, get_region_centroids, load_config
from src.validate import validate_pd

PROJECT_ROOT = Path(__file__).resolve().parent
INTERIM = PROJECT_ROOT / "data" / "interim"
PROCESSED = PROJECT_ROOT / "data" / "processed"


def run_week3_pd_validation(save: bool = True) -> dict:
    """Score map + BOTH null models for the primary disease (Parkinson's).
    CLAUDE.md §7.3/§7.4 — the hard gate before Week 4 starts.
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


if __name__ == "__main__":
    run_week3_pd_validation()
