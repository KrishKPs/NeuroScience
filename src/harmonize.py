"""Reconcile GWAS Catalog gene symbols against the AHBA expression matrix's
gene columns (HGNC symbols from abagen).

This is the "boring 40%" the project plan calls out: GWAS Catalog gene symbols
are author-reported and not guaranteed to match current HGNC nomenclature used
by abagen's probe annotation. We do a direct-match pass and report the
survival rate; anything more elaborate (alias resolution) is deliberately out
of scope unless the survival rate is too low to be usable.
"""
from __future__ import annotations

import pandas as pd


def reconcile_genes(risk_genes: pd.DataFrame, expression: pd.DataFrame) -> dict:
    """Match a GWAS risk-gene table (column 'gene') against expression matrix
    columns (genes). Returns a dict with the matched gene list, the dropped
    list, and the survival rate — log all three.
    """
    gwas_set = set(risk_genes["gene"])
    expr_set = set(expression.columns)

    matched = sorted(gwas_set & expr_set)
    dropped = sorted(gwas_set - expr_set)
    survival_rate = len(matched) / len(gwas_set) if gwas_set else 0.0

    return {
        "matched": matched,
        "dropped": dropped,
        "n_gwas_genes": len(gwas_set),
        "n_matched": len(matched),
        "survival_rate": survival_rate,
    }
