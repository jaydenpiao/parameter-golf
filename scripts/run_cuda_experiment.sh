#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/config.sh"

CONFIG_PATH="${1:?usage: scripts/run_cuda_experiment.sh <config> [train-script]}"
TRAIN_SCRIPT="${2:-train_gpt.py}"

load_config "${CONFIG_PATH}"

python3 "${SCRIPT_DIR}/check_config_support.py" \
  --config "${CONFIG_PATH}" \
  --source "${REPO_ROOT}/${TRAIN_SCRIPT}"

if ! command -v torchrun >/dev/null 2>&1; then
  echo "torchrun not found in PATH" >&2
  exit 1
fi

RESULT_DIR="${REPO_ROOT}/results/${RUN_ID}"
ARTIFACT_DIR="results/${RUN_ID}/artifacts"
mkdir -p "${RESULT_DIR}"
mkdir -p "${REPO_ROOT}/${ARTIFACT_DIR}"

if [[ ! -f "${RESULT_DIR}/legality.json" ]]; then
  python3 - "${REPO_ROOT}/results/legality.template.json" "${RESULT_DIR}/legality.json" "${TRACK}" <<'PY'
import json
import sys
from pathlib import Path

template = json.loads(Path(sys.argv[1]).read_text())
template["track"] = sys.argv[3]
Path(sys.argv[2]).write_text(json.dumps(template, indent=2) + "\n")
PY
fi

if [[ ! -d "${REPO_ROOT}/${DATA_PATH#./}" || ! -f "${REPO_ROOT}/${TOKENIZER_PATH#./}" ]]; then
  python3 "${REPO_ROOT}/data/cached_challenge_fineweb.py" \
    --variant "${TOKENIZER_VARIANT}" \
    --train-shards "${TRAIN_SHARDS:-1}"
fi

cat > "${RESULT_DIR}/command.sh" <<EOF
set -a
source ${CONFIG_PATH}
set +a
OUT_DIR=${ARTIFACT_DIR} torchrun --standalone --nproc_per_node=${NPROC_PER_NODE:-1} ${TRAIN_SCRIPT}
EOF

(
  cd "${REPO_ROOT}"
  OUT_DIR="${ARTIFACT_DIR}" torchrun --standalone --nproc_per_node="${NPROC_PER_NODE:-1}" "${TRAIN_SCRIPT}"
) | tee "${RESULT_DIR}/train.log"

python3 "${SCRIPT_DIR}/collect_summary.py" \
  --config "${CONFIG_PATH}" \
  --log "${RESULT_DIR}/train.log" \
  --source "${REPO_ROOT}/${TRAIN_SCRIPT}"

echo "run log: ${RESULT_DIR}/train.log"
echo "summary: ${RESULT_DIR}/summary.json"
