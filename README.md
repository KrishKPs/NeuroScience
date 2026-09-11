# Regional Vulnerability Signatures in Brain Disease

Imaging transcriptomics pipeline linking Allen Human Brain Atlas gene expression to
GWAS disease risk genes, testing whether each disease's regional expression
signature predicts where it actually causes atrophy — with spatial null models
controlling for spatial autocorrelation.

**Status:** in progress. See `CLAUDE.md` for the full project spec, methodology,
and decision log. Primary disease: **Parkinson's**.

Not novel research — a clean, rigorous, well-told reproduction + cross-disease
comparison in imaging transcriptomics. Association, not causation.

## Setup

```bash
conda env create -f environment.yml
conda activate neuro-signatures
```

`enigmatoolbox` is not on PyPI; if `environment.yml`'s pip step doesn't pick it
up, install it directly:

```bash
pip install "git+https://github.com/MICA-MNI/ENIGMA.git"
```

**Known install gotcha:** `abagen`'s mouse submodule imports `pkg_resources`,
which `setuptools>=81` removed. `requirements.txt` pins `setuptools<81` — if you
see `ModuleNotFoundError: No module named 'pkg_resources'`, that pin is missing.

## Data provenance

| Source | What | Access date | Notes |
|---|---|---|---|
| Allen Human Brain Atlas | Region x gene expression, DK-parcellated | 2026-09-11 | via `abagen.get_expression_data`; 6 donor brains, mostly left hemisphere, microarray. Cached in `data/raw/abagen-data/` (gitignored — re-downloads on first run). |
| GWAS Catalog (ebi.ac.uk/gwas) | Disease risk genes | 2026-09-11 | REST API, per-trait associations, filtered p <= 5e-8. **PD trait id: `MONDO_0005180`** — the commonly-cited `EFO_0002508` is obsolete (verified against `ebi.ac.uk/ols4`); GWAS Catalog no longer indexes associations under it. |
| ENIGMA Toolbox | Case-control Cohen's d atrophy maps, DK-parcellated | 2026-09-11 | via `enigmatoolbox.datasets.load_summary_stats('parkinsons')`. PD target (substantia nigra) isn't in DK, so validation uses a basal-ganglia proxy (caudate/putamen/pallidum) against `Subvol_PDvsCN`. |

Re-download: delete `data/raw/` and re-run the relevant `src/data_load.py`
functions — everything under `data/raw/` is reconstructed from source, nothing
there is hand-edited.

## Repository structure

See CLAUDE.md §9 for the full layout and rationale. Analysis logic lives in
`src/`; notebooks only narrate and import from it.

## Reproducibility

Global seed `1234`, 10,000 permutations for both null models, all tunables in
`config/params.yaml`. See CLAUDE.md §11.

## Limitations

(To be filled in as the pipeline is validated — see CLAUDE.md §13 for the
pitfalls this project explicitly watches for: gene-symbol mismatches, AHBA's
6-donor/left-hemisphere bias, invalid use of cortical spin tests on subcortical
maps, and the small-N ML layer.)
