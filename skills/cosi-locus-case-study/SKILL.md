---
name: cosi-locus-case-study
description: Build, revise, or audit detailed gene-centered COSI locus case-study packets modeled on BIN1, CASS4, PICALM, and SRC. Covers canonical INTACT direction and context selection, SuSiE credible-set extraction, explicitly labeled subthreshold or non-CS evidence, allele-aligned GWAS/eQTL tracks, actual PLINK LD triangles, GRCh38 gene tracks, R/ggplot SVG/PDF/PNG exports, executed R-kernel notebooks, provenance, and QA. Use for detailed locuszoom or modality plots, sign-flip locus figures, credible-set/LD comparisons, or when reproducing one of these gene notebooks for another locus.
---

# COSI Gene Locus Case Studies

Build a self-contained, evidence-backed packet rather than a figure assembled from manually chosen points. Use current corrected COSI results and preserve missing or failed evidence honestly.

## Required companion conventions

- Apply the `cosi-notebook` convention for the executed R-kernel review notebook and provenance section.
- Apply the `cosi-locus-zoom` convention for aligned genomic panels and two-segment LD triangles.
- Use R with `data.table`, `ggplot2`, `ggrepel`, and `patchwork` or the established local equivalent for the scientific figure.
- Read [case-study-contract.md](references/case-study-contract.md) before implementing a new locus.
- Read [exemplar-map.md](references/exemplar-map.md) and start from the closest scientific pattern, not simply the most recent script.

## Choose the evidence pattern

Classify the requested locus before plotting:

1. **Concordant retained CS** — multiple supported contexts have the same canonical gene-level direction and retained SuSiE credible sets. Follow the BIN1 pattern.
2. **Opposing retained CS** — supported contexts have opposite canonical directions and retained credible sets. Follow the PICALM pattern.
3. **Subthreshold-CS sensitivity** — a scientifically important context lacks a retained 95% CS but a recomputed lower-coverage candidate is coherent. Follow the CASS4 pattern and label it as a sensitivity, never as a retained CS.
4. **Non-CS model evidence** — a context lacks `susie_result_trimmed`, but real OTTERS model SNPs are worth displaying. Follow the SRC pattern and label every such marker `not CS`.
5. **No valid variant-level evidence** — report the gene-level result and fine-mapping failure; do not manufacture a locus track.

Use more than one pattern only when the data require it. Do not choose contexts merely to make the plot look balanced.

## Workflow

### 1. Resolve the locus from the current truth tables

- Start from the current corrected union INTACT table used by the repository. Resolve symlinks and record the exact file hash.
- Select by stable `gene_id`; use `gene_symbol` for display only.
- Audit every AD GWAS/eQTL row for the gene before choosing the focal GWAS or contexts.
- Use canonical `Z_acat_num`/`Z_acat` for gene-level effect direction. INTACT PP, ABF PP4, regional PP, and SuSiE-coloc PP4 are support measures, not direction statistics.
- Record all audited rows, including unselected and failed contexts, in a direction/status table.

### 2. Select a single focal GWAS and honest context set

- Use one focal GWAS across plotted eQTL contexts so the regional background is comparable.
- Require one unambiguous canonical focal row per selected context.
- State whether context selection requires strict support, merely provides direction context, or is a named sensitivity.
- Preserve independent dataset identifiers and study-family metadata. Do not call repeated populations independent replication.
- If a requested context lacks usable fine-mapping, keep it in the audit table and explain its omission from the CS panel.

### 3. Inspect the actual fine-mapping objects

- Locate authoritative GWAS/eQTL RDS files from current workflow metadata and result paths; do not infer them from filenames alone when a manifest exists.
- Inspect object structure before coding. The retained CS source is the saved SuSiE object, normally `susie_result_trimmed$sets$cs` with indices into the corresponding variant vector.
- Validate every CS index, variant ID, position, REF/ALT pair, and dataset label.
- Collapse duplicate membership only for display; retain the full CS-to-variant membership table.
- Record convergence, iteration count, CS count, unique CS variants, and explicit failure reason.
- Never reinterpret OTTERS weight SNPs, a PIP cutoff, proximity, or `susie_lbf` as a retained credible set.

### 4. Handle lower-coverage or non-CS evidence explicitly

- Add a lower-coverage candidate only when requested or needed to explain a supported direction that lacks a retained 95% CS.
- Recompute it from the saved SuSiE fit, record coverage and purity, and validate purity using the exact project LD reference.
- Use hollow markers and dashed connectors for lower-coverage sensitivity sets.
- Use a distinct marker and the literal label `not CS` for OTTERS model SNPs.
- Keep primary and sensitivity evidence separate in source tables and legends.

### 5. Build notebook-ready intermediates

Create a dedicated R builder under `analysis/<GENE>/`; do not hide data construction inside the notebook. Standard outputs are listed in [case-study-contract.md](references/case-study-contract.md).

- Regional GWAS track: signed focal-GWAS Z and allele fields in the display window.
- eQTL evidence track: signed eQTL Z, exact evidence membership, context, CS label, coverage, and evidence type.
- Context direction table: canonical gene-level Z, INTACT PP, coloc support, selection status, and reason.
- Fine-mapping status table: retained/missing/failed status and convergence fields.
- Variant map: COSI ID, chromosome, position, REF/ALT, PLINK ID, PLINK A1/A2, and orientation.
- LD pairs: complete pairwise signed LD for the displayed evidence-variant union.
- GRCh38 gene track: genes overlapping the plotted window with the focal gene uniquely flagged.
- Input manifest and machine-readable QA tables.

Use [scaffold_case_study.py](scripts/scaffold_case_study.py) to create a new packet skeleton and AI-readable configuration when helpful.
Invoke bundled helpers through the active Python interpreter, for example `python <skill-dir>/scripts/scaffold_case_study.py --help`; they have no external Python dependencies.

### 6. Derive LD from the exact project reference

- Resolve the LD prefix through the authoritative regional LD metadata when available.
- Validate PLINK sidecars and sample count before calculation.
- Require exact chromosome, position, and unordered allele-set agreement for every displayed evidence variant.
- Record PLINK A1 orientation relative to COSI ALT. Reorient signed `r` into the declared allele orientation before interpretation.
- Generate the complete LD matrix/pair table first. Apply readability thresholds only in the static plot.
- Never retain or copy individual-level genotypes into the packet.

### 7. Draw the three-panel figure

Use a shared x-axis and deterministic theme:

1. **Regional evidence** — focal GWAS signed Z background with context-specific eQTL evidence. Draw a dashed connector only when the same allele-aligned SNP has both GWAS and eQTL Z. Keep gene-level direction in the subtitle/annotation, not encoded as a variant-level claim.
2. **LD triangles** — draw each displayed pair with two segments through its midpoint. Scale or color by signed or absolute LD as declared. Retain dense pairs in the underlying table even when omitted by a readability rule.
3. **Gene track** — aligned GRCh38 gene bodies, TSS ticks, nonoverlapping labels, and a clear focal-gene highlight.

Export editable SVG, vector PDF, and a 600-dpi PNG review image. Inspect the raster and rendered PDF for clipping, label collisions, unreadable legends, and misleading empty space.

### 8. Build and execute the review notebook

- Generate or edit `<GENE>_modality_ggplot.ipynb` with the R kernel.
- Keep data construction in the builder; let the notebook read saved intermediates, reproduce the final plot, show evidence tables, and state limitations.
- Include raw result paths, builder path, and notebook-ready intermediate paths in a concise provenance section.
- Execute top-to-bottom with no error outputs and save execution counts.
- Do not start the workflow with a Jupyter command. Build inputs and notebook source first, then execute the notebook as validation.

### 9. Validate before reporting completion

Require all of the following:

- Current canonical focal rows and selected contexts are unique and traceable.
- Every displayed CS variant comes from the declared saved CS or a visibly distinct sensitivity/non-CS set.
- Missing GWAS/eQTL values remain missing, never zero.
- Every displayed evidence variant maps exactly to the LD reference.
- Raw LD contains all `n(n-1)/2` unordered pairs for `n` displayed variants.
- Every LD triangle uses two midpoint segments.
- The focal GTF record is present exactly once.
- Figure/table counts match.
- Notebook executes without errors.
- Input and artifact manifests contain paths, sizes, timestamps, and hashes where practical.

Run [validate_case_study.py](scripts/validate_case_study.py) for the portable packet checks, then retain locus-specific scientific assertions in the R builder and notebook.

## Completion report

Report:

- exact notebook and SVG/PDF/PNG paths;
- focal GWAS, plotted contexts, window, and LD reference;
- retained CS, sensitivity, and non-CS context counts;
- canonical gene-level direction and INTACT PP for each plotted context;
- omitted contexts and why;
- validation status and reproduction commands;
- interpretation limitations, especially allele orientation, failed fine-mapping, and sensitivity evidence.

Do not describe the plot as proof of a shared causal variant or mechanism.
