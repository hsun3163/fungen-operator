#!/bin/bash
# Compatibility entrypoint for the retained native smoke job.
set -euo pipefail
project=${LS_SUBCWD:-$(pwd)}
exec python "$project/container/acceptance.py" staged \
  --root "${FUNGEN_AUDIT_DIR:?}" --image "${FUNGEN_IMAGE:?}" \
  --staged "${FUNGEN_STAGED_MODELS:?}"
