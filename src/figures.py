"""Hero / specificity / validation figures. CLAUDE.md §8.

Cortical scores are rendered on the fsaverage5 surface (bundled with abagen —
the same mesh underlying the DK surface parcellation used for the spin test).
We project region -> vertex ourselves with a direct raw-label lookup rather
than neuromaps.parcellate.parcels_to_vertices: that function assumes a
compact 1..N label numbering, but abagen's DK surface GIFTIs use raw DK atlas
ids (L cortex 1-34, R cortex 42-75, non-contiguous) and crashes with an
IndexError against them (CLAUDE.md §16) — a direct dict lookup sidesteps the
mismatch entirely and is simpler regardless.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd

ABAGEN_DATA = Path(__import__("abagen").__file__).parent / "data"
FSAVERAGE5_LH_MESH = ABAGEN_DATA / "fsaverage5-pial-lh.surf.gii.gz"
FSAVERAGE5_RH_MESH = ABAGEN_DATA / "fsaverage5-pial-rh.surf.gii.gz"


def project_scores_to_surface(score_map: pd.Series, lh_annot, rh_annot) -> tuple[np.ndarray, np.ndarray]:
    """Region scores (indexed by DK atlas region id) -> per-vertex arrays for
    (lh, rh), via direct label lookup. Background/unknown vertices (label 0)
    and any region id not present in `score_map` get NaN.
    """
    lh_labels = nib.load(lh_annot).agg_data()
    rh_labels = nib.load(rh_annot).agg_data()

    lookup = score_map.to_dict()
    lh_vertex = np.array([lookup.get(int(lab), np.nan) if lab != 0 else np.nan for lab in lh_labels])
    rh_vertex = np.array([lookup.get(int(lab), np.nan) if lab != 0 else np.nan for lab in rh_labels])
    return lh_vertex, rh_vertex


def plot_2d_fallback_schematic(
    score_map: pd.Series,
    lh_annot,
    rh_annot,
    disease_label: str,
    vmax: float,
    save_path=None,
):
    """Labeled lateral + superior brain schematic for one disease — the
    no-WebGL fallback (Frontend.md §12: "a designed 2D experience, not a
    banner"). Left hemisphere lateral view (matches the hero figure's
    convention) + a top-down view so both hemispheres are visible at once.
    """
    from nilearn import plotting

    lh_v, rh_v = project_scores_to_surface(score_map, lh_annot, rh_annot)

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.5), subplot_kw={"projection": "3d"})

    plotting.plot_surf_stat_map(
        surf_mesh=str(FSAVERAGE5_LH_MESH), stat_map=lh_v, hemi="left", view="lateral",
        cmap="RdBu_r", vmin=-vmax, vmax=vmax, colorbar=False,
        title="Lateral (L)", axes=axes[0], figure=fig,
    )
    # Superior view layers BOTH hemispheres onto one 3D axes (two calls, one
    # per hemisphere mesh) so the fallback shows the whole brain from above,
    # not just the left side.
    plotting.plot_surf_stat_map(
        surf_mesh=str(FSAVERAGE5_LH_MESH), stat_map=lh_v, hemi="left", view="dorsal",
        cmap="RdBu_r", vmin=-vmax, vmax=vmax, colorbar=False,
        title="Superior", axes=axes[1], figure=fig,
    )
    plotting.plot_surf_stat_map(
        surf_mesh=str(FSAVERAGE5_RH_MESH), stat_map=rh_v, hemi="right", view="dorsal",
        cmap="RdBu_r", vmin=-vmax, vmax=vmax, colorbar=True,
        axes=axes[1], figure=fig,
    )

    fig.suptitle(f"{disease_label} — 2D fallback view", fontsize=13)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    return fig


def plot_hero_figure(
    score_maps: dict[str, pd.Series],
    lh_annot,
    rh_annot,
    save_path=None,
    view: str = "lateral",
    hemi: str = "left",
):
    """3 disease signature maps side by side (cortical view). Full 83-region
    scores are computed for every disease (§7.3); this renders their cortical
    portion. PD's validated result is subcortical (§16) — shown here for
    visual comparability across diseases, not as PD's primary evidence.
    """
    from nilearn import plotting

    mesh = FSAVERAGE5_LH_MESH if hemi == "left" else FSAVERAGE5_RH_MESH
    annot = lh_annot if hemi == "left" else rh_annot

    diseases = list(score_maps.keys())
    fig, axes = plt.subplots(1, len(diseases), figsize=(5 * len(diseases), 5),
                              subplot_kw={"projection": "3d"})
    if len(diseases) == 1:
        axes = [axes]

    all_vals = []
    projected = {}
    for name in diseases:
        lh_v, rh_v = project_scores_to_surface(score_maps[name], lh_annot, rh_annot)
        vtx = lh_v if hemi == "left" else rh_v
        projected[name] = vtx
        all_vals.append(vtx[~np.isnan(vtx)])
    vmax = np.max([np.max(np.abs(v)) for v in all_vals])

    for ax, name in zip(axes, diseases):
        plotting.plot_surf_stat_map(
            surf_mesh=str(mesh), stat_map=projected[name], hemi=hemi, view=view,
            cmap="RdBu_r", vmin=-vmax, vmax=vmax, colorbar=True,
            title=name, axes=ax, figure=fig,
        )

    fig.suptitle("Disease regional expression signatures (cortical view)", y=1.02, fontsize=14)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_specificity_matrix(corr_matrix: pd.DataFrame, save_path=None):
    """Disease x atrophy-map correlation matrix (§7.6). H3 predicts the
    diagonal is strongest."""
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(corr_matrix.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr_matrix.columns)))
    ax.set_xticklabels(corr_matrix.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr_matrix.index)))
    ax.set_yticklabels(corr_matrix.index)
    ax.set_xlabel("Atrophy map (ENIGMA / fallback ground truth)")
    ax.set_ylabel("Expression signature (disease)")
    ax.set_title("Cross-disease specificity: signature vs. atrophy-map correlation")

    for i in range(len(corr_matrix.index)):
        for j in range(len(corr_matrix.columns)):
            val = corr_matrix.iloc[i, j]
            if pd.notna(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        color="white" if abs(val) > 0.5 else "black")

    fig.colorbar(im, ax=ax, label="Pearson r")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_validation_scatter(score: pd.Series, atrophy: pd.Series, title: str, p_value: float,
                             null_type: str, save_path=None):
    """Score map vs. ground-truth atrophy scatter, with the spatial null's
    p-value annotated (§8 deliverable 3)."""
    common = score.index.intersection(atrophy.index)
    x = score.loc[common]
    y = atrophy.loc[common]
    r = np.corrcoef(x, y)[0, 1]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(x, y, alpha=0.7, edgecolor="k", linewidth=0.5)
    m, b = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(xs, m * xs + b, color="crimson", linewidth=1.5)
    ax.set_xlabel("Expression signature score")
    ax.set_ylabel("Atrophy (Cohen's d)")
    ax.set_title(f"{title}\nr = {r:.2f}, {null_type} p = {p_value:.4f}, N = {len(common)}")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
