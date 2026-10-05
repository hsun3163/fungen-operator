#!/bin/bash

minerva_ollama_load_state() {
  local env_job_name="${MINERVA_OLLAMA_JOB_NAME-}"
  local env_remote_port="${MINERVA_OLLAMA_REMOTE_PORT-}"
  local env_local_port="${MINERVA_OLLAMA_LOCAL_PORT-}"
  local env_default_model="${MINERVA_OLLAMA_DEFAULT_MODEL-}"
  local env_real_bin="${MINERVA_OLLAMA_REAL_BIN-}"
  local env_socket_dir="${MINERVA_OLLAMA_SOCKET_DIR-}"
  local env_curl_bin="${MINERVA_OLLAMA_CURL_BIN-}"
  local host_tag

  MINERVA_OLLAMA_STATE_FILE="${MINERVA_OLLAMA_STATE_FILE:-$HOME/.codex/ollama-flash-next.env}"

  if [[ -f "$MINERVA_OLLAMA_STATE_FILE" ]]; then
    # shellcheck source=/dev/null
    source "$MINERVA_OLLAMA_STATE_FILE"
  fi

  MINERVA_OLLAMA_JOB_NAME="${env_job_name:-${MINERVA_OLLAMA_JOB_NAME:-codex-ollama-flash-next}}"
  MINERVA_OLLAMA_REMOTE_PORT="${env_remote_port:-${MINERVA_OLLAMA_REMOTE_PORT:-8889}}"
  MINERVA_OLLAMA_LOCAL_PORT="${env_local_port:-${MINERVA_OLLAMA_LOCAL_PORT:-11435}}"
  MINERVA_OLLAMA_DEFAULT_MODEL="${env_default_model:-${MINERVA_OLLAMA_DEFAULT_MODEL:-qwen3.8-flash-next:125b-a6b-q4_K_M}}"
  MINERVA_OLLAMA_REAL_BIN="${env_real_bin:-${MINERVA_OLLAMA_REAL_BIN:-$HOME/sunh14_project/conda/ollama-v0.34.4/bin/ollama}}"
  host_tag="$(hostname -s 2>/dev/null || echo unknown-host)"
  MINERVA_OLLAMA_SOCKET_DIR="${env_socket_dir:-${MINERVA_OLLAMA_SOCKET_DIR:-/tmp/$USER/ollama-tunnels/$host_tag}}"
  MINERVA_OLLAMA_CURL_BIN="${env_curl_bin:-${MINERVA_OLLAMA_CURL_BIN:-/usr/bin/curl}}"
}

minerva_ollama_local_url() {
  printf 'http://127.0.0.1:%s\n' "$MINERVA_OLLAMA_LOCAL_PORT"
}

minerva_ollama_local_curl() {
  env \
    -u http_proxy \
    -u https_proxy \
    -u HTTP_PROXY \
    -u HTTPS_PROXY \
    -u all_proxy \
    -u ALL_PROXY \
    "$MINERVA_OLLAMA_CURL_BIN" \
    --noproxy '*' \
    "$@"
}

minerva_ollama_default_model() {
  minerva_ollama_load_state
  printf '%s\n' "${CODEX_OLLAMA_MODEL:-$MINERVA_OLLAMA_DEFAULT_MODEL}"
}

minerva_ollama_use_local_url() {
  local local_url

  local_url="$(minerva_ollama_local_url)"
  export OLLAMA_HOST="$local_url"
  export OLLAMA_API_KEY="${OLLAMA_API_KEY:-ollama}"
  export no_proxy="${no_proxy:+$no_proxy,}127.0.0.1,localhost"
  export NO_PROXY="${NO_PROXY:+$NO_PROXY,}127.0.0.1,localhost"
}

minerva_ollama_local_ready() {
  local local_url

  local_url="$(minerva_ollama_local_url)"
  minerva_ollama_local_curl -sf --max-time 2 "${local_url}/api/tags" >/dev/null 2>&1
}

minerva_ollama_find_running_job() {
  local line
  local fallback

  minerva_ollama_load_state

  line="$(
    bjobs -u "$USER" -J "$MINERVA_OLLAMA_JOB_NAME" -o 'jobid stat exec_host' -noheader 2>/dev/null \
      | awk '
          $2 == "RUN" && $3 != "-" {
            host = $3
            sub(/.*\*/, "", host)
            print $1 "\t" host
          }
        ' \
      | sort -nr -k1,1 \
      | head -n1 \
      || true
  )"

  if [[ -z "$line" ]]; then
    fallback="$(
      bjobs -u "$USER" -J "$MINERVA_OLLAMA_JOB_NAME" -o 'jobid stat exec_host' -noheader 2>/dev/null \
        | head -n1 \
        || true
    )"
    if [[ -n "$fallback" ]]; then
      local jobid stat exec_host
      jobid="$(awk '{print $1}' <<<"$fallback")"
      stat="$(awk '{print $2}' <<<"$fallback")"
      exec_host="$(awk '{print $3}' <<<"$fallback")"
      echo "No running ${MINERVA_OLLAMA_JOB_NAME} job is ready. Latest job ${jobid} is ${stat} on ${exec_host:-no-host}." >&2
      echo "Start or wait for a job with: ~/minerva-codex-ollama.sh" >&2
    else
      echo "No ${MINERVA_OLLAMA_JOB_NAME} job found. Start one with: ~/minerva-codex-ollama.sh" >&2
    fi
    return 1
  fi

  MINERVA_OLLAMA_ACTIVE_JOB_ID="${line%%$'\t'*}"
  MINERVA_OLLAMA_ACTIVE_NODE="${line#*$'\t'}"
  export MINERVA_OLLAMA_ACTIVE_JOB_ID MINERVA_OLLAMA_ACTIVE_NODE
}

minerva_ollama_listener_pids() {
  ss -ltnp 2>/dev/null \
    | awk -v port="${MINERVA_OLLAMA_LOCAL_PORT}" '
        $4 ~ ":" port "$" {
          line = $0
          while (match(line, /pid=[0-9]+/)) {
            print substr(line, RSTART + 4, RLENGTH - 4)
            line = substr(line, RSTART + RLENGTH)
          }
        }
      ' \
    | sort -u
}

minerva_ollama_recycle_stale_local_port() {
  local pid
  local cmdline
  local found=0

  for pid in $(minerva_ollama_listener_pids); do
    [[ -n "$pid" ]] || continue
    cmdline="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
    case "$cmdline" in
      *"ssh "*"-L ${MINERVA_OLLAMA_LOCAL_PORT}:127.0.0.1:"*)
        kill "$pid" 2>/dev/null || true
        found=1
        ;;
    esac
  done

  if (( found )); then
    sleep 1
  fi
}

minerva_ollama_remote_ready() {
  ssh \
    -o BatchMode=yes \
    -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=accept-new \
    "$MINERVA_OLLAMA_ACTIVE_NODE" \
    "unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY; /usr/bin/curl -sf --max-time 5 http://127.0.0.1:${MINERVA_OLLAMA_REMOTE_PORT}/api/tags >/dev/null"
}

minerva_ollama_open_tunnel() {
  local socket="$1"

  rm -f "$socket"
  ssh \
    -f \
    -N \
    -M \
    -S "$socket" \
    -L "${MINERVA_OLLAMA_LOCAL_PORT}:127.0.0.1:${MINERVA_OLLAMA_REMOTE_PORT}" \
    -o BatchMode=yes \
    -o ConnectTimeout=5 \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveCountMax=10 \
    -o ServerAliveInterval=60 \
    -o StrictHostKeyChecking=accept-new \
    "$MINERVA_OLLAMA_ACTIVE_NODE"
}

minerva_ollama_wait_for_local() {
  local local_url="$1"
  local tries=0

  until minerva_ollama_local_curl -sf --max-time 2 "${local_url}/api/tags" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if (( tries >= 30 )); then
      return 1
    fi
    sleep 1
  done
}

minerva_ollama_ensure_connection() {
  local local_url
  local socket

  minerva_ollama_load_state

  if [[ -n "${OLLAMA_HOST:-}" ]]; then
    return 0
  fi

  if minerva_ollama_local_ready; then
    minerva_ollama_use_local_url
    return 0
  fi

  local_url="$(minerva_ollama_local_url)"
  minerva_ollama_find_running_job

  if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${MINERVA_OLLAMA_LOCAL_PORT}\$"; then
    minerva_ollama_recycle_stale_local_port
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${MINERVA_OLLAMA_LOCAL_PORT}\$"; then
      echo "Local port ${MINERVA_OLLAMA_LOCAL_PORT} is busy but not responding as Ollama." >&2
      echo "Free that port or set OLLAMA_HOST explicitly before running codex/ollama." >&2
      return 1
    fi
  fi

  mkdir -p "$MINERVA_OLLAMA_SOCKET_DIR"
  socket="${MINERVA_OLLAMA_SOCKET_DIR}/${MINERVA_OLLAMA_ACTIVE_NODE}_${MINERVA_OLLAMA_LOCAL_PORT}_${MINERVA_OLLAMA_REMOTE_PORT}.sock"

  if ! ssh -S "$socket" -O check "$MINERVA_OLLAMA_ACTIVE_NODE" >/dev/null 2>&1; then
    minerva_ollama_open_tunnel "$socket"
  fi

  if ! minerva_ollama_wait_for_local "$local_url"; then
    if minerva_ollama_remote_ready; then
      ssh -S "$socket" -O exit "$MINERVA_OLLAMA_ACTIVE_NODE" >/dev/null 2>&1 || true
      minerva_ollama_open_tunnel "$socket"
      if ! minerva_ollama_wait_for_local "$local_url"; then
        echo "Ollama server on ${MINERVA_OLLAMA_ACTIVE_NODE}:${MINERVA_OLLAMA_REMOTE_PORT} is healthy, but the local tunnel on ${local_url} did not come up." >&2
        echo "Retry from this host, or inspect the job with: bjobs -l ${MINERVA_OLLAMA_ACTIVE_JOB_ID}" >&2
        return 1
      fi
    else
      echo "Ollama tunnel is up but ${local_url}/api/tags is not responding." >&2
      echo "Inspect the job with: bjobs -l ${MINERVA_OLLAMA_ACTIVE_JOB_ID}" >&2
      return 1
    fi
  fi

  minerva_ollama_use_local_url
}
