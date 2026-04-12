#!/usr/bin/env bash

set -euo pipefail

repo_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
}

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "missing required config variable: ${name}" >&2
    return 1
  fi
}

load_config() {
  local config_path="$1"
  if [[ ! -f "${config_path}" ]]; then
    echo "config not found: ${config_path}" >&2
    return 1
  fi

  set -a
  # shellcheck disable=SC1090
  source "${config_path}"
  set +a

  require_var CONFIG_NAME
  require_var TRACK
  require_var TOKENIZER_VARIANT
  require_var TARGET_HARDWARE_TIER
  require_var RESULTS_TAG
  require_var RUN_ID
  require_var DATA_PATH
  require_var TOKENIZER_PATH
  require_var VOCAB_SIZE
}
