# Closed sketch-to-PLINK1 pilot

Closed on 2026-09-23 after the user accepted the negative result and selected a fixed-bin behavioral fixture. Further theta optimization is stopped.

The fitted single-theta rule (theta = 1.4305555556) had development/held-out weighted LD RMSE 0.114764/0.133228 against a 0.10 gate. The theta = 1 baseline also failed that LD gate. Strong LD was attenuated; the fitted rule also failed the HWE heterozygosity criterion. The separate two-MAF-stratum follow-up failed its acceptance gates. The experiment does not support faithful sketch-to-genotype reconstruction.

## Benchmark decision

- Behavioral cases use opaque objects identified as genotype data and realistic workflow states. Accurate sketch inversion is outside their pass/fail contract.
- A fixed theta = 1 quantization provides a PLINK1-shaped behavioral fixture, with explicit synthetic sample IDs and genotype type metadata.
- Scientific integration cases use genuinely synthetic or public PLINK genotypes and the real mini-protocol. Their scientific validity is established separately.

## Retained evidence

`manifest.tsv` gives SHA256 hashes and original paths for the source, design, parameter freeze, aggregate results, acceptance decisions, and pilot-format verification copied into this archive. The copied files are historical evidence and preserve their original content, including historical relative links and execution instructions. Use the live `experiments/sketch_to_plink1/RUN.md` for the fixed-bin export command.

Full caches, per-job results, figures, logs, and the original fitted pilot remain in place under `output/sketch_to_plink1/`. The original pilot prefix is `output/sketch_to_plink1/pilot/pilot`; its BED SHA256 is `36e3808271d5c2279de9f2964f563f225f0fe07cffacef26ce63dc1ef382c81e`. The fixed-bin fixture uses the separate prefix `output/sketch_to_plink1/behavioral_fixture/genotype`.
