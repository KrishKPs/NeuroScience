"""Cheap sanity checks per CLAUDE.md §11. Data-dependent tests skip cleanly
when their input file hasn't been generated yet (run the relevant src/
pipeline step first) rather than failing.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPRESSION_PATH = PROJECT_ROOT / "data" / "interim" / "expression_matrix.csv"
PD_GENES_PATH = PROJECT_ROOT / "data" / "interim" / "pd_gwas_risk_genes.csv"
PROCESSED = PROJECT_ROOT / "data" / "processed"


@pytest.fixture(scope="module")
def expression():
    if not EXPRESSION_PATH.exists():
        pytest.skip(f"{EXPRESSION_PATH} not built yet — run src.data_load.get_expression_matrix")
    return pd.read_csv(EXPRESSION_PATH, index_col=0)


def test_expression_matrix_shape(expression):
    n_regions, n_genes = expression.shape
    assert n_regions == 83, f"expected 83 DK regions, got {n_regions}"
    assert n_genes > 10000, f"expected ~15,600 genes, got {n_genes}"


def test_housekeeping_gene_broadly_expressed(expression):
    assert "GAPDH" in expression.columns, "GAPDH missing from expression matrix"
    gapdh = expression["GAPDH"]
    assert gapdh.notna().sum() >= 0.9 * len(gapdh), "GAPDH should be expressed in nearly all regions"


def test_expression_no_unexpected_all_nan_columns(expression):
    all_nan_frac = expression.isna().all(axis=0).mean()
    assert all_nan_frac < 0.01, f"{all_nan_frac:.2%} of genes are all-NaN across regions"


def test_pd_gwas_risk_genes():
    if not PD_GENES_PATH.exists():
        pytest.skip(f"{PD_GENES_PATH} not built yet — run src.data_load.get_disease_risk_genes")
    genes = pd.read_csv(PD_GENES_PATH)
    assert len(genes) > 0
    assert "gene" in genes.columns
    assert genes["gene"].is_unique, "risk gene list should be deduplicated"
    assert (genes["pvalue"] <= 5e-8).all(), "all rows should be genome-wide significant"


def test_reconcile_genes_survival_rate(expression):
    if not PD_GENES_PATH.exists():
        pytest.skip(f"{PD_GENES_PATH} not built yet")
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.harmonize import reconcile_genes

    genes = pd.read_csv(PD_GENES_PATH)
    result = reconcile_genes(genes, expression)
    assert result["n_matched"] > 0
    # Sanity floor, not a hard scientific claim — flag if reconciliation looks broken.
    assert result["survival_rate"] > 0.5, (
        f"only {result['survival_rate']:.1%} of GWAS genes matched the expression matrix — "
        "investigate symbol mismatches before proceeding"
    )


def test_pd_score_map_no_unexpected_nans():
    path = PROCESSED / "pd_score_map_full.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet — run run_pipeline.run_week3_pd_validation")
    score = pd.read_csv(path, index_col=0)["score"]
    assert len(score) == 83
    assert score.notna().all(), "score map has unexpected NaNs"


def test_pd_null_distributions_expected_length():
    import numpy as np

    gene_set_path = PROCESSED / "pd_gene_set_null_distribution.npy"
    spatial_path = PROCESSED / "pd_spatial_null_distribution.npy"
    if not (gene_set_path.exists() and spatial_path.exists()):
        pytest.skip("null distributions not built yet — run run_pipeline.run_week3_pd_validation")

    gene_set_null = np.load(gene_set_path)
    spatial_null = np.load(spatial_path)
    assert len(gene_set_null) == 10000, f"expected 10,000 permutations, got {len(gene_set_null)}"
    assert len(spatial_null) == 10000, f"expected 10,000 permutations, got {len(spatial_null)}"
    assert np.isfinite(gene_set_null).all(), "gene-set null distribution has non-finite values"
    assert np.isfinite(spatial_null).all(), "spatial null distribution has non-finite values"


def test_pd_validation_summary_reports_both_nulls():
    path = PROCESSED / "pd_validation_summary.json"
    if not path.exists():
        pytest.skip(f"{path} not built yet — run run_pipeline.run_week3_pd_validation")
    with open(path) as f:
        summary = json.load(f)
    assert 0 <= summary["gene_set_null_p"] <= 1
    assert 0 <= summary["spatial_null_p"] <= 1
    assert summary["n_regions"] >= 10, "too few regions for a meaningful spatial null"


@pytest.mark.parametrize("disease,extra_keys", [
    ("scz", ["gene_set_null_p", "spatial_null_p"]),
    ("ad", ["gene_set_null_p", "approx_spatial_null_p"]),
])
def test_week4_validation_summaries(disease, extra_keys):
    path = PROCESSED / f"{disease}_validation_summary.json"
    if not path.exists():
        pytest.skip(f"{path} not built yet — run run_pipeline.py")
    with open(path) as f:
        summary = json.load(f)
    for key in extra_keys:
        assert 0 <= summary[key] <= 1, f"{key} should be a valid p-value"


def test_week4_score_maps_no_unexpected_nans():
    for disease in ("scz", "ad"):
        path = PROCESSED / f"{disease}_score_map_full.csv"
        if not path.exists():
            pytest.skip(f"{path} not built yet — run run_pipeline.py")
        score = pd.read_csv(path, index_col=0)["score"]
        assert len(score) == 83
        assert score.notna().all(), f"{disease} score map has unexpected NaNs"


def test_specificity_matrix_diagonal_present():
    path = PROJECT_ROOT / "results" / "tables" / "specificity_matrix.csv"
    if not path.exists():
        pytest.skip(f"{path} not built yet — run run_pipeline.py")
    matrix = pd.read_csv(path, index_col=0)
    assert matrix.shape == (3, 3)
    # PD and SCZ have real continuous atrophy ground truth — diagonal should be
    # their row's strongest correlation (H3, §7.6). AD uses a weaker fallback
    # ROI indicator and was not significant under either null (§16), so its
    # diagonal is NOT asserted to be strongest — that's an honest finding, not
    # a bug (see docs/writeup.md limitations).
    for disease in ["parkinsons", "schizophrenia"]:
        row = matrix.loc[disease]
        assert row.idxmax() == disease, f"{disease}'s own atrophy map should be its strongest match"
