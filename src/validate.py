"""Validate a disease's expression score map against its ENIGMA atrophy ground
truth (CLAUDE.md §7.5), running BOTH required null models (§7.4) — never
report a correlation without them.
"""
from __future__ import annotations

import pandas as pd

from src.nulls import gene_set_null, subcortical_variogram_null, cortical_spin_null
from src.score import region_score


# DK subcortical labels that ENIGMA's SubcorticalVolume tables also cover (excludes
# lateral ventricles, which ENIGMA includes but which aren't a gray-matter DK region).
SUBCORTICAL_LABEL_MAP = {
    ("L", "accumbensarea"): "Laccumb", ("R", "accumbensarea"): "Raccumb",
    ("L", "amygdala"): "Lamyg", ("R", "amygdala"): "Ramyg",
    ("L", "caudate"): "Lcaud", ("R", "caudate"): "Rcaud",
    ("L", "hippocampus"): "Lhippo", ("R", "hippocampus"): "Rhippo",
    ("L", "pallidum"): "Lpal", ("R", "pallidum"): "Rpal",
    ("L", "putamen"): "Lput", ("R", "putamen"): "Rput",
    ("L", "thalamusproper"): "Lthal", ("R", "thalamusproper"): "Rthal",
}

# The PD-specific hypothesis: substantia nigra isn't in DK, so we proxy it with the
# basal ganglia (caudate/putamen/pallidum, bilateral). See CLAUDE.md §3/§16.
PD_PROXY_LABELS = {"caudate", "putamen", "pallidum"}


def subcortical_atrophy_map(enigma_subvol_df: pd.DataFrame, atlas_info: pd.DataFrame) -> pd.Series:
    """Map an ENIGMA SubcorticalVolume table's Structure names onto DK atlas
    region ids, for every subcortical gray-matter structure both datasets
    share (14 regions: 7 bilateral). Returns Cohen's d (d_icv), indexed by
    atlas region id, matching the expression matrix's index.

    We validate across the FULL subcortex rather than only the 3-structure
    basal-ganglia proxy because brainsmash's variogram fit (the spatial null,
    §7.4b) needs more spatial points than N=6 can support — it errors
    building its neighbor bins with a `ValueError: zero-size array` at N=6.
    N=14 is still small but usable. This is a deviation from a literal
    "basal-ganglia-only" reading of CLAUDE.md §3 — logged in §16. The
    basal-ganglia subset remains the specific hypothesis of interest and is
    reported separately as a descriptive (non-null-tested) number.
    """
    rows = atlas_info[atlas_info["label"].isin({lbl for _, lbl in SUBCORTICAL_LABEL_MAP})]
    struct_to_d = enigma_subvol_df.set_index("Structure")["d_icv"]

    id_to_d = {}
    for _, row in rows.iterrows():
        struct = SUBCORTICAL_LABEL_MAP.get((row["hemisphere"], row["label"]))
        if struct is not None and struct in struct_to_d.index:
            id_to_d[row["id"]] = struct_to_d[struct]

    if len(id_to_d) != 14:
        raise ValueError(f"expected 14 matched subcortical regions, mapped {len(id_to_d)}")

    return pd.Series(id_to_d, name="atrophy_d")


def pd_basal_ganglia_ids(atlas_info: pd.DataFrame) -> list[int]:
    """The 6 bilateral basal-ganglia region ids (PD's specific proxy target),
    as a subset of the 14 returned by subcortical_atrophy_map."""
    rows = atlas_info[atlas_info["label"].isin(PD_PROXY_LABELS)]
    return rows["id"].tolist()


def validate_pd(
    expression: pd.DataFrame,
    pd_risk_genes: list[str],
    enigma_subvol_pdvscn: pd.DataFrame,
    atlas_info: pd.DataFrame,
    coords: pd.DataFrame,
    method: str = "mean",
    n_perm: int = 10000,
    seed: int = 1234,
) -> dict:
    """Full Week 3 validation for the primary disease: score map, real
    correlation against the full-subcortex ENIGMA atrophy map (N=14, needed
    for the spatial null to be well-posed — see subcortical_atrophy_map's
    docstring), gene-set null, and subcortical variogram null (PD's proxy is
    subcortical -> NOT a spin test, see CLAUDE.md §7.4b / §16). Also reports
    the basal-ganglia-only (N=6) correlation as a descriptive number, without
    its own null (too few points for brainsmash's variogram fit).
    """
    atrophy_map = subcortical_atrophy_map(enigma_subvol_pdvscn, atlas_info)
    proxy_ids = pd_basal_ganglia_ids(atlas_info)

    score_map_full = region_score(expression, pd_risk_genes, method=method)
    score_map_subcortex = score_map_full.loc[atrophy_map.index]

    gs_null = gene_set_null(
        expression=expression, real_gene_set=pd_risk_genes, atrophy_map=atrophy_map,
        method=method, n_perm=n_perm, seed=seed,
    )
    spatial_null = subcortical_variogram_null(
        score_map=score_map_subcortex, atrophy_map=atrophy_map, coords=coords,
        n_perm=n_perm, seed=seed,
    )

    proxy_r = score_map_full.loc[proxy_ids].corr(atrophy_map.loc[proxy_ids])

    return {
        "score_map_full": score_map_full,
        "score_map_subcortex": score_map_subcortex,
        "atrophy_map": atrophy_map,
        "real_r": gs_null["real_r"],
        "gene_set_null": gs_null,
        "spatial_null": spatial_null,
        "basal_ganglia_proxy_r_descriptive_only": proxy_r,
        "method": method,
        "n_perm": n_perm,
        "seed": seed,
    }
