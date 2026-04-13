# Config Interface

Every experiment configuration lives in `configs/*.env` and is sourced directly
before invoking `train_gpt.py` or `train_gpt_mlx.py`.

Required metadata keys for each config:

- `CONFIG_NAME`: stable config identifier
- `TRACK`: `track_a` or `track_b`
- `TOKENIZER_VARIANT`: tokenizer family identifier such as `sp1024`, `sp4096`, `sp8192`
- `TARGET_HARDWARE_TIER`: `mac_smoke`, `1xh100`, or `8xh100`
- `RESULTS_TAG`: short human-readable tag used in results folders and logs

Training, evaluation, tokenizer, quantization, and model-shape parameters should
also live here so runs can be reproduced with a single command.

Suggested invocation pattern:

```bash
set -a
source configs/baseline_sp1024.env
set +a
torchrun --standalone --nproc_per_node=1 train_gpt.py
```

Validate that the config and source agree before launching a run:

```bash
python3 scripts/check_config_support.py --config configs/baseline_sp1024_1xh100.env --source train_gpt.py
```

Configs that reference feature flags the source does not consume should fail fast.
This avoids mislabeled runs where metadata says `track_b` but the underlying code
ignored the requested evaluation or adaptation knobs.

Current evaluation knobs consumed by `train_gpt.py` include:

- `EVAL_STRIDE` / `EVAL_BATCH_SEQS` for sliding-window scoring
- `TTT_ENABLED`, `TTT_LR`, `TTT_EPOCHS`, and `TTT_CHUNK_TOKENS` for the narrow
  score-first TTT proof lane

Do not treat shell history as configuration. If a parameter matters, it belongs
in the config file.
