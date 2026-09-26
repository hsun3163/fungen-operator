# Sketch to synthetic PLINK1: method and transfer experiment

Status: proposed experiment, 2026-09-23. No tuning or synthetic-genotype generation has run.

## Question and recommendation

Can one parameter selected on chromosome 22 produce synthetic integer genotypes with acceptable signed LD on held-out chromosomes?

Start with a frequency-preserving, rank-based three-category quantizer. Its single parameter changes the minor-allele homozygote frequency; theta = 1 is the ordinary Hardy–Weinberg equilibrium (HWE) quantile baseline. Test the hypothesis rather than assume that discretization can preserve continuous correlation. If the baseline is best, retain it without an unnecessary adjustable parameter.

This is a genotype-matrix benchmark, with synthetic pseudo-individuals. It does not reconstruct participants, phased haplotypes, pedigrees, or original sample size.

## 1. Inputs and decoding

Verified EUR root:

```text
/sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/3_Production/cosi_archive/COSI/hg38/ADSP_reference_panel/ADSP_sketch_reference/EUR/
```

Prefixes are `rss_ld_sketch/chr{c}/ADSP.R4.EUR.admixture85.chr{c}`. All 22 PGEN/PVAR/PSAM/AFREQ sets exist: B = 10,000, 13,888,847 variants in total. Each PGEN opened and passed a one-variant read; full integrity remains untested.

| Role | Quantities |
|---|---|
| Fixed experiment inputs | Source sketch, source state, common row order, N* = B = 10,000, seeds, regions, pair lists and weights, eligibility rules, parameter grid, acceptance criteria |
| Per-variant inputs | Supplied ALT frequency p_j, CHR/POS/ID/REF/ALT, encoding/orientation metadata, optional U_MIN/U_MAX |
| Global fitted quantity | theta in [0, 2], minor-allele homozygote-frequency multiplier |
| Derived quantities, not fitted parameters | Empirical ranks, category counts, rounding corrections, sample moments, correlations |
| Outputs | Synthetic ALT counts G* in {0,1,2}, PLINK1 files, allele map, exclusions, parameter freeze, metrics and provenance |

The stored PGEN values are scaled sketch dosages. Establish their allele orientation from the applicable generation and reading code before defining the target. If D is the positively scaled, ALT-oriented dosage, the usual inverse is

U_ij = U_MIN_j + (D_ij / 2)(U_MAX_j - U_MIN_j).

A minor-oriented loader may require a `2 - D` correction; establish that from the actual implementation and apply it exactly once. ALT_FREQS alone is not evidence that a particular PGEN reader needs a flip. Metadata joins use chromosome, position and alleles, with ID cross-checks; AFREQ and PVAR may have different row orders.

Positive per-column affine rescaling changes neither ranks nor Pearson correlation. Consequently, U_MIN/U_MAX are unnecessary for this method when the positive affine encoding and ALT orientation are established. Missing transforms become a blocker only if the stored representation is not known to be equivalent in this sense.

Use R_U = cor(U_ALT), with the same retained rows for every variant. This matches the inspected pecotmr 0.3.4 sample-correlation implementation on complete inputs. Do not silently replace it with rank correlation, r-squared, a thresholded matrix, or a corrected latent correlation. Distinguish sketch-estimated LD from unavailable original-genotype LD.

Several conda environments contain different pecotmr versions. The checked `py3.11` environment has pecotmr 0.3.4 and the documented `open_pgen`, `read_pgen`, and `compute_LD` helpers. Start there, validate the reader semantics, and pin the executable, library paths and versions. The companion prompt records the six observed installations and provenance lookup requirements.

## 2. One-dimensional transformation

Let m_j = min(p_j, 1-p_j). Orient the decoded column toward the minor allele:

X_ij = U_ij if p_j <= 1/2, and X_ij = -U_ij otherwise.

For theta in [0,2], define minor-allele count probabilities

q_2j(theta) = theta m_j^2,
q_1j(theta) = 2m_j - 2theta m_j^2,
q_0j(theta) = 1 - 2m_j + theta m_j^2.

They are nonnegative and sum to one for m_j in [0,1/2]. Also

E[C_j] = 2m_j,
Var(C_j) = 2m_j + 2theta m_j^2 - 4m_j^2.

At theta = 1, these are HWE probabilities. Theta changes homozygosity while preserving allele frequency. It is a synthetic-distribution parameter, not an estimate of biological inbreeding. Its implied heterozygosity departure is

F_j = 1 - q_1j / [2m_j(1-m_j)] = (theta - 1)m_j/(1-m_j).

Let r_ij be the ascending rank of X_ij among the B rows. Use a fixed, seeded row-order key to break dosage-quantization ties, shared across variants and theta. Reverse that key when reversing allele orientation, so exact opposite columns have reverse ranks. Never independently permute sample rows between variants or regions.

Use integer counts rather than floating-point quantile cutoffs:

```text
round_half_up(x) = floor(x + 0.5)
M_j  = round_half_up(2 B m_j)
n_2j = clip(round_half_up(B theta m_j^2), max(0, M_j-B), floor(M_j/2))
n_1j = M_j - 2 n_2j
n_0j = B - n_1j - n_2j
C_ij = 1[r_ij > n_0j] + 1[r_ij > n_0j+n_1j]
G*_ij = C_ij if p_j <= 1/2, else 2-C_ij
```

Thus the reconstructed ALT-frequency error relative to the supplied p_j is at most 1/(4B), or 2.5E-5 at B = 10,000. Finite-count clipping is a deterministic feasibility correction, not SNP-specific tuning. Record its incidence.

This is a column-wise empirical-quantile transformation, rather than a purely scalar function of U_ij. No per-SNP threshold is fitted against LD. Freeze B: changing synthetic sample size changes quantization and requires a separately labeled experiment.

Theta = 0 can make a balanced-frequency variant all heterozygous and hence monomorphic. Any candidate that makes a fixed eligible variant monomorphic is invalid; do not drop that variant from the candidate's loss. Input monomorphic or unrepresentable variants are identified before searching.

### Why this family

| Approach | Decision |
|---|---|
| Round/clamp stored 0–2 sketch dosages | Diagnostic baseline only: the storage scale does not encode allele probabilities |
| Affine or robust scaling followed by fixed rounding | Can change LD, but generally changes allele frequencies without a natural HWE baseline |
| Affine scaling, shifts or positive temperature followed by empirical quantiles | Same ranks and assignments: an ineffective tuning parameter |
| HWE-aware empirical quantiles | Required zero-tuning baseline, theta = 1 |
| One homozygosity multiplier | Selected experimental family: effective, one-dimensional, frequency preserving |
| Pair-specific latent-correlation calibration | Separate, more complex method; outside this first experiment |

Clipping creates ties and discards information; no clipping parameter is introduced. Exact allele frequency and exact HWE marginals already determine both quantile thresholds. A meaningful extra knob must relax those marginals, alter dependence, or introduce another mechanism. This proposal explicitly relaxes HWE while retaining allele frequency.

Thresholding changes Pearson correlation, and not every desired correlation is compatible with specified discrete marginals. These issues are established in [correlated ordinal simulation](https://epub.ub.uni-muenchen.de/12157/1/kaiser-tr-94-ordinal.pdf); allele-frequency dependence also constrains conventional LD statistics ([VanLiere and Rosenberg](https://rosenberglab.stanford.edu/papers/VanLiereRosenberg2008-TPB.pdf)). The proposed quantizer is an experiment, not a guarantee of LD recovery.

## 3. Objective and diagnostics

Use a theta-independent variant/pair universe. Primary scoring includes biallelic autosomal variants with finite variable sketch columns, valid unique metadata and expected synthetic minor-allele count 2B m_j >= 20. Variants below that threshold are a separately reported low-count stress set, not silently discarded from the inventory or export policy. Record SNP/indel status separately.

For each region, each SNP contributes at most 32 pairs with later SNPs within 1 Mb: up to 16 nearest neighbors and up to 16 uniformly sampled remaining candidates, using a fixed seed. Deduplicate unordered pairs. Keep every sampled pair, including weak LD, negative LD and cross-block pairs within the region. This defines bounded local coverage, not complete chromosome-wide LD.

Compute target signed correlations once. Partition the fixed edges by target |r| into [0,0.1), [0.1,0.5), and [0.5,1]. Define the single primary loss

L(theta) = sqrt{ (1/K) sum_regions [ (1/H_r) sum_nonempty_LD_bins mean_edges_in_bin (R_G(theta) - R_U)^2 ] }.

Here K is the number of regions and H_r the number of nonempty target-LD bins in region r. This fixed weighted RMSE gives regions and available LD regimes equal weight, so abundant near-zero pairs do not hide loss of strong LD. Save pair weights; do not recompute bins or weights from G*. Also report ordinary unweighted pair RMSE as a diagnostic.

Select the minimum primary loss; ties within 1E-6 go to theta closest to 1, then the smaller theta. No QC-weighted composite objective or validation-driven selection.

Report per-region, split, chromosome and fixed LD/MAF strata:

- Signed-r RMSE, bias and vector correlation; absolute-|r| attenuation for strong pairs.
- r-squared RMSE and vector correlation, explicitly using squares of the same signed correlations.
- ALT-frequency and MAF MAE/max error; same MAF does not detect an allele flip.
- Genotype proportions, departure from q(theta), heterozygosity departure from HWE; HWE p-values are descriptive only for constructed rows.
- Conversion rate, input exclusions and candidate-induced failures with denominators.
- Runtime, peak memory, read/write volume and tie frequency.

Use MAF groups <0.01, 0.01–0.05, and >=0.05, including all six unordered pair types and the separate low-count stress set. Undefined correlations are NA with reasons.

As a compact feasibility diagnostic, calculate pairwise attainable correlation bounds from the chosen three-category marginals by same-order and opposite-order quantile coupling. These pairwise bounds need not be jointly attainable. Keep the original target and loss even if a target exceeds its marginal bounds.

## 4. Development and held-out design

1. Select and freeze regions/variants using metadata and target-sketch summaries only, with deterministic seeds.
2. Development: eight disjoint chr22 regions, 500–2,000 variants each, targeting 1,000. Select two per low/high-LD × low/high-rare-variant-fraction quadrant; document coverage gaps.
3. Validation: twelve regions, three each on chr21, chr1, chr6 and chr19, covering the same regimes; include an eligible MHC region if available. Reserve fresh chr2/chr20 regions for any separate follow-up. Do not LD-prune or select on reconstructed outcomes.
4. Coarse grid: 17 values, 0, 0.125, ..., 2. Add up to eight points in the best neighboring interval if informative: at most 25 values total. The finite-count objective is piecewise constant; stop refinement on a plateau.
5. Freeze theta*, code/runtime/input identities, eligibility, regions, pairs, weights, B, seeds and acceptance contract. Validate only theta* and the prespecified theta = 1 baseline; never reopen tuning from validation.
6. Audit dense LD once at frozen theta on one prespecified development and one held-out subset, each capped at 500 variants. This assesses pair-sampling coverage, without retuning.

Use region-level bootstrap intervals for descriptive uncertainty, rather than treating millions of dependent pairs as independent observations. Report LD/MAF-stratified development-to-validation differences so changes in case mix are visible. A dozen held-out regions support sampled cross-chromosome transfer, not a proof about every genomic locus.

## 5. Execution and complexity

Prepare each region once. Cache integer ranks, per-variant metadata and counts, input-content fingerprints, and fixed target pairs/correlations/weights. Keep decoded projected matrices in memory only. Cache paths and content identities belong to the trial record.

One `jobs.tsv` contains region × theta × phase rows, dispatched as independent native LSF array jobs. Workers load prepared ranks and emit atomic results. One reducer verifies completeness/identities, aggregates the objective and appends refinement/validation jobs. Reuse matching completed results; scheduler acceptance alone is not completion.

Suggested result fields: phase, region_id, chromosome, theta, variant_count, pair_count, primary_rmse, unweighted_rmse, signed_r_correlation, r2_rmse, r2_correlation, alt_af_mae, maf_mae, max_af_error, conversion_rate, heterozygosity_error, runtime_s, peak_rss_mb, status, error_reason, input_hash, code_hash, seed.

| Work | Cost |
|---|---|
| Read and basic preprocessing | O(BP) |
| Rank preparation, once | O(P B log B) using comparison sorting |
| Discretization, per theta | O(BP) |
| Dense correlations, per theta | O(BP^2) time and O(P^2) output |
| Selected pairs, per theta | O(B \|E\|), evaluated in bounded chunks |
| T selected-pair evaluations | O(P B log B + B \|E\| + T B(P + \|E\|)) |
| With \|E\| <= kP, fixed k | O(P B log B + T B P k) |
| Working memory with pair chunks | O(BP + \|E\|), plus bounded temporary buffers |

With B, T and k fixed, selected-pair work approaches linear scaling in variant count. Ranking occurs once; genome-wide export uses one frozen theta. Benchmark actual I/O and BLAS costs. Cache ranks to avoid re-reading raw PGEN values per theta.

## 6. Acceptance and failure interpretation

These are provisional engineering thresholds, not biological standards. Calibrate only from development/downstream requirements and freeze before opening validation; later changes constitute a new experiment.

| Check | Initial criterion |
|---|---|
| Primary weighted RMSE | Development and pooled held-out <= 0.10 |
| Transfer degradation | Held-out minus development <= 0.03 and held-out/max(development,0.02) <= 1.25 |
| Regime coverage | Each held-out chromosome and sufficiently populated LD/MAF pair stratum RMSE <= 0.15; report sparse strata as insufficient evidence |
| Signed-r agreement | Held-out vector correlation >= 0.90, with undefined cases explicitly labeled |
| r-squared agreement | Held-out RMSE <= 0.10 |
| Strong-pair attenuation | Absolute mean bias in |r| for target |r| >= 0.5 <= 0.10 |
| Frequency preservation | Max ALT-frequency error <= 1/(4B) + 1E-10 relative to supplied frequencies |
| HWE sanity | For m >= 0.05, at least 95% of variants have relative heterozygosity error versus HWE <= 0.10; disclose all tails |
| Valid conversion | 100% of the predeclared eligible universe yields finite, nonconstant integer columns; zero silent omissions |
| File validity | Exact sample/variant/allele agreement after PLINK1 write/read round trip |

Require 1,000 pairs across three held-out regions for a stratum claim. QC validates the selected minimum-loss candidate; it does not supply extra optimization targets.

Distinguish three conclusions: transfer supported within tested scope; transfer not supported; not answerable because required inputs/execution/coverage failed. Similar but poor losses on development and validation establish transfer of a bad approximation, not acceptable LD preservation.

Diagnose encoding/allele errors, discrete feasibility, threshold attenuation, MAF/LD dependence, finite-row resolution, sketch uncertainty, ties/rounding, input quality and runtime/serialization separately. Original LD is unobserved here.

If a systematic MAF effect remains, the smallest follow-up is two global theta values for fixed m < 0.05 versus m >= 0.05. Evaluate all cross-stratum pairs under the actual mixed transformation. Fit only on chr22, preserve the failed single-theta result, and use previously untouched regions for confirmatory follow-up. Do not repeatedly reuse the first validation set as a new holdout. More general correlation calibration or haplotype generation is a separate method, not a quiet repair.

## 7. Products and provenance

Deliver selection records and exclusions, job manifest and resumable results, frozen parameters, loss curves, signed-LD scatter/residuals, LD/MAF/HWE QC, runtime/memory tables and the explicit transfer conclusion.

Write PLINK1 BED/BIM/FAM for finalized pilot regions with synthetic sample IDs and an explicit ALT/A1/A2 map. The BED contains selected integer calls, not automatic hardcalls from the original dosage PGEN. PLINK's dosage import and hardcall defaults are different operations ([PLINK 2 input documentation](https://www.cog-genomics.org/plink/2.0/input)); verify the files against the [PLINK1 format specification](https://www.cog-genomics.org/plink/1.9/formats#bed).

If the rule passes, apply it chromosome by chromosome to the supported eligible domain, preserving B, row identities, allele rules and theta. Label variants outside the primary MAC-supported domain separately. If it fails, retain experimental pilot files and the negative result; do not produce an accepted genome-wide release.

Use only sketches, permitted frequency/variant/block metadata and non-identifying provenance. Exclude original genotypes/VCFs, participant lists and W. Use new synthetic IDs. Synthetic output establishes neither formal privacy protection nor external-release authorization.

The operator-building task belongs to another session. This experiment changes neither that operator nor the shared xQTL scientific workflow. The companion `sketch_genotype_mwe_luna_prompt.md` is the standalone execution assignment.
