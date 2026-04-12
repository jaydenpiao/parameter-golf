#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/config.sh"

CONFIG_PATH="${1:?usage: scripts/check_metric.sh <config> <log> <source>}"
LOG_PATH="${2:?usage: scripts/check_metric.sh <config> <log> <source>}"
SOURCE_PATH="${3:?usage: scripts/check_metric.sh <config> <log> <source>}"

load_config "${CONFIG_PATH}"

python3 "${SCRIPT_DIR}/collect_summary.py" \
  --config "${CONFIG_PATH}" \
  --log "${LOG_PATH}" \
  --source "${SOURCE_PATH}" >/dev/null

python3 - "${SOURCE_PATH}" <<'PY'
from pathlib import Path
import re
import sys

source = Path(sys.argv[1]).read_text()
required_markers = [
    "sentencepiece",
    "glob.glob",
    "sorted(",
]
for marker in required_markers:
    if marker not in source:
        raise SystemExit(f"metric check failed: missing source marker {marker!r}")

if "base_bytes_lut" not in source and "build_sentencepiece_luts" not in source:
    raise SystemExit("metric check failed: missing tokenizer byte accounting markers")

suspicious = [
    r"/\s*\(log\(2\)\s*\*\s*3\.[0-9]+\)",
    r"/\s*3\.[0-9]+",
    r"bits_per_token\s*/\s*3\.[0-9]+",
]
for pattern in suspicious:
    if re.search(pattern, source):
        raise SystemExit(f"metric check failed: suspicious hardcoded bytes-per-token pattern {pattern}")

print("metric check passed")
PY
