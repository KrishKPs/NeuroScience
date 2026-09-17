"""Validate a disease's expression score map against its ENIGMA atrophy ground
truth, running BOTH required null models — never
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
# basal ganglia (caudate/putamen/pallidum, bilateral).
PD_PROXY_LABELS = {"caudate", "putamen", "pallidum"}


def subcortical_atrophy_map(enigma_subvol_df: pd.DataFrame, atlas_info: pd.DataFrame) -> pd.Series:
    """Map an ENIGMA SubcorticalVolume table's Structure names onto DK atlas
    region ids, for every subcortical gray-matter structure both datasets
    share (14 regions: 7 bilateral). Returns Cohen's d (d_icv), indexed by
    atlas region id, matching the expression matrix's index.

    We validate across the FULL subcortex rather than only the 3-structure
    basal-ganglia proxy because brainsmash's variogram fit (the spatial null)
    needs more spatial points than N=6 can support — it errors
    building its neighbor bins with a `ValueError: zero-size array` at N=6.
    N=14 is still small but usable. This is a deviation from a literal
    "basal-ganglia-only" reading of the PD target, logged as a limitation. The
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
    subcortical -> NOT a spin test). Also reports
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


def whole_brain_atrophy_map(
    enigma_cortthick_df: pd.DataFrame,
    enigma_subvol_df: pd.DataFrame,
    atlas_info: pd.DataFrame,
) -> pd.Series:
    """Combine a disease's cortical-thickness (68 regions) and subcortical-
    volume (14 regions) ENIGMA Cohen's d tables into one whole-brain atrophy
    map (82 of 83 DK regions — everything except brainstem, which ENIGMA
    doesn't cover). Used for the ML layer, whose "83 samples" framing
    implies a whole-brain target, not the 14-region subcortical-only map used
    for PD's null-tested validation (validate_pd) or the 68-region
    cortical-only map used for SCZ's (validate_scz).
    """
    cortical = cortical_atrophy_map(enigma_cortthick_df, atlas_info)
    subcortical = subcortical_atrophy_map(enigma_subvol_df, atlas_info)
    combined = pd.concat([cortical, subcortical]).sort_index()
    if combined.index.duplicated().any():
        raise ValueError("unexpected overlap between cortical and subcortical region ids")
    return combined


def cortical_atrophy_map(enigma_cortthick_df: pd.DataFrame, atlas_info: pd.DataFrame) -> pd.Series:
    """Map an ENIGMA cortical-thickness table's `Structure` column
    (`{hemisphere}_{label}`, e.g. 'L_bankssts') onto DK atlas region ids for
    all 68 cortical regions. Returns Cohen's d (d_icv), indexed by atlas
    region id, matching the expression matrix's index. Used for
    schizophrenia (cortical target -> spin test).
    """
    cortex = atlas_info[atlas_info["structure"] == "cortex"].copy()
    cortex["structure_name"] = cortex["hemisphere"] + "_" + cortex["label"]

    struct_to_d = enigma_cortthick_df.set_index("Structure")["d_icv"]
    id_to_d = {
        row["id"]: struct_to_d[row["structure_name"]]
        for _, row in cortex.iterrows()
        if row["structure_name"] in struct_to_d.index
    }

    if len(id_to_d) != 68:
        raise ValueError(f"expected 68 matched cortical regions, mapped {len(id_to_d)}")

    return pd.Series(id_to_d, name="atrophy_d").sort_index()


def validate_scz(
    expression: pd.DataFrame,
    scz_risk_genes: list[str],
    enigma_cortthick_df: pd.DataFrame,
    atlas_info: pd.DataFrame,
    lh_annot,
    rh_annot,
    method: str = "mean",
    n_perm: int = 10000,
    seed: int = 1234,
) -> dict:
    """Full validation for schizophrenia: score map, real correlation against
    the ENIGMA cortical-thickness atrophy map (all 68 DK cortical regions),
    gene-set null, and the cortical spin test (Alexander-Bloch) — SCZ's
    target is fully cortical, so a spin test is the correct spatial null
    here (unlike PD's subcortical proxy, see validate_pd).

    `lh_annot`/`rh_annot` must be DK surface GIFTI label files
    (abagen.fetch_desikan_killiany(surface=True)['image']); alexander_bloch's
    expected data order is cortex regions sorted by ascending atlas id (L
    1-34 then R 42-75) — verified against neuromaps' get_parcel_centroids
    source, not assumed. `region_score`/`atrophy_map` here
    are naturally already in that order since atlas_info's `id` column sorts
    L-cortex (1-34) before R-cortex (42-75).
    """
    atrophy_map = cortical_atrophy_map(enigma_cortthick_df, atlas_info)

    score_map_full = region_score(expression, scz_risk_genes, method=method)
    score_map_cortex = score_map_full.loc[atrophy_map.index]

    gs_null = gene_set_null(
        expression=expression, real_gene_set=scz_risk_genes, atrophy_map=atrophy_map,
        method=method, n_perm=n_perm, seed=seed,
    )
    spatial_null = cortical_spin_null(
        score_map=score_map_cortex, atrophy_map=atrophy_map,
        lh_annot=lh_annot, rh_annot=rh_annot, n_perm=n_perm, seed=seed,
    )

    return {
        "score_map_full": score_map_full,
        "score_map_cortex": score_map_cortex,
        "atrophy_map": atrophy_map,
        "real_r": gs_null["real_r"],
        "gene_set_null": gs_null,
        "spatial_null": spatial_null,
        "method": method,
        "n_perm": n_perm,
        "seed": seed,
    }


# No ENIGMA case-control map exists for Alzheimer's in enigmatoolbox==2.0.3 (confirmed:
# 'alzheimers'/'ad' isn't in its valid disorder list). Fallback: a
# defensible canonical vulnerable-region list. AD's target spans both cortex
# (entorhinal) and subcortex (hippocampus, amygdala) — mixing compartments that no
# bundled null tool (spin test = cortex-only; burt2020/brainsmash = built for one
# geometric domain) cleanly supports together. See validate_ad's docstring for how
# this is handled and its limitation.
AD_CANONICAL_VULNERABLE_LABELS = {"entorhinal", "hippocampus", "amygdala"}


def ad_vulnerable_region_indicator(atlas_info: pd.DataFrame) -> pd.Series:
    """Binary indicator (1 = canonically AD-vulnerable, 0 = not), indexed by
    atlas region id, for all 83 DK regions."""
    ind = atlas_info["label"].isin(AD_CANONICAL_VULNERABLE_LABELS).astype(float)
    return pd.Series(ind.to_numpy(), index=atlas_info["id"], name="vulnerable")


def validate_ad(
    expression: pd.DataFrame,
    ad_risk_genes: list[str],
    atlas_info: pd.DataFrame,
    coords: pd.DataFrame,
    method: str = "mean",
    n_perm: int = 10000,
    seed: int = 1234,
) -> dict:
    """Fallback validation for Alzheimer's (no ENIGMA ground-truth map, see
    module-level note above): tests whether the AD score map is elevated in
    the canonical vulnerable ROI set (entorhinal, hippocampus, amygdala,
    bilateral) versus the rest of the brain.

    Two results, both reported, with different rigor:
    1. PRIMARY — gene-set null only. Compares the real correlation between
       score and ROI-membership against `n_perm` random gene sets of the same
       size. Well-posed regardless of spatial domain mixing, since the ROI
       set itself is held fixed (not spatially permuted).
    2. SECONDARY / APPROXIMATE — a whole-brain (83-region) variogram null via
       brainsmash, treating cortical region centroids the same way as
       subcortical ones (raw 3D Euclidean distance). This is a coarser
       approximation than the surface-geodesic spin test used for pure
       cortical targets (SCZ) — cortex isn't well modeled by 3D centroid
       distance — but no bundled tool handles a single null spanning both
       compartments. Flagged as a limitation, not hidden.
    """
    indicator = ad_vulnerable_region_indicator(atlas_info)
    score_map_full = region_score(expression, ad_risk_genes, method=method)

    gs_null = gene_set_null(
        expression=expression, real_gene_set=ad_risk_genes, atrophy_map=indicator,
        method=method, n_perm=n_perm, seed=seed,
    )
    approx_spatial_null = subcortical_variogram_null(
        score_map=score_map_full, atrophy_map=indicator, coords=coords,
        n_perm=n_perm, seed=seed,
    )

    return {
        "score_map_full": score_map_full,
        "vulnerable_indicator": indicator,
        "real_r": gs_null["real_r"],
        "gene_set_null": gs_null,
        "approx_whole_brain_spatial_null": approx_spatial_null,
        "method": method,
        "n_perm": n_perm,
        "seed": seed,
    }
