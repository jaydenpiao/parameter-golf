#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/config.sh"

CONFIG_PATH="${1:-${REPO_ROOT}/configs/local_mlx_smoke.env}"
load_config "${CONFIG_PATH}"

RESULT_DIR="${REPO_ROOT}/results/${RUN_ID}"
mkdir -p "${RESULT_DIR}"
MLX_LOG="${REPO_ROOT}/logs/${RUN_ID}.txt"
SOURCE_DATA_PATH="${SMOKE_SOURCE_DATA_PATH:-${DATA_PATH}}"

if ! python3 - <<'PY' >/dev/null 2>&1
import importlib
mods = ["mlx", "numpy", "sentencepiece", "datasets", "huggingface_hub", "tqdm"]
for name in mods:
    importlib.import_module(name)
PY
then
  cat >&2 <<'EOF'
Missing MLX smoke dependencies. Install with:
  python3 -m pip install mlx numpy sentencepiece huggingface-hub datasets tqdm
EOF
  exit 1
fi

if [[ ! -d "${REPO_ROOT}/${SOURCE_DATA_PATH#./}" || ! -f "${REPO_ROOT}/${TOKENIZER_PATH#./}" ]]; then
  python3 "${REPO_ROOT}/data/cached_challenge_fineweb.py" \
    --variant "${TOKENIZER_VARIANT}" \
    --train-shards "${TRAIN_SHARDS:-1}"
fi

python3 "${SCRIPT_DIR}/prepare_smoke_dataset.py" \
  --source-root "${REPO_ROOT}/${SOURCE_DATA_PATH#./}" \
  --target-root "${REPO_ROOT}/${DATA_PATH#./}" \
  --val-tokens "${SMOKE_VAL_TOKENS:-131073}" >/dev/null

cat > "${RESULT_DIR}/command.sh" <<EOF
set -a
source ${CONFIG_PATH}
set +a
python3 -u train_gpt_mlx.py
EOF

(
  cd "${REPO_ROOT}"
  python3 -u train_gpt_mlx.py
) | tee "${RESULT_DIR}/stdout.log"

if [[ -f "${MLX_LOG}" ]]; then
  cp "${MLX_LOG}" "${RESULT_DIR}/train.log"
fi

python3 "${SCRIPT_DIR}/collect_summary.py" \
  --config "${CONFIG_PATH}" \
  --log "${RESULT_DIR}/train.log" \
  --source "${REPO_ROOT}/train_gpt_mlx.py" >/dev/null

echo "smoke log: ${RESULT_DIR}/train.log"
