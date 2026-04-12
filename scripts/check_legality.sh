#!/usr/bin/env bash

set -euo pipefail

RUN_DIR="${1:?usage: scripts/check_legality.sh <results/run-id> [source] }"
SOURCE_PATH="${2:-}"
LEGALITY_PATH="${RUN_DIR}/legality.json"

python3 - "${LEGALITY_PATH}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(
        "legality check failed: missing legality.json. Start from results/legality.template.json"
    )

data = json.loads(path.read_text())
required = [
    "track",
    "reviewer",
    "reviewed_at",
    "condition_1",
    "condition_2",
    "condition_3",
    "condition_4",
    "no_prequant_ttt_on_val",
    "no_rescoring",
]
for key in required:
    if key not in data:
        raise SystemExit(f"legality check failed: missing field {key}")

for key in required[3:]:
    check = data[key]
    if not isinstance(check, dict):
        raise SystemExit(f"legality check failed: {key} must be an object")
    if check.get("status") is not True:
        raise SystemExit(f"legality check failed: {key} is not approved")
    if not str(check.get("evidence", "")).strip():
        raise SystemExit(f"legality check failed: {key} is missing evidence")

print("legality checklist passed")
PY

if [[ -n "${SOURCE_PATH}" && -f "${SOURCE_PATH}" ]]; then
  if rg -n "score-after-adapt|rescor|second pass|oracle" "${SOURCE_PATH}" >/dev/null 2>&1; then
    echo "legality check warning: source contains suspicious terms; inspect manually" >&2
  fi
fi
