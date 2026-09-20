# Route3 Workflow Contract

## Contents

1. Source hierarchy
2. Canonical stage graph
3. Shared and context-specific data
4. Completion checks
5. Scientific invariants

## Source Hierarchy

The applicable `AGENTS.md` is the controlling harness and execution contract. For scientific workflow semantics, use this precedence when implementations disagree:

1. canonical mini-protocol wrapper under `./xqtl-protocol/pipeline/`;
2. lower-level notebook/script invoked by that wrapper within `./xqtl-protocol/`;
3. source Snakemake path within `./xqtl-protocol/`, where one exists;
4. renovated Route3 notebook and rule;
5. MESA config and launch wrappers.

Do not use `./xqtl-renovated/xqtl-protocol/` as semantic authority unless the user explicitly scopes the task to that checkout. Explicitly report drift instead of silently choosing the renovated behavior.

## Canonical Stage Graph

### Expression

Canonical wrapper: `./xqtl-protocol/pipeline/bulk_expression.ipynb`.

Preserve the selected assay's normalization, filtering, outlier handling, naming, and sample columns. A Route3-ready phenotype BED is not equivalent to raw counts or FASTQ input. State which level is being reused.

### Shared genotype

Canonical wrapper: `./xqtl-protocol/pipeline/genotype_preprocessing.ipynb`.

Preserve distinct stages:

1. per-chromosome VCF preparation/QC;
2. VCF-to-PLINK conversion;
3. chromosome merge;
4. merged-genotype QC;
5. chromosome partition/manifest generation.

The MESA WGS genotype is shared across ancestry and assay contexts. Do not duplicate these stages per context unless the input genotype universe actually differs.

Validate PLINK as a trio: `.bed`, `.bim`, and `.fam`. A `.bed` marker or symlink alone is not a genotype dataset.

### Context sample QC and PCA

Canonical intent spans genotype, phenotype, and covariate wrappers in `./xqtl-protocol/pipeline/`.

Preserve distinct stages:

1. genotype/phenotype sample matching;
2. KING kinship inference and unrelated-sample selection;
3. unrelated-sample variant QC/pruning;
4. related-sample extraction using the already selected variants and sample-level missingness only;
5. PCA on unrelated samples;
6. projection of related samples;
7. PCA/covariate merge.

Do not apply unrelated-sample MAC/MAF/HWE filters again to a small related subset. The source related branch extracts selected variants and applies sample missingness filtering.

### Phenotype coordinates and chromosome split

Canonical wrapper: `./xqtl-protocol/pipeline/phenotype_preprocessing.ipynb`.

Preserve the active source annotation convention. Do not silently switch to a different TSS interval convention. Produce a coordinate-sorted, bgzip-compressed, tabix-indexable BED before chromosome fan-out. Preserve metadata columns such as `#chr`, `start`, `end`, `ID`, and `strand`; sample columns begin after all metadata columns.

Validate the chromosome manifest against actual files. Absence of one chromosome can be biologically legitimate only if the input has no rows for it; document that fact rather than fabricating an empty result.

### Covariates

Canonical wrapper: `./xqtl-protocol/pipeline/covariate_preprocessing.ipynb`.

Preserve distinct stages:

1. configured biological/technical covariates;
2. genotype principal components;
3. sample intersection and orientation;
4. Marchenko-Pastur phenotype-PC selection/residualization inputs where configured;
5. final analysis covariate matrix.

Matrix operations match samples by identifiers; phenotype row ordering is not a substitute for sample-column alignment.

### Association testing

Canonical wrapper: `./xqtl-protocol/pipeline/qtl_association_testing.ipynb`.

Preserve chromosome fan-out and final significance fan-in. TensorQTL cis windows are measured around the phenotype position according to the active phenotype-coordinate contract. A configured `window=1000000` means plus/minus 1 Mb, a 2 Mb span before chromosome-boundary truncation.

Validate per chromosome:

- nominal pairs/parquet output;
- compressed/indexed pair output where configured;
- regional output and index;
- final regional-significance table and summary.

### Fine mapping and TWAS weights

Canonical wrapper: `./xqtl-protocol/pipeline/2_finemapping.ipynb`.

Preserve region-level fan-out. Small-sample correction is a configured scientific option and must be recorded in provenance. Do not infer it from sample size after results already exist.

Validate each expected region independently. Distinguish:

- successful model with substantive result;
- valid source-defined no-result record;
- missing output;
- malformed/tiny error object;
- stale output generated with different options.

## Shared And Context-Specific Data

Shared:

- raw WGS VCFs;
- merged/QCed genotype;
- genotype chromosome manifest.

Context-specific:

- phenotype BED and samples;
- sample overlap and ancestry subset;
- kinship split, PCA projection, and covariates;
- phenotype chromosome manifest;
- TensorQTL outputs;
- SuSiE/TWAS outputs.

## Completion Checks

| Stage | Required evidence |
| --- | --- |
| VCF QC | every expected chromosome output exists and is readable |
| PLINK merge/QC | nonempty BED/BIM/FAM trio and expected sample/variant counts |
| Genotype split | manifest rows map to readable chromosome PLINK trios |
| Sample match | nonempty overlap files with expected identifiers |
| KING | kinship output plus materialized related/unrelated datasets or valid empty-related branch |
| PCA/covariates | model/projection artifacts and final covariate matrix with matched samples |
| Phenotype split | manifest, all listed BED.gz files, and valid indexes |
| TensorQTL | all chromosome outputs plus final significance outputs before `.done_cis` |
| SuSiE/TWAS | expected-region accounting plus both output families before `.done_susie_twas` |

## Scientific Invariants

- Never change filters merely to make a stage pass.
- Never reinterpret an empty biological subset as a corrupt file without checking the source branch contract.
- Never mix SSC and non-SSC result trees without explicit provenance.
- Never use a downstream result to validate a mismatched upstream sample universe.
- Never alter coordinate conventions, cis windows, allele orientation, or sample alignment silently.
