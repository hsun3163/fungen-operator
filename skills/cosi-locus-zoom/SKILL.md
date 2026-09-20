---
name: cosi-locus-zoom
description: Create or revise COSI locus-zoom, regional association, APP-style locus, ca-SNP, snATAC co-accessibility, gene-track, and LD triangle plots. Use when Codex is asked to make, debug, update, or refactor locus-zoom figures, APP zoom plots, regional GWAS/eQTL visualizations, or LD triangle panels in the COSI project.
---

# COSI Locus-Zoom Plots

Use the established COSI visual structure unless the user explicitly asks for a different layout.

## Locus-Zoom Structure

Build locus-zoom plots as five vertically aligned panels:

1. GWAS signed `-log10(p)` scatter, with credible-set color, key marker vertical line, highlighted variant, and `ggrepel` labels when labels are needed.
2. eQTL signed `-log10(p)` scatter with the same coordinate system and key marker line.
3. ca-SNP PIP scatter with key marker line.
4. snATAC effect estimates with a zero baseline, highlighted TF targets when relevant, and co-accessibility arcs.
5. Gene track with gene body segments, TSS ticks, and gene labels.

Combine panels vertically with `cowplot::plot_grid` or the existing local plotting pattern. Keep genomic coordinates aligned across panels.

## LD Triangle

Use the two-segment triangle method for LD arcs:

```r
geom_segment(aes(x = pos1, xend = mid, y = 0, yend = R))
geom_segment(aes(x = mid, xend = pos2, y = R, yend = 0))
```

Do not replace this with a single curve unless the user asks for a different LD style.

## COSI Plotting Defaults

- Prefer tidyverse and ggplot2 for ordinary figure work; use data.table for large inputs.
- Use `ggrepel` for labels and avoid covering important points unless explicitly requested.
- Keep plotting notebooks self-contained: include a short markdown section listing raw result paths, processing script paths, and intermediate files read directly by the notebook.
- Preserve existing local figure style and paths when revising an established COSI plot.
