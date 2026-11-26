#!/bin/sh
# Installed as /usr/lib/ollama/llama-server; Ollama's own binary is beside it as
# llama-server.ollama.
#
# Ollama 0.40.6 checks each GPU in a separate llama-server run with
# GGML_CUDA_INIT=1 and CUDA_VISIBLE_DEVICES set to the GPU's position among the
# job's GPUs (discover/runner.go, ml/device.go). CUDA reads that number against
# every GPU on the node. Where a job sees the whole node, as on BU SCC, the check
# for a job given GPU 3 opens GPU 0. When GPU 0 belongs to another job in
# Exclusive_Process mode, the check fails as busy and Ollama falls back to CPU.
# Point the check at the job's own GPU. serve passes the job's list in
# FUNGEN_JOB_CUDA_VISIBLE_DEVICES.
if [ "${GGML_CUDA_INIT:-}" = 1 ] && [ -n "${FUNGEN_JOB_CUDA_VISIBLE_DEVICES:-}" ]; then
    position=${CUDA_VISIBLE_DEVICES:-}
    case $position in
        ''|*[!0-9]*) ;;
        *)
            IFS=,
            for gpu in $FUNGEN_JOB_CUDA_VISIBLE_DEVICES; do
                if [ "$position" = 0 ]; then
                    CUDA_VISIBLE_DEVICES=$gpu
                    export CUDA_VISIBLE_DEVICES
                    break
                fi
                position=$((position - 1))
            done
            unset IFS
            ;;
    esac
fi
exec "$0.ollama" "$@"
