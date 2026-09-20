---
name: cosi-notebook
description: Create or edit COSI Jupyter notebooks, plotting notebooks, notebook-ready analysis inputs, and R-kernel exploratory analysis. Use when the user says "notebook" in the COSI project, asks for plotting notebooks, wants notebook-contained analysis code, or asks to document raw/intermediate paths used by a figure.
---

# COSI Notebooks

Use COSI notebook conventions unless the user explicitly asks otherwise.

## Notebook Format

- Create Jupyter notebooks (`.ipynb`) with an R kernel.
- Do not create `.qmd` or `.Rmd` for requests phrased as "notebook".
- Keep plotting notebooks focused on plotting code and the immediate inputs they read.

## Plotting Notebook Provenance

For a plotting notebook, include a short markdown section listing:

1. Raw result path(s).
2. Code path(s) that process raw results into notebook-ready inputs.
3. Intermediate saved input file(s) read directly by the notebook.

## COSI R Defaults

- Prefer tidyverse and ggplot2 for ordinary wrangling/plotting.
- Use data.table for inputs larger than about 1 GB.
- Prefer `ggrepel` for labels and avoid covering plotted points unless requested.
- Preserve existing local figure style and output paths when revising established COSI plots.
