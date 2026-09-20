#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def sanitize_gene(gene: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", gene)


def get_helper_script() -> Path:
    candidates = [
        Path.home() / ".codex" / "skills" / "jupyter-notebook" / "scripts" / "new_notebook.py",
        Path("/hpc/users/sunh14/.codex/skills/jupyter-notebook/scripts/new_notebook.py"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not find jupyter-notebook helper script new_notebook.py")


def build_cells(gene: str, match_mode: str, tsv_filename: str) -> list[dict]:
    title = f"# INTACT Gene Query: {gene} ({match_mode})\n"
    return [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                title,
                "\n",
                "This notebook loads the saved gene query result and filters high-confidence rows.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "suppressPackageStartupMessages({\n",
                "  library(tidyverse)\n",
                "  library(data.table)\n",
                "})\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                f"result_path <- \"{tsv_filename}\"\n",
                "result_df <- fread(result_path)\n",
                "result_df\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "result_df_high_pp <- result_df[intact_pp > 0.8]\n",
                "result_df_high_pp\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "z_col <- if (\"best_z\" %in% names(result_df)) {\n",
                "  \"best_z\"\n",
                "} else if (\"Z_acat\" %in% names(result_df)) {\n",
                "  \"Z_acat\"\n",
                "} else {\n",
                "  stop(\"No z-score column found. Expected best_z or Z_acat.\")\n",
                "}\n",
                "\n",
                "plot_df <- as_tibble(result_df) %>%\n",
                "  mutate(\n",
                "    ad_eqtl = paste(gwas_name, eqtl_name, sep = \" + \"),\n",
                "    z_score = as.numeric(.data[[z_col]]),\n",
                "    highlight = if_else(\n",
                "      dplyr::coalesce(as.numeric(intact_pp), 0) >= 0.8,\n",
                "      \"intact_pp >= 0.8\",\n",
                "      \"intact_pp < 0.8\"\n",
                "    )\n",
                "  ) %>%\n",
                "  filter(!is.na(z_score), !is.na(ad_eqtl))\n",
                "\n",
                "ggplot(plot_df, aes(x = z_score, y = fct_reorder(ad_eqtl, z_score, .fun = max, na.rm = TRUE))) +\n",
                "  geom_point(aes(size = intact_pp, color = highlight), alpha = 0.9) +\n",
                "  scale_color_manual(values = c(\"intact_pp >= 0.8\" = \"red\", \"intact_pp < 0.8\" = \"grey60\")) +\n",
                "  labs(\n",
                f"    title = \"INTACT hits for {gene}\",\n",
                "    x = \"Z score\",\n",
                "    y = \"AD + eQTL\",\n",
                "    size = \"intact_pp\",\n",
                "    color = NULL\n",
                "  ) +\n",
                "  theme_bw() +\n",
                "  theme(axis.text.y = element_text(size = 9))\n",
            ],
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an R notebook for a saved INTACT gene query TSV."
    )
    parser.add_argument("--base-dir", required=True, help="COSI repository root")
    parser.add_argument("--gene", required=True, help="Gene query string")
    parser.add_argument(
        "--match-mode",
        default="exact",
        choices=["exact", "contains"],
        help="Gene matching mode",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    safe_gene = sanitize_gene(args.gene)

    tsv_path = (
        base_dir
        / "analysis"
        / "gene_query"
        / safe_gene
        / f"intact_query_gene_{safe_gene}_{args.match_mode}.tsv"
    )
    if not tsv_path.exists():
        raise FileNotFoundError(f"Query TSV does not exist: {tsv_path}")

    nb_path = tsv_path.with_suffix(".ipynb")
    helper_script = get_helper_script()
    nb_title = f"INTACT Gene Query {args.gene} ({args.match_mode})"

    subprocess.run(
        [
            "python",
            str(helper_script),
            "--kind",
            "experiment",
            "--title",
            nb_title,
            "--out",
            str(nb_path),
            "--force",
        ],
        check=True,
    )

    with nb_path.open("r", encoding="utf-8") as f:
        notebook = json.load(f)

    notebook["cells"] = build_cells(args.gene, args.match_mode, tsv_path.name)
    notebook["metadata"] = {
        "kernelspec": {
            "display_name": "R",
            "language": "R",
            "name": "ir",
        },
        "language_info": {
            "codemirror_mode": "r",
            "file_extension": ".r",
            "mimetype": "text/x-r-source",
            "name": "R",
            "pygments_lexer": "r",
            "version": "4.3.3",
        },
    }

    with nb_path.open("w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=2)
        f.write("\n")

    print(f"Saved notebook: {nb_path}")


if __name__ == "__main__":
    main()
