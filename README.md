# Runner skills

Three skills for operating existing research workflows through visible, reproducible commands.

| Skill | Purpose |
| --- | --- |
| [human-runner](skills/human-runner/SKILL.md) | Use the project-native execution path and retain a clear command and result trail. |
| [xqtl-runner](skills/xqtl-runner/SKILL.md) | Operate MESA, AIDA, and CARDIA through the shared xQTL Snakemake, SoS, and LSF workflow. |
| [cosi-runner](skills/cosi-runner/SKILL.md) | Operate COSI workflows from a visible operator notebook and YAML configuration. |

## Contents and use

Each directory under `skills/` is a complete skill folder. Copy the desired folders into your agent's skill directory, retaining their subdirectories. Apply `human-runner` before the domain-specific runner.

The skills and bundled operator notebook templates are preserved from the local skill installation. Historical archives and backup files are excluded. This repository contains instructions and templates, not the analysis workflows, environments, or research datasets.

The domain runners target an existing Minerva environment and retain site-specific paths, queues, project names, and historical examples. Follow each skill's instructions to adapt its notebook copy and configuration to the intended run before execution. Never execute the bundled templates directly.

The runners have distinct execution contracts: xQTL requires a successful exact-graph dry-run before production; COSI uses its documented production submission path without adding a dry-run stage.
