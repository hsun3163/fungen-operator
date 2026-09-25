# Sourced by non-interactive bash inside sbx. The sentinel stops nested sbx calls from re-sourcing it.
if [ -z "${_SANITIZE_BASH_ENV_LOADED:-}" ]; then
  _SANITIZE_BASH_ENV_LOADED=1
  case "${SANITIZE_PREV_BASH_ENV:-}" in
    ""|*/bash_env.sh) ;;
    *) [ -f "$SANITIZE_PREV_BASH_ENV" ] && . "$SANITIZE_PREV_BASH_ENV" ;;
  esac
  if ! declare -F conda >/dev/null 2>&1 && [ -n "${CONDA_EXE:-}" ]; then
    _sl_conda_sh="$(dirname "$(dirname "$CONDA_EXE")")/etc/profile.d/conda.sh"
    [ -f "$_sl_conda_sh" ] && . "$_sl_conda_sh"
    unset _sl_conda_sh
  fi
fi
