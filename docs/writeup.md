# Regional Vulnerability Signatures in Brain Disease

*Imaging transcriptomics pipeline linking Allen Human Brain Atlas gene expression to
GWAS disease risk genes, testing whether each disease's regional expression signature
predicts where it actually causes atrophy — validated against spatial null models.*

## The question

Brain diseases don't damage the whole brain evenly — Parkinson's hits the basal
ganglia, schizophrenia erodes frontal and temporal cortex, Alzheimer's starts in the
entorhinal cortex and hippocampus. Why those regions and not others is only partly
understood. One hypothesis, from the field of imaging transcriptomics: a disease's
risk genes are more strongly expressed, at baseline, in exactly the regions it later
damages. If true, you should be able to score every brain region for how "switched
on" a disease's risk genes are there, and that score map should line up with where
the disease actually causes atrophy.

This project is not novel research. It's a faithful, documented reproduction of that
method across three diseases — Parkinson's (primary), schizophrenia, and
Alzheimer's — built as a portfolio piece with an emphasis on doing the statistics
honestly.

## Data

Three free, public sources, all in the Desikan-Killiany (DK) 83-region brain
parcellation: the **Allen Human Brain Atlas** (via `abagen`) for a region × gene
expression matrix (83 regions × 15,633 genes, from 6 donor brains); the **GWAS
Catalog** for each disease's genome-wide-significant (p ≤ 5×10⁻⁸) risk genes; and the
**ENIGMA Toolbox** for case-control Cohen's d atrophy maps in the same DK space.

Two of the three GWAS Catalog trait IDs commonly cited for these diseases turned out
to be obsolete in the current ontology — including Parkinson's own `EFO_0002508` —
silently returning no data. All three were re-verified live against the API before
use.

## Method

For each disease: pull its risk genes, reconcile their symbols against the AHBA
matrix's gene columns (PD: 149/202 matched, 73.8%; SCZ: 913/1449, 63.0%; AD:
164/254, 64.6% — GWAS Catalog symbols vs. HGNC nomenclature don't align perfectly,
and this reconciliation step is genuinely the boring 40% of the project), z-score
each gene across all 83 regions, then average the z-scores of the disease's risk
genes within each region. That's the region's "signature score." Correlate the
signature map against the disease's real ENIGMA atrophy map.

## The rigor step

A raw correlation between two brain maps is close to meaningless on its own, because
neighboring brain regions resemble each other — any two smooth, spatially
autocorrelated maps will correlate above zero just by construction. Two null models
address this from different angles: a **gene-set null** (10,000 random gene sets of
the same size, to test whether the *specific* genes matter) and a **spatial null**
(10,000 spatially-structured surrogate maps, to test whether the correlation survives
once autocorrelation is accounted for). Cortical targets use the Alexander-Bloch spin
test; Parkinson's target isn't cortical — substantia nigra isn't in the DK atlas — so
its basal-ganglia proxy uses a variogram-matched null (Burt et al. 2020) instead. No
result below is reported without both.

## Results

**Parkinson's** (basal-ganglia proxy vs. subcortical atrophy, N=14 DK subcortical
structures — extended from the 3-structure proxy because the variogram null needs
more spatial points than N=6 supports): **r = 0.76**, gene-set p = 0.042, spatial
p < 0.001.

**Schizophrenia** (cortical signature vs. cortical thickness atrophy, N=68): **r =
0.45**, gene-set p = 0.0034, spin p = 0.0028.

**Alzheimer's** (no ENIGMA AD map exists in the toolbox used here, so this falls back
to a canonical vulnerable-region list — entorhinal, hippocampus, amygdala): **r =
0.23**, gene-set p = 0.40, approximate spatial p = 0.14 — **not significant**. Reported
as-is; there's no reason to expect every disease to work equally well, and AD's
result here is honestly negative.

The cross-disease specificity matrix (each disease's signature vs. every disease's
atrophy map) shows the diagonal strongest for PD and SCZ, as hypothesized — but not
for AD, consistent with its non-significant validation.

An exploratory ElasticNet layer (82 regions × ~15,600 genes, single-level 5-fold CV)
predicting PD's combined whole-brain atrophy map from full expression profiles
reached pooled CV R² = 0.63, with 28 non-zero-weight genes, only one of which
(C8orf58) overlaps PD's own GWAS risk set — a reminder that a predictive model and a
biologically-grounded gene set are not the same claim.

## Limitations

AHBA is only 6 donor brains, mostly the left hemisphere, and microarray (not
RNA-seq) — small-N and platform effects are real. Parkinson's true target,
substantia nigra, isn't in the DK atlas, so its validation uses a basal-ganglia
proxy — a real limitation, not just a technicality. Alzheimer's has no continuous
ENIGMA ground truth in this toolbox, so its result rests on a coarser, non-significant
fallback test. The ElasticNet layer's cross-validation is single-level, not nested,
for tractability at this sample size — a fully nested version was tried and took over
20 minutes per run for negligible extra rigor. And throughout: everything here is
association, not causation — "consistent with," never "proves."
