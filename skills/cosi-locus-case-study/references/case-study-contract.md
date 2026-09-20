# Detailed locus case-study contract

## Contents

1. Source precedence
2. Standard packet layout
3. Standard intermediate schemas
4. Evidence and direction rules
5. LD rules
6. Notebook and figure QA

## 1. Source precedence

Use sources in this order:

1. Current corrected union INTACT table for gene-level support and direction.
2. Current completed workflow configuration/metadata for authoritative result paths, dataset metadata, sample sizes, and LD references.
3. Current regional GWAS/eQTL fine-mapping RDS objects for variant-level evidence.
4. Pinned GRCh38 GTF for gene tracks.
5. Older notebooks only for visual grammar or historical context.

Resolve symlinks. Do not replace a configured input with a newer similarly named file. Record any schema ambiguity as a failure or explicit limitation.

## 2. Standard packet layout

```text
analysis/<GENE>/
  <GENE>_case_study.config.json
  <GENE>_modality_ggplot.ipynb
  build_<GENE>_inputs.R
  write_<GENE>_notebook.py          # optional when notebook is generated
  inputs/
    <GENE>_context_direction.tsv
    <GENE>_finemap_status.tsv
    <GENE>_gwas_track.tsv.gz
    <GENE>_sumstat_cs_annotated.tsv.gz
    <GENE>_cs_membership.tsv
    <GENE>_ld_variant_map.tsv
    <GENE>_ld_pairs.tsv.gz
    <GENE>_gene_track.tsv
  figures/
    <GENE>_LD_three_panel.svg
    <GENE>_LD_three_panel.pdf
    <GENE>_LD_three_panel.png
  provenance/
    <GENE>_input_manifest.tsv
    <GENE>_artifact_manifest.tsv
  checks/
    <GENE>_build_qa.tsv
    <GENE>_notebook_qa.tsv
    <GENE>_packet_validation.tsv
```

Existing packets may have flatter layouts. Preserve established locations when revising them; use the standard layout for new genes.

## 3. Standard intermediate schemas

Column names may preserve authoritative upstream names, but provide these semantic fields.

### Context direction

- `gene_id`, `gene_symbol`, `source_gwas`, `source_eqtl`
- `gwas_family`, `eqtl_compartment`, `eqtl_study_family`
- `Z_acat`, `intact_pp`, `best_model`
- `coloc_abf_PP4`, `regional_abf_PP`, `susie_coloc_PP4` when available
- `passes_strict095`, `selected_for_plot`, `selection_reason`
- `canonical_direction` in `positive`, `negative`, `mixed`, `unavailable`

### Fine-mapping status

- dataset ID and role (`GWAS` or `eQTL`)
- RDS path and object hash when practical
- `susie_result_trimmed_present`, convergence/iteration fields
- retained CS count, unique CS variant count
- explicit status/reason

### Evidence membership

- dataset ID, variant ID, chromosome, position, REF, ALT
- evidence type: `retained_95_cs`, `subthreshold_cs_sensitivity`, or `model_weight_not_cs`
- CS ID and requested coverage when applicable
- eQTL Z and focal GWAS Z, both with declared allele orientation
- display flag and reason

### LD variant map

- variant ID, PLINK ID, position, REF, ALT, PLINK A1, PLINK A2
- exact position match, exact allele-set match
- ALT-versus-PLINK-A1 orientation (`+1` or `-1`)

### LD pairs

- two unique variant IDs and positions
- raw PLINK-A1-oriented `r`
- declared allele-oriented signed `r`
- `abs_r`, display flag, display-rule description

## 4. Evidence and direction rules

- Gene-level direction is the sign of canonical `Z_acat`, not INTACT PP or any coloc posterior.
- Variant-level Z and LD signs are allele-oriented quantities. Do not infer gene-level direction from one SNP.
- INTACT PP and coloc values may support selection but never determine sign.
- A retained CS must come from the saved trimmed SuSiE CS object.
- A lower-coverage candidate must state its requested coverage and purity rule.
- Weight SNPs must be called model evidence or `not CS`.
- Missing and failed are separate from zero support.
- Preserve all underlying rows used to create collapsed annotations.

## 5. LD rules

- Use the exact region's authoritative reference and chromosome.
- Validate sidecars, sample count, variant position, and allele set.
- Store a complete matrix/pair table for the displayed evidence union.
- Expected unordered-pair count is `n * (n - 1) / 2`.
- Reorient signed LD only after validating the allele mapping.
- Use a two-segment midpoint triangle in the plot.
- A plot threshold such as `0.20 <= |r| < 0.99` is a display rule, not an input filter.

## 6. Notebook and figure QA

- R kernel metadata is present.
- Every nonempty code cell has an execution count and no error output.
- Notebook provenance lists raw paths, builder code, and intermediate inputs.
- SVG is editable, PDF is vector and readable, PNG is a high-resolution review image.
- Axis windows align across panels.
- Labels and legends are unclipped at final output size.
- Figure counts, captions, and tables agree.
- The caption distinguishes retained CS, lower-coverage sensitivity, and non-CS evidence.
