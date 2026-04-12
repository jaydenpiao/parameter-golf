#!/usr/bin/env bash

set -euo pipefail

SUMMARY_PATH="${1:?usage: scripts/check_artifact.sh <summary.json>}"

python3 - "${SUMMARY_PATH}" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text())
artifact = int(summary["artifact_bytes"])
code = int(summary["code_bytes"])
model = int(summary["model_bytes"])

if artifact != code + model:
    raise SystemExit(f"artifact check failed: artifact_bytes={artifact} but code+model={code + model}")
if artifact >= 16_000_000:
    raise SystemExit(f"artifact check failed: artifact_bytes={artifact} exceeds 16,000,000")

print(f"artifact check passed: {artifact} bytes")
PY
