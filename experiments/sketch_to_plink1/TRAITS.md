# Covariates and phenotypes for the fixed-bin fixture

This simulation adds nontrivial synthetic content to the theta = 1 behavioral genotype object. Its inputs are the existing PLINK1 fixture and the prepared region/variant metadata. The generator reads those files directly; participant-level phenotype or covariate sources are unnecessary.

The native entry point is `simulate_traits.py`, with seed `20260924`. All 10,000 rows follow the exact FAM order and retain the `SYN_EUR_` identifiers. Outputs are under `output/sketch_to_plink1/behavioral_fixture/traits/`.

## Covariates

The 12-column analysis matrix contains age, centered age squared, binary synthetic sex, BMI, three batch indicators, cell fraction, log library size, and three genotype PCs. Continuous terms are standardized using sample standard deviations; binary terms are 0/1. Batch A is the reference. The four batches contain 10%, 20%, 30%, and 40% of samples. The intercept is supplied by the downstream regression, and the combined design must have full rank.

PCs come from an exact eigendecomposition of the covariance of 256 evenly spaced common SNPs in this artificial genotype matrix; their signs are anchored to the largest absolute loading. They are fixture genotype axes. Batch assignment correlates with PC1; age correlates with PC1 and batch; BMI depends on age, sex, and batch; cell fraction depends on age, PC2, and batch; library size depends on batch and cell fraction. The raw synthetic measurements are retained alongside the analysis matrix.

## Phenotypes and ground truth

There are 40 quantitative traits across the 20 retained regions: one genetic signal and one null trait per region. Ten signal traits have one causal variant and ten have two. Causal variants have MAF >= 0.05; each two-variant pair has absolute correlation below 0.2 and lies within 500 kb. Trait coordinates use the primary causal position as a synthetic molecular-trait anchor, with `chr`-prefixed chromosomes matching canonical phenotype preprocessing. IDs are artificial, rather than annotated genes.

Let C be the analysis covariates, X = [1,C], and g_j the signed weighted sum of causal ALT dosages. The generated trait is

```text
Y_j = (C - mean(C)) gamma_j
      + k_j [g_j - X least_squares(X, g_j)]
      + sigma_j epsilon_j.
```

The covariate component has sample variance 0.25. Signal traits cycle through conditional genetic-component variances 0.03, 0.06, and 0.12; null traits use zero. k_j scales the genetic residual to that variance. sigma_j² = 1 - 0.25 - genetic variance. Epsilon is an independent standard Gaussian draw: it is neither orthogonalized nor selected based on association outcomes. The nominal conditional genetic fractions are genetic variance / 0.75; finite-sample totals and noise covariances are measured, rather than assumed to equal their expectations.

The projection removes covariance between the designated genetic and covariate components. It still has an explicit ordinary linear representation with raw ALT dosages: `covariate_model_truth.tsv` records the effective intercept and covariate coefficients, and `causal_truth.tsv` records per-ALT causal effects. The component table retains the actual covariate, genetic, and noise vectors for each phenotype. Opposing causal effects and alternating overall signs make direction checks meaningful.

## Files and verification

| File | Contents |
|---|---|
| `covariates.tsv` | FID, IID, 12 analysis covariates; native PLINK input |
| `covariates.cov.gz` | Covariates in rows, `#id` then samples as columns; canonical xQTL reader input |
| `sample_metadata.tsv` | Synthetic age, sex, BMI, batch, cell fraction and log library size |
| `phenotypes.tsv` | FID, IID, 40 quantitative traits; native PLINK input |
| `phenotypes.bed.gz` and `.tbi` | Coordinate-sorted BGZF phenotype BED, `#chr/start/end/ID` then samples |
| `causal_truth.tsv` | Causal IDs, positions, alleles, MAFs and signed per-ALT effects |
| `phenotype_truth.tsv` | Declared and observed component variances and covariances |
| `covariate_model_truth.tsv` | Effective coefficients in the direct genotype-plus-covariate model |
| `phenotype_components.tsv.gz` | Exact generated component vectors, indexed by synthetic sample |
| `pc_variants.tsv` | SNPs defining the three fixture PCs |
| `regional_association_qc.tsv.gz` | Adjusted single-variant regressions within each source region |
| `joint_causal_recovery.tsv` | Joint causal effect estimates, directions, SEs and P values |
| `native_plink_association_qc.tsv` | Independent native PLINK checks on every causal SNP against all traits |
| `qc_summary.json`, `provenance.json` | Alignment, missingness, rank, signal/null diagnostics, commands, seed, source versions and hashes |

The generator loads the saved BED/covariate files through `load_phenotype_bed` and `load_covariates` in the canonical xQTL `TensorQTL.py`, verifies every sample and value, and reads every trait back through the tabix index. PLINK 1.9 independently tests all planted variants with all traits and all supplied covariates; its local effect estimates are compared with adjusted OLS. Joint regression tests whether both effects in each two-variant trait can be recovered. Null P-value fractions and regional Bonferroni hits are reported as diagnostics, including any chance positives.

**Answerability:** this fixture can establish whether planted effects are recoverable in its artificial matrix and whether genotype/covariate/phenotype inputs align. It carries the behavioral genotype object's scope: faithful source-cohort LD, biological realism, and a complete scientific mini-protocol execution remain separate questions. Scientific integration fixtures use separately generated synthetic or public genotypes as specified in `docs/benchmark.md`.

## Verified result, 2026-09-23

LSF job `270117742` completed the generation and verification command in [RUN.md](RUN.md).

| Check | Observed result |
|---|---:|
| Samples / covariates / quantitative phenotypes | 10,000 / 12 / 40 |
| Genetic signal / null phenotypes | 20 / 20 |
| Model rank including intercept | 13 |
| Design condition number | 11.75 |
| Missing covariate or phenotype entries | 0 |
| Joint causal effects with correct direction | 30 / 30 |
| Joint causal effects with P < 5E-8 | 30 / 30 |
| Largest causal P value | 7.29E-22 |
| Native PLINK association checks | 1,200 |
| Null regional tests with P < 0.05 | 5.93% of 20,000 |
| Null traits with a regional Bonferroni hit | 1 / 20 |

Every serialized sample ID matches the genotype FAM order. The canonical reader values match the generated arrays, every indexed trait is retrievable, and PLINK's regional effect estimates match the adjusted OLS estimates to its printed precision. Ground truth and null diagnostics are retained as observed, with no seed or effect adjustment after viewing results. The covariate, genotype, and phenotype components are complete; full fine-mapping or end-to-end scientific integration was outside this generation task.
