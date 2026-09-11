"""Loaders for the three raw data sources: AHBA expression (abagen), GWAS Catalog
risk genes, and ENIGMA Toolbox atrophy maps. See CLAUDE.md §7.1-7.2, §7.5.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import abagen
import numpy as np
import pandas as pd
import requests
import yaml

GWAS_API_BASE = "https://www.ebi.ac.uk/gwas/rest/api"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | Path = PROJECT_ROOT / "config" / "params.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# 1. AHBA expression matrix (abagen)
# ---------------------------------------------------------------------------

def fetch_dk_atlas(surface: bool = False):
    """Desikan-Killiany atlas (image + 83-region info table). Ships with abagen,
    no download required. `surface=True` returns DK surface GIFTI label files
    (lh, rh) instead of the volumetric image — needed for the cortical spin
    test (CLAUDE.md §7.4b)."""
    return abagen.fetch_desikan_killiany(surface=surface)


def get_expression_matrix(
    atlas: dict | None = None,
    ibf_threshold: float = 0.5,
    probe_selection: str = "diff_stability",
    lr_mirror: str = "bidirectional",
    missing: str = "centroids",
    gene_norm: str = "srs",
    data_dir: str | Path | None = None,
    save_path: str | Path | None = None,
    verbose: int = 1,
) -> pd.DataFrame:
    """Build the 83-region x ~15,600-gene AHBA expression matrix for the DK atlas.

    First call downloads the ~4GB AHBA microarray dataset into `data_dir` (or
    abagen's default cache) and can take a long time. Subsequent calls reuse
    the cache.
    """
    if atlas is None:
        atlas = fetch_dk_atlas()

    expression = abagen.get_expression_data(
        atlas["image"],
        atlas["info"],
        ibf_threshold=ibf_threshold,
        probe_selection=probe_selection,
        lr_mirror=lr_mirror,
        missing=missing,
        gene_norm=gene_norm,
        return_donors=False,
        data_dir=str(data_dir) if data_dir else None,
        verbose=verbose,
    )

    if save_path is not None:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        expression.to_csv(save_path)

    return expression


# ---------------------------------------------------------------------------
# 2. GWAS Catalog risk genes
# ---------------------------------------------------------------------------

def fetch_gwas_associations(efo_id: str, page_size: int = 500, max_pages: int = 200) -> list[dict]:
    """Pull every association record for a GWAS Catalog EFO/MONDO trait id.

    NOTE: as of 2026-09-11 this endpoint has been observed to ignore `size`/`page`
    and return the full association set on every call (verified for
    MONDO_0005180: 814 records regardless of page). We still paginate
    defensively via the `_links.next` HAL link in case behavior differs for
    larger traits (e.g. schizophrenia), and de-duplicate by SNP+study to be
    safe against that non-standard pagination.
    """
    url = f"{GWAS_API_BASE}/efoTraits/{efo_id}/associations"
    params = {"projection": "associationByEfoTrait", "size": page_size, "page": 0}

    records: list[dict] = []
    seen_keys: set[tuple] = set()
    pages_fetched = 0

    while url and pages_fetched < max_pages:
        resp = requests.get(url, params=params if pages_fetched == 0 else None, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("_embedded", {}).get("associations", [])

        new_in_batch = 0
        for r in batch:
            key = (
                r.get("study", {}).get("accessionId"),
                tuple(sorted(sn.get("rsId", "") for sn in r.get("snps", []))),
                r.get("pvalue"),
            )
            if key not in seen_keys:
                seen_keys.add(key)
                records.append(r)
                new_in_batch += 1

        pages_fetched += 1
        next_href = data.get("_links", {}).get("next", {}).get("href")
        if not next_href or new_in_batch == 0:
            break
        url = next_href
        params = None
        time.sleep(0.2)

    return records


def extract_risk_genes(records: list[dict], pvalue_threshold: float = 5e-8) -> pd.DataFrame:
    """From raw GWAS Catalog association records, keep genome-wide significant
    hits (p <= pvalue_threshold) and return their MAPPED_GENE-equivalent
    (authorReportedGenes) symbols as a tidy DataFrame with provenance.

    Filters out obviously invalid gene tokens (empty, pure numeric — the
    catalog occasionally has junk entries like a lone "1") and strips stray
    control characters (observed: trailing "\\r" on some gene names).
    """
    rows = []
    for r in records:
        p = r.get("pvalue")
        if p is None or p > pvalue_threshold:
            continue
        rs_ids = [sn.get("rsId") for sn in r.get("snps", [])]
        accession = r.get("study", {}).get("accessionId")
        for locus in r.get("loci", []):
            for g in locus.get("authorReportedGenes", []):
                name = g.get("geneName")
                if not name:
                    continue
                name = name.strip()
                if not name or not re.match(r"^[A-Za-z0-9][A-Za-z0-9\-_.]*$", name):
                    continue
                if name.isdigit():
                    continue
                rows.append({
                    "gene": name,
                    "pvalue": p,
                    "rsids": ";".join(x for x in rs_ids if x),
                    "study_accession": accession,
                })

    df = pd.DataFrame(rows)
    return df


def get_disease_risk_genes(efo_id: str, pvalue_threshold: float = 5e-8) -> pd.DataFrame:
    """Convenience wrapper: fetch + filter + dedupe to one row per unique gene
    (keeping the minimum/most-significant p-value seen for that gene)."""
    records = fetch_gwas_associations(efo_id)
    hits = extract_risk_genes(records, pvalue_threshold=pvalue_threshold)
    if hits.empty:
        return hits
    deduped = (
        hits.sort_values("pvalue")
        .groupby("gene", as_index=False)
        .first()
        .sort_values("gene")
        .reset_index(drop=True)
    )
    return deduped


# ---------------------------------------------------------------------------
# 3. ENIGMA Toolbox atrophy maps
# ---------------------------------------------------------------------------

def get_region_centroids(atlas: dict | None = None) -> pd.DataFrame:
    """World-space (MNI) centroid coordinates for every DK atlas region, computed
    as the mean voxel coordinate (in world space) of each region's label in the
    atlas volume. Needed for the subcortical variogram null (§7.4b) — there is
    no surface to spin, so distances are computed directly in volume space.

    Returns a DataFrame indexed by region id (1-83) with columns
    ['label', 'hemisphere', 'structure', 'x', 'y', 'z'].
    """
    import nibabel as nib

    if atlas is None:
        atlas = fetch_dk_atlas()

    img = nib.load(atlas["image"])
    data = img.get_fdata()
    affine = img.affine
    info = pd.read_csv(atlas["info"])

    rows = []
    for _, row in info.iterrows():
        rid = row["id"]
        coords = np.argwhere(data == rid)
        if len(coords) == 0:
            xyz = (np.nan, np.nan, np.nan)
        else:
            centroid_vox = coords.mean(axis=0)
            xyz = tuple(nib.affines.apply_affine(affine, centroid_vox))
        rows.append({
            "id": rid,
            "label": row["label"],
            "hemisphere": row["hemisphere"],
            "structure": row["structure"],
            "x": xyz[0], "y": xyz[1], "z": xyz[2],
        })

    return pd.DataFrame(rows).set_index("id")


def load_enigma_atrophy(disorder: str) -> dict[str, pd.DataFrame]:
    """Case-control Cohen's d summary stats for `disorder` (DK-parcellated).
    Valid keys per enigmatoolbox: '22q','adhd','anorexia','antisocial',
    'asymmetry','asd','bipolar','depression','epilepsy','lifespan','ocd',
    'parkinsons','psychosis','schizophrenia','schizotypy'.

    Returns the full dict of sub-tables (cortical thickness / surface area /
    subcortical volume, x several contrasts). Callers pick the relevant table,
    e.g. for Parkinson's: 'CortThick_PDvsCN', 'CortSurf_PDvsCN',
    'Subvol_PDvsCN' (note: lowercase 'v' in 'Subvol' — a quirk of the
    package's actual key, not a typo here).
    """
    from enigmatoolbox.datasets import load_summary_stats

    return load_summary_stats(disorder)


def load_enigma_schizophrenia_atrophy() -> dict[str, pd.DataFrame]:
    """Direct replacement for load_enigma_atrophy('schizophrenia').

    enigmatoolbox==2.0.3's own `load_summary_stats('schizophrenia')` crashes
    with FileNotFoundError: it references 'Schizophrenia_case-controls_SubVol.csv'
    (plural "controls"), but the file actually shipped in the package is named
    'Schizophrenia_case-control_SubVol.csv' (singular) — an upstream filename
    typo. The package separately ships a correctly-named, consistent
    'scz_case-controls_*.csv' set that the same function also loads before
    hitting the broken reference; we load those three directly and skip the
    broken 'Schizo_*' duplicate entirely (CLAUDE.md §16).
    """
    import enigmatoolbox.datasets as eds

    root = Path(eds.__file__).parent / "summary_statistics"
    return {
        "CortThick_case_vs_controls": pd.read_csv(root / "scz_case-controls_CortThick.csv", on_bad_lines="skip"),
        "CortSurf_case_vs_controls": pd.read_csv(root / "scz_case-controls_CortSurf.csv", on_bad_lines="skip"),
        "SubVol_case_vs_controls": pd.read_csv(root / "scz_case-controls_SubVol.csv", on_bad_lines="skip"),
    }
