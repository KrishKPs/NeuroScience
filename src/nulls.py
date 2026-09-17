"""Null models — the scientific core. Two
complementary nulls, both required before any correlation is reported:

(a) Gene-set null: is the REAL gene set special vs. random gene sets of the
    same size? Controls for set size / expression structure.
(b) Spatial null: does the correlation survive once spatial autocorrelation
    (nearby regions looking alike) is accounted for? A naive p-value on brain
    maps is almost always too optimistic without this.
    - Cortical regions -> spin test (alexander_bloch): rotates the map on a
      sphere, which is only meaningful for a cortical surface.
    - Subcortical regions (our PD basal-ganglia proxy) have no sphere to spin
      -> variogram-matched surrogates (Burt et al. 2020) built directly from a
      volumetric distance matrix instead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.score import region_score, zscore_genes


def _empirical_p(real_stat: float, null_stats: np.ndarray, two_sided: bool = True) -> float:
    """Two-sided empirical p-value with the standard +1/+1 continuity correction
    (avoids p=0, which is never truly justified with a finite number of draws).
    """
    if two_sided:
        exceed = np.sum(np.abs(null_stats) >= np.abs(real_stat))
    else:
        exceed = np.sum(null_stats >= real_stat)
    return (exceed + 1) / (len(null_stats) + 1)


def gene_set_null(
    expression: pd.DataFrame,
    real_gene_set: list[str],
    atrophy_map: pd.Series,
    method: str = "mean",
    n_perm: int = 10000,
    seed: int = 1234,
) -> dict:
    """(a) Gene-set null. Draws `n_perm` random gene sets of the same size as
    `real_gene_set` (after reconciliation) from the full AHBA gene pool,
    scores each, correlates with `atrophy_map`, and returns where the real
    correlation falls in that null distribution.
    """
    present = [g for g in real_gene_set if g in expression.columns]
    k = len(present)
    if k == 0:
        raise ValueError("none of the real gene set's genes are present in the expression matrix")

    common_regions = expression.index.intersection(atrophy_map.index)
    if len(common_regions) < 3:
        raise ValueError(f"only {len(common_regions)} regions in common between expression and atrophy map")

    z = zscore_genes(expression)
    z_common = z.loc[common_regions]
    atro = atrophy_map.loc[common_regions].to_numpy()

    real_score = region_score(expression, present, method=method).loc[common_regions]
    real_r = np.corrcoef(real_score.to_numpy(), atro)[0, 1]

    rng = np.random.default_rng(seed)
    Z = z_common.to_numpy()
    n_genes = Z.shape[1]
    agg = np.mean if method == "mean" else np.median

    null_r = np.empty(n_perm)
    for i in range(n_perm):
        idx = rng.choice(n_genes, size=k, replace=False)
        s = agg(Z[:, idx], axis=1)
        null_r[i] = np.corrcoef(s, atro)[0, 1]

    p_value = _empirical_p(real_r, null_r)

    return {
        "real_r": real_r,
        "null_r": null_r,
        "p_value": p_value,
        "n_perm": n_perm,
        "gene_set_size": k,
        "n_regions": len(common_regions),
    }


def subcortical_variogram_null(
    score_map: pd.Series,
    atrophy_map: pd.Series,
    coords: pd.DataFrame,
    n_perm: int = 10000,
    seed: int = 1234,
) -> dict:
    """(b) Spatial null for SUBCORTICAL regions — no cortical surface exists to
    spin, so we generate variogram-matched surrogates (Burt et al. 2020) of
    `score_map` directly from a volumetric distance matrix, via brainsmash
    (the library neuromaps.nulls.burt2020 itself requires and wraps).

    We call brainsmash directly rather than neuromaps.nulls.burt2020 because
    that wrapper's volumetric path expects data embedded in neuromaps' own
    MNI152 reference volume — the wrong tool for a handful of DK subcortical
    parcels with their own centroid coordinates.

    `coords` must be indexed the same way as score_map/atrophy_map, with
    columns ['x', 'y', 'z'] (world/MNI space) — see
    src.data_load.get_region_centroids.
    """
    from brainsmash.mapgen.base import Base
    from scipy.spatial.distance import cdist

    common = score_map.index.intersection(atrophy_map.index).intersection(coords.index)
    if len(common) < 3:
        raise ValueError(f"only {len(common)} regions in common across score/atrophy/coords")

    x = score_map.loc[common].to_numpy().astype(float)
    y = atrophy_map.loc[common].to_numpy().astype(float)
    xyz = coords.loc[common][["x", "y", "z"]].to_numpy()
    D = cdist(xyz, xyz)

    real_r = np.corrcoef(x, y)[0, 1]

    base = Base(x=x, D=D, seed=seed)
    surrogates = base(n=n_perm)  # shape (n_perm, N)

    null_r = np.array([np.corrcoef(surrogates[i], y)[0, 1] for i in range(n_perm)])
    p_value = _empirical_p(real_r, null_r)

    return {
        "real_r": real_r,
        "null_r": null_r,
        "p_value": p_value,
        "n_perm": n_perm,
        "n_regions": len(common),
    }


def cortical_spin_null(
    score_map: pd.Series,
    atrophy_map: pd.Series,
    lh_annot,
    rh_annot,
    n_perm: int = 10000,
    seed: int = 1234,
    density: str = "10k",
) -> dict:
    """(b) Spatial null for CORTICAL regions — the Alexander-Bloch spin test,
    exactly as specified. Used for schizophrenia (Week 4),
    NOT for PD's subcortical proxy (see subcortical_variogram_null above).
    Untested until Week 4 wires in real DK->fsaverage annot files.
    """
    from neuromaps import nulls, stats

    common = score_map.index.intersection(atrophy_map.index)
    x = score_map.loc[common].to_numpy()
    y = atrophy_map.loc[common].to_numpy()

    rotated = nulls.alexander_bloch(
        x, atlas="fsaverage", density=density,
        parcellation=(lh_annot, rh_annot), n_perm=n_perm, seed=seed,
    )
    real_r, p_value, null_r = stats.compare_images(
        x, y, nulls=rotated, metric="pearsonr", return_nulls=True,
    )

    return {
        "real_r": real_r, "null_r": null_r, "p_value": p_value,
        "n_perm": n_perm, "n_regions": len(common),
    }
