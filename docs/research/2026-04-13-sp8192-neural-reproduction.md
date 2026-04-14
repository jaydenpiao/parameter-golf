# 2026-04-13 SP8192 Neural Reproduction

This note captures the first 1xH100 reproduction pass on open PR `#1529`,
plus the tokenizer legality/tooling gate from `#1578` and the compression
sidecar from `#1510`.

## Primary Sources

- Merged leaderboard top: `records/track_10min_16mb/2026-04-09_SP8192_3LayerRecur_ParResid_QK525_LegalTTT/README.md`
- Open neural PR: [openai/parameter-golf#1529](https://github.com/openai/parameter-golf/pull/1529)
- Open tokenizer PR: [openai/parameter-golf#1578](https://github.com/openai/parameter-golf/pull/1578)
- Open compression PR: [openai/parameter-golf#1510](https://github.com/openai/parameter-golf/pull/1510)

## Pod Layout

- Untouched competition checkout: `/workspace/parameter-golf`
- Scratch neural clone: `/workspace/research/parameter-golf-upstream`
- Scratch tokenizer clone: `/workspace/research/parameter-golf-pr1578`
- Scratch compression clone: `/workspace/research/parameter-golf-pr1510`
- Pod access used for all work: `ssh root@103.207.149.90 -p 10229 -i ~/.ssh/id_ed25519`

## `#1529` Minimal Reproduction Patch

The record folder is `records/track_10min_16mb/2026-04-11_ImrpovedParallelResiduals/`.
The first reproduction pass did not change model logic. It only added the
minimum runtime surface needed to iterate safely on 1xH100:

- `DATA_PATH`
- `TOKENIZER_PATH`
- `OUT_DIR`

Human-readable diff against `train_gpt_human.py`:

```diff
@@
-    datasets_dir = os.path.join(data_dir, 'datasets', f'fineweb10B_sp{vocab_size}')
+    data_path = os.environ.get('DATA_PATH')
+    datasets_dir = data_path if data_path else os.path.join(data_dir, 'datasets', f'fineweb10B_sp{vocab_size}')
     train_files = os.path.join(datasets_dir, 'fineweb_train_*.bin')
     val_files = os.path.join(datasets_dir, 'fineweb_val_*.bin')
-    tokenizer_path = os.path.join(data_dir, 'tokenizers', f'fineweb_{vocab_size}_bpe.model')
-    logfile = f'logs/{run_id}.txt'
-    model_path = 'final_model.pt'
-    quantized_model_path = 'final_model.int6.ptz'
+    tokenizer_path = os.environ.get('TOKENIZER_PATH', os.path.join(data_dir, 'tokenizers', f'fineweb_{vocab_size}_bpe.model'))
+    out_dir = os.environ.get('OUT_DIR', '.')
+    logfile = os.path.join(out_dir, 'logs', f'{run_id}.txt')
+    model_path = os.path.join(out_dir, 'final_model.pt')
+    quantized_model_path = os.path.join(out_dir, 'final_model.int6.ptz')
@@
-        os.makedirs('logs', exist_ok=True)
+        os.makedirs(h.out_dir, exist_ok=True)
+        os.makedirs(Path(h.logfile).parent, exist_ok=True)
+        log(f'Artifact output dir: {h.out_dir}', console=True)
+        log(f'Model path: {h.model_path}', console=True)
+        log(f'Quantized model path: {h.quantized_model_path}', console=True)
```

## Reduced Validation Shard

`#1529` validates shard size against a 256-int32 header where `header[2]` is the
token count. A raw file truncation is invalid. Use
`scripts/research/write_reduced_shard.py` to create a valid smaller shard.

Example:

```bash
python3 scripts/research/write_reduced_shard.py \
  --input /workspace/research/parameter-golf-upstream/data/datasets/fineweb10B_sp8192/fineweb_val_000000.bin \
  --output /workspace/research/parameter-golf-upstream/data/datasets/fineweb10B_sp8192_val1m/fineweb_val_000000.bin \
  --num-tokens 1048577 \
  --symlink-train-from /workspace/research/parameter-golf-upstream/data/datasets/fineweb10B_sp8192/fineweb_train_000000.bin
```

## Local Copies Of Remote Results

The synced artifacts/logs live under ignored local result folders:

- `results/pr1529_smoke_v2/`
- `results/pr1529_signal_300_val1m_fixed/`
- `results/pr1578_verify_bytes/`
- `results/pr1510_ans_analysis/`
- `results/legal_ttt_sp1024_1xh100/`

These are intentionally local-only and should not be committed.

## Measured Results

### `#1529` smoke on full validation shard

Source log: `results/pr1529_smoke_v2/artifacts/logs/pr1529_smoke_v2.txt`

- Iterations: `12`
- Validation tokens: `40,540,160`
- Standard quantized BPB: `3.36631809`
- Quantized submission size: `15,959,923` bytes
- Result: boots end-to-end on 1xH100

### `#1529` reduced signal on valid 1M-token validation shard

Source log: `results/pr1529_signal_300_val1m_fixed/artifacts/logs/pr1529_signal_300_val1m_fixed.txt`

- Iterations: `300`
- Validation tokens: `1,048,576`
- Pre-quant BPB: `2.79756028`
- Standard quantized BPB: `2.80578296`
- Sliding quantized BPB: `2.80205778`
- Legal TTT BPB: `1.90818105`
- Standard eval time: `4.978s`
- Sliding eval time: `37.391s`
- Legal TTT eval time: `95.220s`
- Quantized submission size: `16,016,008` bytes

Interpretation:

- This is a usable inner-loop setup for neural iteration on 1xH100.
- It is not leaderboard-comparable because the validation split is reduced.
- The artifact is only `16,008` bytes over the cap, so size work is now a
  first-order constraint.

### `#1578` tokenizer verification

Source log: `results/pr1578_verify_bytes/verify_bytes.txt`

- Documents checked: `200`
- Ground-truth bytes: `1,489,674`
- LUT bytes: `1,489,674`
- Mismatched documents: `0`
- Result: `ALL CHECKS PASSED`

Interpretation:

- The tokenizer legality/tooling gate is clear.
- Tokenizer retraining should wait until the SP8192 neural base is stable.

### `#1510` compression sidecar

Source logs:

- `results/pr1510_ans_analysis/legal_ttt_sp1024_1xh100_ans_analysis.txt`
- `results/pr1510_ans_analysis/pr1529_smoke_ans_analysis.txt`
- `results/pr1510_ans_analysis/pr1529_signal_300_val1m_fixed_ans_analysis.txt`

SP1024 proof artifact (`results/legal_ttt_sp1024_1xh100/summary.json` baseline family):

- LZMA: `13.59 MB`
- ANS: `13.45 MB`
- Savings: `142.9 KB` (`1.0%`)

SP8192 smoke raw model:

- LZMA: `21.41 MB`
- ANS: `18.15 MB`
- Savings: `3342.7 KB` (`15.2%`)

SP8192 reduced-signal raw model:

- LZMA: `23.09 MB`
- ANS: `18.89 MB`
- Savings: `4294.9 KB` (`18.2%`)

Interpretation:

- ANS barely matters on the smaller SP1024 proof family.
- ANS matters a lot on the large SP8192 family.
- Compression integration is worth doing once the neural base is stable enough
  that those freed bytes can be spent intentionally.

### First config-only ablation: `TTT_LR=0.005`

Source log: `results/pr1529_ablate_tttlr_0005/artifacts/logs/pr1529_ablate_tttlr_0005.txt`

- Base reduced-signal run: legal TTT BPB `1.90818105`, TTT eval `95.220s`
- `TTT_LR=0.005`: legal TTT BPB `2.02779804`, TTT eval `43.054s`
- Size change: `16,016,008` bytes -> `16,015,585` bytes

Interpretation:

- Lowering `TTT_LR` from `0.01` to `0.005` is a clear quality regression on the
  reduced SP8192 loop.
- The eval becomes much faster, but the quality drop is too large to justify it
  for the current objective.
- This makes smaller `TTT_LR` values low priority unless we later hit a strict
  eval-time constraint.

### Second config-only ablation: `TTT_LR=0.02`

Source log: `results/pr1529_ablate_tttlr_002/artifacts/logs/pr1529_ablate_tttlr_002.txt`

- Base reduced-signal run: legal TTT BPB `1.90818105`, TTT eval `95.220s`
- `TTT_LR=0.02`: legal TTT BPB `1.81829712`, TTT eval `42.738s`
- Sliding BPB: `2.80205778` -> `2.78217989`
- Size change: `16,016,008` bytes -> `16,016,384` bytes

Interpretation:

- Raising `TTT_LR` from `0.01` to `0.02` is a clear win on the reduced SP8192
  loop.
- The legal TTT metric improves by about `0.0899` BPB and the adaptive eval is
  much faster.
- This makes `TTT_LR=0.02` the new parent setting for the next reduced-loop
  ablations.

## Competition Conclusions

1. `#1529` is now reproducible on 1xH100 with a practical reduced-val loop.
2. The immediate constraint on the SP8192 lane is artifact size, not bring-up.
3. Legal TTT remains the largest measured eval gain in the reduced loop.
4. Tokenizer work is ready from a byte-correctness perspective, but should stay
   behind the neural lane until the base is stable.
5. ANS is strategically important for SP8192, but low leverage for the current
   SP1024 proof model.
6. Decreasing `TTT_LR` to `0.005` is the wrong direction for quality on this
   lane, even though it roughly halves TTT eval time.
7. Increasing `TTT_LR` to `0.02` is a real reduced-loop improvement and should
   be treated as the new local parent.

## Next Priority Order

1. Run config-only ablations on the reduced `#1529` lane:
   - `TTT_LR` upward from `0.02`, then stop if quality rolls over
   - `PARALLEL_RESIDUAL_START`
   - `MUON_MOMENTUM`
   - `QK_GAIN_INIT` if the script exposes it
   - `GPTQ_RESERVE_SECONDS`
2. Prefer ablations that either:
   - improve legal TTT BPB on the reduced loop, or
   - pull total size below `16,000,000` bytes.
3. Only after a stable config-only win, compare against merged `1.0810` and
   decide whether to port one merged neural ingredient that `#1529` lacks.
