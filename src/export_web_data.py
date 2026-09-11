"""Export the finished analysis to browser-consumable JSON for the web viewer
(CLAUDE.md §17). Pure read + reshape of already-committed pipeline outputs —
no new numbers get computed here except genes_top_contributors, which reuses
score.zscore_genes directly so it stays provably consistent with the region
scores already shown elsewhere.
"""
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from src.data_load import fetch_dk_atlas, get_region_centroids
from src.harmonize import reconcile_genes
from src.score import zscore_genes

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTERIM = PROJECT_ROOT / "data" / "interim"
PROCESSED = PROJECT_ROOT / "data" / "processed"
WEB_DATA = PROJECT_ROOT / "web" / "public" / "data"

DISEASES = ["parkinsons", "schizophrenia", "alzheimers"]
DISEASE_PREFIX = {"parkinsons": "pd", "schizophrenia": "scz", "alzheimers": "ad"}


def export_mesh(save: bool = True) -> dict:
    """Merged (both hemispheres) cortical surface geometry, JSON typed arrays
    (not glTF — see CLAUDE.md §17 for why). Built from the same GIFTI files
    src/figures.py::project_scores_to_surface uses for the static hero figure.
    """
    atlas_surf = fetch_dk_atlas(surface=True)
    lh_annot, rh_annot = atlas_surf["image"]

    abagen_data = Path(__import__("abagen").__file__).parent / "data"
    lh_mesh = abagen_data / "fsaverage5-pial-lh.surf.gii.gz"
    rh_mesh = abagen_data / "fsaverage5-pial-rh.surf.gii.gz"

    lh_verts, lh_faces = nib.load(lh_mesh).agg_data()
    rh_verts, rh_faces = nib.load(rh_mesh).agg_data()
    lh_labels = nib.load(lh_annot).agg_data().astype(int)
    rh_labels = nib.load(rh_annot).agg_data().astype(int)

    n_lh = lh_verts.shape[0]
    vertices = np.vstack([lh_verts, rh_verts]).astype(np.float32)
    faces = np.vstack([lh_faces, rh_faces + n_lh]).astype(np.int32)
    vertex_region_id = np.concatenate([lh_labels, rh_labels]).astype(int)

    mesh = {
        "_provenance": {
            "source": "abagen fsaverage5-pial-{lh,rh}.surf.gii.gz + atlas-desikankilliany-{lh,rh}.label.gii.gz",
            "n_vertices_per_hemi": int(n_lh),
        },
        "vertices": vertices.flatten().tolist(),
        "faces": faces.flatten().tolist(),
        "vertex_region_id": vertex_region_id.tolist(),
    }

    if save:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        with open(WEB_DATA / "mesh.json", "w") as f:
            json.dump(mesh, f)
        print(f"Saved mesh.json: {len(mesh['vertices'])//3} vertices, {len(mesh['faces'])//3} faces")

    return mesh


def export_regions(save: bool = True) -> dict:
    """One object per region id: atlas info + real MNI centroid + all three
    disease scores + whichever atrophy value exists for that region/disease.
    """
    atlas = fetch_dk_atlas()
    atlas_info = pd.read_csv(atlas["info"]).set_index("id")
    coords = get_region_centroids(atlas)

    scores = {}
    for disease in DISEASES:
        prefix = DISEASE_PREFIX[disease]
        path = PROCESSED / f"{prefix}_score_map_full.csv"
        scores[disease] = pd.read_csv(path, index_col=0)["score"]

    atrophy = {"parkinsons": {}, "schizophrenia": {}, "alzheimers": {}}
    pd_atrophy = pd.read_csv(PROCESSED / "pd_subcortex_atrophy_map.csv", index_col=0)["atrophy_d"]
    scz_atrophy = pd.read_csv(PROCESSED / "scz_cortex_atrophy_map.csv", index_col=0)["atrophy_d"]
    atrophy["parkinsons"] = pd_atrophy.to_dict()
    atrophy["schizophrenia"] = scz_atrophy.to_dict()
    # No continuous ENIGMA ground truth for AD (CLAUDE.md §16) — every region is null.

    regions = {}
    for region_id, row in atlas_info.iterrows():
        rid = int(region_id)
        c = coords.loc[rid]
        regions[str(rid)] = {
            "id": rid,
            "label": row["label"],
            "hemisphere": row["hemisphere"],
            "structure": row["structure"],
            "is_cortical": row["structure"] == "cortex",
            "x": float(c["x"]), "y": float(c["y"]), "z": float(c["z"]),
            "scores": {d: float(scores[d].get(rid, float("nan"))) for d in DISEASES},
            "atrophy": {d: atrophy[d].get(rid) for d in DISEASES},
        }

    payload = {
        "_meta": {"n_regions": len(regions), "atlas": "desikan_killiany", "seed": 1234},
        "regions": regions,
    }

    if save:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        with open(WEB_DATA / "regions.json", "w") as f:
            json.dump(payload, f)
        print(f"Saved regions.json: {len(regions)} regions")

    return payload


def export_validation_summary(save: bool = True) -> dict:
    """Copy-through merge of the three *_validation_summary.json files plus
    pd_ml_summary.json — no new numbers, just one fetch instead of four."""
    summary = {}
    for disease in DISEASES:
        prefix = DISEASE_PREFIX[disease]
        with open(PROCESSED / f"{prefix}_validation_summary.json") as f:
            summary[disease] = json.load(f)

    with open(PROCESSED / "pd_ml_summary.json") as f:
        summary["parkinsons"]["ml_layer"] = json.load(f)

    if save:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        with open(WEB_DATA / "validation_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print("Saved validation_summary.json")

    return summary


def export_specificity_matrix(save: bool = True) -> dict:
    matrix_df = pd.read_csv(PROJECT_ROOT / "results" / "tables" / "specificity_matrix.csv", index_col=0)
    payload = {
        "diseases": matrix_df.index.tolist(),
        "atrophy_maps": matrix_df.columns.tolist(),
        "matrix": matrix_df.to_numpy().tolist(),
    }

    if save:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        with open(WEB_DATA / "specificity_matrix.json", "w") as f:
            json.dump(payload, f, indent=2)
        print("Saved specificity_matrix.json")

    return payload


def _matched_genes_for(disease: str, expression: pd.DataFrame) -> list[str]:
    prefix = DISEASE_PREFIX[disease]
    if disease == "parkinsons":
        return pd.read_csv(INTERIM / "pd_matched_genes.csv")["gene"].tolist()
    risk_genes = pd.read_csv(INTERIM / f"{prefix}_gwas_risk_genes.csv")
    result = reconcile_genes(risk_genes, expression)
    return result["matched"]


def export_genes_top_contributors(save: bool = True, top_n: int = 5) -> dict:
    """Top-N genes per region per disease, by z-scored expression within that
    disease's matched GWAS gene set — reuses score.zscore_genes directly so
    these numbers stay consistent with the displayed region score.
    """
    expression = pd.read_csv(INTERIM / "expression_matrix.csv", index_col=0)
    expression.index = expression.index.astype(int)
    z = zscore_genes(expression)

    ml_nonzero_genes = set(pd.read_csv(PROCESSED / "pd_ml_nonzero_genes.csv", index_col=0).index)

    payload = {}
    for disease in DISEASES:
        matched = _matched_genes_for(disease, expression)
        present = [g for g in matched if g in z.columns]
        sub = z[present]

        disease_payload = {}
        for region_id, row in sub.iterrows():
            top = row.sort_values(ascending=False).head(top_n)
            disease_payload[str(int(region_id))] = [
                {
                    "gene": gene,
                    "z": float(val),
                    **({"in_ml_nonzero": True} if disease == "parkinsons" and gene in ml_nonzero_genes else {}),
                }
                for gene, val in top.items()
            ]
        payload[disease] = disease_payload

    if save:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        with open(WEB_DATA / "genes_top_contributors.json", "w") as f:
            json.dump(payload, f)
        print("Saved genes_top_contributors.json")

    return payload


def export_all(save: bool = True) -> dict:
    return {
        "mesh": export_mesh(save=save),
        "regions": export_regions(save=save),
        "validation_summary": export_validation_summary(save=save),
        "specificity_matrix": export_specificity_matrix(save=save),
        "genes_top_contributors": export_genes_top_contributors(save=save),
    }


if __name__ == "__main__":
    export_all()
