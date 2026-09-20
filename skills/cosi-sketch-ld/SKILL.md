---
name: cosi-sketch-ld
description: "Compute complete, allele-audited regional LD matrices and pair tables from the existing COSI ADSP R4 sketch-genotype PGEN files. Use for COSI or COSI_pecotmr sketch LD requests, locus-packet LD, SuSiE-RSS LD inputs, sketch-versus-reference checks, or questions about the canonical sketch paths and symlink provenance."
---

# COSI Sketch LD

Use the executed R-kernel tutorial as the canonical implementation and operator guide:

`/sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/3_Production/COSI_paper/output/jupyter-notebook/cosi-sketch-genotype-ld.ipynb`

The reproducible notebook writer is adjacent:

`/sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/3_Production/COSI_paper/output/jupyter-notebook/write_cosi_sketch_genotype_ld_notebook.py`

## Storage contract

- Treat `COSI/hg38/ADSP_reference_panel/ADSP_sketch_reference/{EUR,AFR}/rss_ld_sketch` as the physical sketch tree.
- Treat `COSI_pecotmr/hg38/ADSP_reference_panel` as a symlink to the COSI reference panel, not as a second copy.
- Resolve the per-chromosome prefix from the ancestry manifest and require `.pgen`, `.pvar`, `.psam`, and `.afreq`.
- Do not regenerate `W` or the chromosome sketch for an LD query.
- The PGEN rows are projected pseudo-samples, not participants. Never describe `B=10000` as a human sample size and never write the transient projected matrix.

## Required workflow

1. Read the tutorial's `load_sketch_LD_matrix()` cell before changing or executing the method.
2. Supply a same-chromosome table with `variant_id`, `chrom`, `pos`, `ref`, and `alt`.
3. Match by GRCh38 chromosome and position plus the unordered allele set; do not trust identifier punctuation alone.
4. Use the installed `pecotmr` helpers through the notebook wrapper: `pecotmr:::open_pgen`, `pecotmr:::read_pgen`, and `pecotmr:::compute_LD`.
5. Preserve the sketch-specific corrections in the wrapper:
   - when source ALT frequency is greater than 0.5, reverse the minor-allele-oriented stored dosage with `2 - x_scaled`;
   - then undo the per-variant transform using `U_MIN` and `U_MAX` from `.afreq`;
   - orient signed correlation to the requested ALT allele.
6. Return the OTTERS/RSS-style fields `combined_LD_variants`, `combined_LD_matrix`, and `ref_panel`, plus the allele/orientation audit.
7. Export the labeled square matrix and all `n(n-1)/2` unordered pairs without an LD threshold. Retain signed `r`, `r2`, variant IDs, positions, and orientation fields.

## Verification gates

- Stop on a missing or multiply matched variant; never silently shrink the requested universe.
- Require exact position-match and allele-set-match rates of 1.
- Require a unit diagonal, symmetry, finite values, and `abs(r) <= 1` within numerical tolerance.
- Require the observed pair count to equal `n(n-1)/2`.
- Record `pecotmr` and `pgenlibr` versions because the PGEN helpers are internal in `pecotmr` 0.3.4.
- For a method check, compare against an existing ancestry-matched full-reference pair table when available. Do not read or copy individual genotypes merely to validate a routine sketch query.

## Scientific boundary

LD describes correlation in the ancestry-matched reference; it is not evidence of colocalization, causality, mechanism, or credible-set membership. Preserve the source evidence labels from the requested variant table.

For a small selected-variant query, run the notebook locally with the R kernel. For a large regional universe, estimate `B * n_variants * 8` bytes plus the square LD matrix and use the project HPC path with at least 32 GB rather than an oversized interactive run.
