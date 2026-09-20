---
name: cosi-weight-scan
description: Fast deterministic COSI OTTERS weight-root audits. Use when asked how many eQTL weight regions/models are complete, good, header-only, missing, failed, or left; especially for old-OTTERS/pecotmr rerun weight directories under hg38/*/results/weights. Runs the bundled scanner script instead of ad hoc filesystem counting.
---

# COSI Weight Scan

Use the bundled script; do not rewrite scan loops inline.

```bash
python /sc/arion/projects/load/users/sunh14/.codex/skills/cosi-weight-scan/scripts/scan_weight_root.py \
  --weight-root hg38/EUR_rerun/results/weights/STARNET_FC_liftover.ADSP.full.admixture85.EUR.LD_meta \
  --region-list hg38/EUR_rerun/results/weights/STARNET_FC_liftover.ADSP.full.admixture85.EUR.LD_meta/runlog/STARNET_FC_liftover.strict_noAPOE_noHLA.region_list.eqtl.tsv
```

It counts only final direct-cache model files:

`{weight_root}/{chr_start_end}/cache/{P0.001.txt,P0.05.txt,PRScs.txt,SDPR.txt,lassosum.txt}`

It intentionally excludes nested `method_work/`, `range.txt`, status logs, and temporary files.
