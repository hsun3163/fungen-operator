#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash skills/intact-gene-query/scripts/run_intact_gene_query.sh <GENE> [exact|contains]"
  exit 1
fi

GENE="$1"
MATCH_MODE="${2:-exact}"

if [[ "$MATCH_MODE" != "exact" && "$MATCH_MODE" != "contains" ]]; then
  echo "match mode must be one of: exact, contains"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

BUILD_SCRIPT="$BASE_DIR/analysis/build_intact_query_df.R"
QUERY_SCRIPT="$BASE_DIR/analysis/query_intact_gene.R"
NOTEBOOK_SCRIPT="$BASE_DIR/skills/intact-gene-query/scripts/generate_gene_query_notebook.py"
QUERY_DF="$BASE_DIR/analysis/intact_query_df.rds"
SUMMARY_TSV="$BASE_DIR/analysis/intact_query_df_file_summary.tsv"

discover_sources() {
  ls "$BASE_DIR"/hg38/*/results/*/*.ADSP.*/intact/*.ADSP.*.ADSP.*.intact.results.tsv 2>/dev/null | grep noQC || true
}

mapfile -t CURRENT_SOURCES < <(discover_sources)

if [[ "${#CURRENT_SOURCES[@]}" -eq 0 ]]; then
  echo "No INTACT noQC source files discovered."
  exit 2
fi

NEEDS_UPDATE=0
UPDATE_REASONS=()

if [[ ! -f "$QUERY_DF" || ! -f "$SUMMARY_TSV" ]]; then
  NEEDS_UPDATE=1
  UPDATE_REASONS+=("query_df_or_summary_missing")
fi

if [[ "$NEEDS_UPDATE" -eq 0 ]]; then
  SUMMARY_COUNT="$(tail -n +2 "$SUMMARY_TSV" | wc -l | tr -d '[:space:]')"
  if [[ "${#CURRENT_SOURCES[@]}" -ne "$SUMMARY_COUNT" ]]; then
    NEEDS_UPDATE=1
    UPDATE_REASONS+=("source_count_changed")
  fi
fi

if [[ "$NEEDS_UPDATE" -eq 0 ]]; then
  NEWEST_SOURCE=""
  for src in "${CURRENT_SOURCES[@]}"; do
    if [[ -z "$NEWEST_SOURCE" || "$src" -nt "$NEWEST_SOURCE" ]]; then
      NEWEST_SOURCE="$src"
    fi
  done
  if [[ "$NEWEST_SOURCE" -nt "$QUERY_DF" ]]; then
    NEEDS_UPDATE=1
    UPDATE_REASONS+=("source_newer_than_query_df")
  fi
fi

if [[ "$NEEDS_UPDATE" -eq 0 ]]; then
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT

  printf '%s\n' "${CURRENT_SOURCES[@]}" | sed "s#^$BASE_DIR/##" | sort > "$TMP_DIR/current_sources.txt"
  tail -n +2 "$SUMMARY_TSV" | cut -f2 | sort > "$TMP_DIR/summary_sources.txt"

  if ! diff -q "$TMP_DIR/current_sources.txt" "$TMP_DIR/summary_sources.txt" >/dev/null 2>&1; then
    NEEDS_UPDATE=1
    UPDATE_REASONS+=("source_file_set_changed")
  fi
fi

if [[ "$NEEDS_UPDATE" -eq 1 ]]; then
  echo "query_df update needed: ${UPDATE_REASONS[*]}"
  Rscript "$BUILD_SCRIPT"
else
  echo "query_df is up-to-date."
fi

Rscript "$QUERY_SCRIPT" "$GENE" "$MATCH_MODE"

python "$NOTEBOOK_SCRIPT" \
  --base-dir "$BASE_DIR" \
  --gene "$GENE" \
  --match-mode "$MATCH_MODE"
