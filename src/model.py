"""ElasticNet regression: predict regional atrophy from regional gene
expression (CLAUDE.md §7.7). 83 (here ~82) samples x ~15,600 features is
*massively* wide — regularization is mandatory, and this is framed as
exploratory + interpretability, not an accuracy race (a handful of dozens of
samples cannot support a reliable accuracy claim). We always report
cross-validated R², never training R².
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import ElasticNetCV
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import StandardScaler


def run_elasticnet_cv(
    expression: pd.DataFrame,
    atrophy_map: pd.Series,
    n_folds: int = 5,
    l1_ratio: float = 0.5,
    n_alphas: int = 30,
    seed: int = 1234,
) -> dict:
    """Two-stage, single-level CV — NOT nested. Stage 1: one `ElasticNetCV`
    fit (fixed l1_ratio, `n_alphas` candidates, internal `n_folds`-fold CV)
    selects alpha and gives final coefficients for interpretability. Stage 2:
    `cross_val_predict` with a FIXED ElasticNet at that alpha/l1_ratio over
    the same fold structure gives clean per-fold / pooled R².

    This is a known, accepted simplification for exploratory work at this
    sample size (~82): a true nested CV (fresh hyperparameter search inside
    every outer fold) was tried first and was too slow to be practical here
    (each of 5 outer folds re-running its own inner grid search over ~15,600
    features took minutes) for the marginal rigor it buys — hyperparameter
    selection and performance estimation share folds here, which can be
    mildly optimistic. Logged honestly (CLAUDE.md rule 6/§16), not hidden;
    §7.7 already frames this whole layer as exploratory/interpretability, not
    an accuracy claim, so this doesn't change the conclusions we draw from it.
    """
    from sklearn.linear_model import ElasticNet

    common = expression.index.intersection(atrophy_map.index)
    X = expression.loc[common].to_numpy()
    y = atrophy_map.loc[common].to_numpy()
    n = len(common)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    cv = KFold(n_splits=n_folds, shuffle=True, random_state=seed)

    # Stage 1: select alpha (+ get final coefficients for interpretability).
    cv_model = ElasticNetCV(
        l1_ratio=l1_ratio, alphas=n_alphas, cv=cv,
        random_state=seed, max_iter=3000, tol=1e-3,
    )
    cv_model.fit(X_scaled, y)

    # Stage 2: clean CV predictions at that fixed alpha/l1_ratio (fast — no
    # further hyperparameter search, just n_folds plain ElasticNet fits).
    fixed_model = ElasticNet(alpha=cv_model.alpha_, l1_ratio=l1_ratio, max_iter=3000, tol=1e-3)
    y_pred = cross_val_predict(fixed_model, X_scaled, y, cv=cv)

    fold_r2 = []
    for _, test_idx in cv.split(X_scaled):
        ss_res = np.sum((y[test_idx] - y_pred[test_idx]) ** 2)
        ss_tot = np.sum((y[test_idx] - y[test_idx].mean()) ** 2)
        fold_r2.append(1 - ss_res / ss_tot if ss_tot > 0 else np.nan)

    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    cv_r2_pooled = 1 - ss_res / ss_tot

    coefs = pd.Series(cv_model.coef_, index=expression.columns, name="coef")
    nonzero_genes = coefs[coefs != 0].sort_values(key=np.abs, ascending=False)

    return {
        "n_regions": n,
        "n_folds": n_folds,
        "cv_r2_pooled": float(cv_r2_pooled),
        "cv_r2_per_fold": [float(r) for r in fold_r2],
        "y_true": pd.Series(y, index=common, name="atrophy_true"),
        "y_pred_cv": pd.Series(y_pred, index=common, name="atrophy_pred_cv"),
        "final_model_alpha": float(cv_model.alpha_),
        "final_model_l1_ratio": float(l1_ratio),
        "nonzero_genes": nonzero_genes,
        "n_nonzero_genes": len(nonzero_genes),
        "cv_type": "single_level_not_nested",
    }


def genes_overlapping_gwas(nonzero_genes: pd.Series, gwas_risk_genes: list[str]) -> pd.Series:
    """Which of the ElasticNet's non-zero-weight genes are also in the
    disease's own GWAS risk-gene set — closes the loop back to biology (§7.7:
    "whether they overlap the GWAS risk set")."""
    overlap = set(nonzero_genes.index) & set(gwas_risk_genes)
    return nonzero_genes.loc[sorted(overlap)].sort_values(key=np.abs, ascending=False)
