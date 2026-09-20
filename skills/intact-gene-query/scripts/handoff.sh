#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

HANDOFF_DIR="$BASE_DIR/handoff"
SUMMARY_MD="$BASE_DIR/SUMMARY.md"
BUILD_SUMMARY="$BASE_DIR/skills/intact-gene-query/scripts/build_summary.sh"

if [[ ! -x "$BUILD_SUMMARY" ]]; then
  echo "Missing build_summary script at $BUILD_SUMMARY"
  exit 1
fi

mkdir -p "$HANDOFF_DIR"
ts="$(date +%Y%m%d_%H%M%S)"
out="$HANDOFF_DIR/${ts}.handoff.md"

bash "$BUILD_SUMMARY"

cp "$SUMMARY_MD" "$out"
echo "Wrote handoff: $out"
