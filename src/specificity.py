"""Cross-disease specificity matrix. H3 predicts each
disease's expression signature best matches its OWN atrophy map — the
diagonal should be strongest.

Ground truth differs in kind per disease (PD: subcortical Cohen's d, SCZ:
cortical Cohen's d, AD: binary canonical-ROI indicator — no continuous map
exists), so cells are computed only where a score map and
an atrophy map share region ids; unmatched cells are NaN rather than forced
to a number that would misrepresent a domain mismatch (e.g. PD's cortex-only
score vs. AD's mixed-domain ROI indicator, where the shared region count is
thin) — left as NaN and explained in the writeup, not smoothed over.
"""
from __future__ import annotations

import pandas as pd


def build_specificity_matrix(
    score_maps: dict[str, pd.Series],
    atrophy_maps: dict[str, pd.Series],
) -> pd.DataFrame:
    diseases = list(score_maps.keys())
    matrix = pd.DataFrame(index=diseases, columns=diseases, dtype=float)

    for row_disease, score in score_maps.items():
        for col_disease, atrophy in atrophy_maps.items():
            common = score.index.intersection(atrophy.index)
            if len(common) < 3:
                matrix.loc[row_disease, col_disease] = float("nan")
                continue
            matrix.loc[row_disease, col_disease] = score.loc[common].corr(atrophy.loc[common])

    return matrix
