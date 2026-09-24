# MWE progress — 2026-09-23

**Completed:** a fixed-bin PLINK1 genotype fixture, 12 nontrivial covariates, and 40 quantitative phenotypes, with deterministic generation, planted ground truth, exact sample alignment, and native PLINK verification.

**Design decision:** accurate sketch inversion is not a prerequisite for Fungen Operator. The reconstruction pilot failed its LD-preservation contract and is closed. The resulting fixed-bin object is suitable for type-aware, content-agnostic behavioral cases. Scientific mini-protocol integration uses separately generated synthetic or public genotype data.

## Delivered and verified

| Component | Completed result | Evidence |
|---|---|---|
| PLINK1 genotype | Fixed theta = 1; 10,000 synthetic samples; 20,000 variants across 20 regions on chr1, chr6, chr19, chr21 and chr22 | [Export metadata](../experiments/sketch_to_plink1/evidence/20260923/export.json) |
| Genotype format | PLINK 1.9 rewrote the BED byte-identically; 32 selected variants matched all 10,000 generated calls | [Round-trip verification](../experiments/sketch_to_plink1/evidence/20260923/roundtrip_verified.json) |
| Covariates | 12 columns: age, age squared, sex, BMI, three batch indicators, cell fraction, log library size and three genotype PCs | [Method and formats](../experiments/sketch_to_plink1/TRAITS.md) |
| Phenotypes | 40 quantitative traits: 10 single-causal, 10 two-causal and 20 null traits | [Phenotype truth](../experiments/sketch_to_plink1/evidence/20260923/traits/phenotype_truth.tsv) |
| Sample alignment | Exact agreement with all 10,000 FAM IDs; no missing covariates or phenotypes; full design rank 13 including intercept | [QC summary](../experiments/sketch_to_plink1/evidence/20260923/traits/qc_summary.json) |
| Planted signal | All 30 causal effects recovered with the correct direction and P < 5E-8; largest causal P = 7.29E-22 | [Joint effect recovery](../experiments/sketch_to_plink1/evidence/20260923/traits/joint_causal_recovery.tsv) |
| Native software check | 1,200 PLINK association checks; local effect estimates match adjusted OLS to printed precision | [Native PLINK results](../experiments/sketch_to_plink1/evidence/20260923/traits/native_plink_association_qc.tsv) |
| Null diagnostics | 5.93% of 20,000 regional null tests have P < 0.05; one of 20 null traits crosses its regional Bonferroni threshold | [QC summary](../experiments/sketch_to_plink1/evidence/20260923/traits/qc_summary.json) |

Covariates contain correlated demographic and technical effects, a nonlinear age term, and imbalanced batch sizes of 1,000/2,000/3,000/4,000. Genotype PCs are axes of the artificial fixture. Signal traits have genetic-component variances 0.03, 0.06 or 0.12, a covariate-component variance of 0.25, and independent Gaussian noise. Two-causal traits include opposing signed effects. The seed is **20260924**. The realized null result is retained; generation was not adjusted after inspecting association outcomes.

## Closed reconstruction experiment

The fitted theta = 1.4305555556 achieved weighted LD RMSE 0.114764 on chr22 development regions and 0.133228 on held-out regions, exceeding the provisional 0.10 gate. The theta = 1 baseline also failed the LD gate. Strong LD was attenuated, the fitted rule failed its HWE heterozygosity criterion, and a separate two-MAF-stratum extension also failed acceptance.

The pilot is [archived with source and evidence hashes](../archive/sketch_to_plink1_20260923/README.md). Further theta optimization is stopped. The fixed theta = 1 export is a separate behavioral fixture; its BED SHA256 is `cd48b88a48021b52e3ff4353557a3bcb1eb448c5eb1e3263bb230696b47cd235`.

## Reproduction and artifact locations

- [Exact commands and execution records](../experiments/sketch_to_plink1/RUN.md)
- [Fixed-bin exporter](../experiments/sketch_to_plink1/sketch_mwe.py)
- [Covariate/phenotype generator](../experiments/sketch_to_plink1/simulate_traits.py)
- [Trait equations, data dictionary and result table](../experiments/sketch_to_plink1/TRAITS.md)
- [Verification snapshots and hashes](../experiments/sketch_to_plink1/evidence/20260923/manifest.tsv)

Native LSF jobs **270113524** (genotype export) and **270117742** (traits and verification) completed successfully. The retained commands pin the runtime, random seed and BLAS thread count. The trait job's initial C++ runtime import failure and the adjustment to a uniform causal MAF cutoff of 0.05 are documented in `RUN.md`.

The generated data remain under this workspace-relative directory:

```text
output/sketch_to_plink1/behavioral_fixture/
    genotype.bed / genotype.bim / genotype.fam
    fixture_metadata.json
    traits/covariates.cov.gz
    traits/phenotypes.bed.gz / phenotypes.bed.gz.tbi
    traits/covariates.tsv / traits/phenotypes.tsv
    traits/causal_truth.tsv
    traits/qc_summary.json / traits/provenance.json
```

The workspace root is `/sc/arion/projects/load/users/sunh14/fungen-operator`. GitHub contains source, documentation, compact verification snapshots and the archived negative result. Generated data matrices and prepared sketch caches stay under ignored `output/`. Snapshot paths in JSON/TSV retain their original runtime locations for provenance.

## Remaining benchmark work

Connect the typed objects and realistic workflow states to the operator's behavioral scenarios and graders. Scientific integration tests require a separate genuinely synthetic/public PLINK fixture and execution of the real mini-protocol. This progress update establishes completed data generation and the stated reader/association checks; it does not establish full mini-protocol integration, fine-mapping performance, or source-cohort LD fidelity.
