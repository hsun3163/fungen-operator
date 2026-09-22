# fungen-operator

Functional-genomics operator skills and the retained history of attempts to make agent work reproducible, scoped, and verifiable.

This repository incorporates the original `hsun3163/runner-skills` Git history and refreshes its skill files from the local installation on 2026-09-20. The original repository remains available.

## Current skill collection

All locally installed `cosi-*` and `xqtl-*` skills are included, along with the common runner and workflow-support skills. Each folder contains its original instructions and available templates, references, scripts, and agent metadata.

- [debug-pipeline](skills/debug-pipeline/SKILL.md)
- [snakemake-sos-parser](skills/snakemake-sos-parser/SKILL.md)
- [cosi-locus-case-study](skills/cosi-locus-case-study/SKILL.md)
- [cosi-locus-zoom](skills/cosi-locus-zoom/SKILL.md)
- [cosi-notebook](skills/cosi-notebook/SKILL.md)
- [cosi-run](skills/cosi-run/SKILL.md)
- [cosi-runner](skills/cosi-runner/SKILL.md)
- [cosi-sketch-ld](skills/cosi-sketch-ld/SKILL.md)
- [cosi-weight-scan](skills/cosi-weight-scan/SKILL.md)
- [cosi-workflow-edit](skills/cosi-workflow-edit/SKILL.md)
- [human-runner](skills/human-runner/SKILL.md)
- [intact-gene-query](skills/intact-gene-query/SKILL.md)
- [lsf-queue-move](skills/lsf-queue-move/SKILL.md)
- [record-handoff](skills/record-handoff/SKILL.md)
- [sos-status-sampler](skills/sos-status-sampler/SKILL.md)
- [sumstat-munger](skills/sumstat-munger/SKILL.md)
- [todoist-task-completion](skills/todoist-task-completion/SKILL.md)
- [xqtl-runner](skills/xqtl-runner/SKILL.md)
- [xqtl-snakemake-analysis](skills/xqtl-snakemake-analysis/SKILL.md)

## Earlier attempts and reviews

These files preserve earlier approaches and critiques, including attempts the owner describes as unsuccessful at taming agent behavior. Inclusion does not establish that every archived skill failed, and the reviews are historical assessments rather than newly reproduced evaluations.

- [reproducible-project-work](archive/reproducible-project-work/SKILL.md): earlier general reproducibility rules, references, and artifact templates.
- [human-runner backup](archive/human-runner/SKILL.md.orig) and [legacy references](archive/human-runner/archive/legacy-references/): retained earlier text and supporting material.
- [xqtl-route3-analysis](archive/xqtl-route3-analysis-20260821/SKILL.md): retired Route3 approach, including both original and retired-active references and scripts.
- [snakemake-lsf-triage](archive/snakemake-lsf-triage/SKILL.md): earlier memory-maintained debugging guidance.
- [reproducibility reviews](archive/reproducibility-reviews/): retained audit prompt and critical reviews, including a proposed replacement embedded in `latest-response.md`.

## Session insights analysis

The [2026-09-22 session insights analysis](docs/session_insights_analysis_20260922.md) interprets the 60-day, 100-thread-limit report for this project. It records verified report errors, overlapping COSI procedures, and proposed incident-based evaluations. Its recommendations are analysis, not changes to the active operating policy.

## Use and interpretation

Copy selected folders from `skills/` into your agent's skill directory, retaining their supporting files. Apply `human-runner` before a domain runner. Archived files are retained for study and comparison; do not install the whole archive as a combined instruction set.

The collection preserves different generations of operating policy. Their instructions can conflict: for example, `xqtl-runner` requires an exact-graph dry-run, while `cosi-runner` forbids adding a dry-run stage. Select the skill appropriate to the task and follow the applicable instruction hierarchy rather than combining all rules indiscriminately.

These are site-specific Minerva skills. Paths, environments, queue settings, project references, and historical examples are preserved. Adapt copied notebook templates to the intended run before execution; never execute the bundled templates directly. Analysis datasets and external workflow implementations are not bundled.

## Provenance

[Source manifest](docs/source-manifest.tsv) records each imported file's original location relative to the source user's home directory and SHA-256 digest. Imported files are preserved byte-for-byte. Generated caches are excluded. Source paths describe provenance and are not portable runtime dependencies supplied by this repository.
