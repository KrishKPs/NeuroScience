"""Regional expression score — the disease "signature map". See CLAUDE.md §7.3.

score[region] = mean (or median) over the disease gene set of z(expr[region, gene]),
where each gene is z-scored across regions first so genes with different
expression scales/variances contribute comparably.
"""
from __future__ import annotations

import pandas as pd


def zscore_genes(expression: pd.DataFrame) -> pd.DataFrame:
    """Z-score each gene (column) across regions (rows)."""
    return (expression - expression.mean(axis=0)) / expression.std(axis=0, ddof=0)


def region_score(
    expression: pd.DataFrame,
    gene_set: list[str],
    method: str = "mean",
    zscored: bool = False,
) -> pd.Series:
    """Collapse a region x gene expression matrix to one score per region by
    averaging (mean or median) the z-scored expression of `gene_set`.

    Genes in `gene_set` not present in `expression.columns` are silently
    dropped (that reconciliation step — and its survival rate — belongs in
    harmonize.py, called before this, not here).
    """
    if method not in ("mean", "median"):
        raise ValueError(f"method must be 'mean' or 'median', got {method!r}")

    present = [g for g in gene_set if g in expression.columns]
    if not present:
        raise ValueError("none of the requested genes are present in the expression matrix")

    z = expression if zscored else zscore_genes(expression)
    sub = z[present]

    return sub.mean(axis=1) if method == "mean" else sub.median(axis=1)
