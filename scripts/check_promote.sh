#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/config.sh"

CONFIG_PATH="${1:?usage: scripts/check_promote.sh <config> <log> <source>}"
LOG_PATH="${2:?usage: scripts/check_promote.sh <config> <log> <source>}"
SOURCE_PATH="${3:?usage: scripts/check_promote.sh <config> <log> <source>}"

load_config "${CONFIG_PATH}"

python3 "${SCRIPT_DIR}/check_config_support.py" \
  --config "${CONFIG_PATH}" \
  --source "${SOURCE_PATH}"

"${SCRIPT_DIR}/check_metric.sh" "${CONFIG_PATH}" "${LOG_PATH}" "${SOURCE_PATH}"

SUMMARY_PATH="${REPO_ROOT}/results/${RUN_ID}/summary.json"
RUN_DIR="${REPO_ROOT}/results/${RUN_ID}"

"${SCRIPT_DIR}/check_artifact.sh" "${SUMMARY_PATH}"
"${SCRIPT_DIR}/check_legality.sh" "${RUN_DIR}" "${SOURCE_PATH}"

python3 - "${SUMMARY_PATH}" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text())
tolerance = 1.0

if float(summary["train_seconds"]) > 600 + tolerance:
    raise SystemExit(
        f"promotion check failed: train_seconds={summary['train_seconds']} exceeds 600s + {tolerance}s tolerance"
    )
if float(summary["eval_seconds"]) > 600 + tolerance:
    raise SystemExit(
        f"promotion check failed: eval_seconds={summary['eval_seconds']} exceeds 600s + {tolerance}s tolerance"
    )
if not str(summary.get("git_sha", "")).strip():
    raise SystemExit("promotion check failed: missing git_sha")
if not str(summary.get("repro_command", "")).strip():
    raise SystemExit("promotion check failed: missing repro_command")
if summary.get("git_dirty") is not False:
    raise SystemExit("promotion check failed: summary.git_dirty must be false")

print("promotion check passed")
PY
