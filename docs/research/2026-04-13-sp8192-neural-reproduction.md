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
- Earlier direct TCP endpoint: `ssh root@103.207.149.90 -p 10229 -i ~/.ssh/id_ed25519`
- Current pod access used for this batch: `ssh -i ~/.ssh/id_ed25519 f0zqqxsw2cfgv3-64412193@ssh.runpod.io`

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
- `results/pr1529_ablate_tttlr_003/`
- `results/pr1529_stability_tttlr_003_r1/`
- `results/pr1529_ablate_tttlr_004/`
- `results/pr1529_stability_tttlr_004_r1/`
- `results/pr1529_ablate_parstart_7/`
- `results/pr1529_stability_parstart_7_r1/`
- `results/pr1529_ablate_parstart_9/`
- `results/pr1529_ablate_muon_0965/`
- `results/pr1529_ablate_muon_0975/`
- `results/pr1529_ablate_gptqreserve_16/`
- `results/pr1529_ablate_gptqreserve_10/`
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

### Third config-only ablation: `TTT_LR=0.03`

Source logs:

- `results/pr1529_ablate_tttlr_003/artifacts/logs/pr1529_ablate_tttlr_003.txt`
- `results/pr1529_stability_tttlr_003_r1/artifacts/logs/pr1529_stability_tttlr_003_r1.txt`

Measured against the `TTT_LR=0.02` parent:

- Parent (`TTT_LR=0.02`): legal TTT BPB `1.81829712`, size `16,016,384` bytes
- `TTT_LR=0.03`: legal TTT BPB `1.78056575`, size `16,016,687` bytes
- Stability rerun: legal TTT BPB `1.77876833`, size `16,015,609` bytes

Interpretation:

- Increasing `TTT_LR` again from `0.02` to `0.03` is a real, stable win.
- The stability rerun is slightly better than the first sample and slightly
  smaller.
- This makes `TTT_LR=0.03` the new parent for the next reduced-loop ablations.

### Fourth config-only ablation: `TTT_LR=0.04`

Source logs:

- `results/pr1529_ablate_tttlr_004/artifacts/logs/pr1529_ablate_tttlr_004.txt`
- `results/pr1529_stability_tttlr_004_r1/artifacts/logs/pr1529_stability_tttlr_004_r1.txt`

Measured against the `TTT_LR=0.03` parent:

- Parent (`TTT_LR=0.03` stability): legal TTT BPB `1.77876833`, size `16,015,609` bytes
- `TTT_LR=0.04`: legal TTT BPB `1.75336425`, size `16,016,477` bytes
- Stability rerun: legal TTT BPB `1.75484111`, size `16,015,888` bytes

Interpretation:

- `TTT_LR=0.04` is another clear win over `0.03`.
- The gain is stable, with only a very small size increase versus the
  `0.03` stability rerun.
- This makes `TTT_LR=0.04` the new parent before moving to other knobs.

### Fifth config-only ablation: `PARALLEL_RESIDUAL_START`

Source logs:

- `results/pr1529_ablate_parstart_7/artifacts/logs/pr1529_ablate_parstart_7.txt`
- `results/pr1529_stability_parstart_7_r1/artifacts/logs/pr1529_stability_parstart_7_r1.txt`
- `results/pr1529_ablate_parstart_9/artifacts/logs/pr1529_ablate_parstart_9.txt`

Measured against the `TTT_LR=0.04`, `PARALLEL_RESIDUAL_START=8` parent:

- Parent (`start=8` stability): legal TTT BPB `1.75484111`, size `16,015,888` bytes
- `start=7`: legal TTT BPB `1.67043940`, size `16,016,264` bytes
- `start=7` stability rerun: legal TTT BPB `1.66993355`, size `16,014,422` bytes
- `start=9`: legal TTT BPB `1.85379938`, size `16,017,103` bytes

Interpretation:

- Moving the parallel residual start earlier to layer `7` is the dominant win
  in this entire batch.
- The `start=7` stability rerun is even slightly better than the first sample
  and brings the total size to only `14,422` bytes over the competition cap.
- Moving the start later to layer `9` is a clear regression and closes this
  knob with `start=7` as the promoted parent.

### Sixth config-only ablation: `MUON_MOMENTUM`

Source logs:

- `results/pr1529_ablate_muon_0965/artifacts/logs/pr1529_ablate_muon_0965.txt`
- `results/pr1529_ablate_muon_0975/artifacts/logs/pr1529_ablate_muon_0975.txt`

Measured against the `TTT_LR=0.04`, `PARALLEL_RESIDUAL_START=7`,
`MUON_MOMENTUM=0.97` parent:

- Parent: legal TTT BPB `1.66993355`, size `16,014,422` bytes
- `MUON_MOMENTUM=0.965`: legal TTT BPB `1.67166528`, size `16,016,631` bytes
- `MUON_MOMENTUM=0.975`: legal TTT BPB `1.67065660`, size `16,015,301` bytes

Interpretation:

- Both nearby momentum values regress on legal TTT BPB.
- `0.975` is closer to the parent than `0.965`, but neither beats the default
  `0.97`.
- This closes the momentum knob with `MUON_MOMENTUM=0.97` retained.

### Seventh config-only ablation: `GPTQ_RESERVE_SECONDS`

Source logs:

- `results/pr1529_ablate_gptqreserve_16/artifacts/logs/pr1529_ablate_gptqreserve_16.txt`
- `results/pr1529_ablate_gptqreserve_10/artifacts/logs/pr1529_ablate_gptqreserve_10.txt`

Measured against the same promoted parent:

- Parent (`13s`): legal TTT BPB `1.66993355`, size `16,014,422` bytes
- `GPTQ_RESERVE_SECONDS=16`: legal TTT BPB `1.67151656`, size `16,014,822` bytes
- `GPTQ_RESERVE_SECONDS=10`: legal TTT BPB `1.67208354`, size `16,015,317` bytes

Interpretation:

- Reserve-time changes are low leverage on this reduced SP8192 loop.
- Both variants lose on quality and do not materially improve size.
- This closes the reserve knob with `GPTQ_RESERVE_SECONDS=13` retained.

## Current Reduced-Loop Parent

After the completed quality-first ladder, the promoted reduced-loop parent is:

- `TTT_LR=0.04`
- `PARALLEL_RESIDUAL_START=7`
- `MUON_MOMENTUM=0.97`
- `GPTQ_RESERVE_SECONDS=13`
- `HASH_EMBED_ENABLED=1`

Measured on the `1,048,576`-token reduced validation shard:

- Pre-quant BPB: `2.43263471`
- Standard quantized BPB: `2.43655021`
- Sliding quantized BPB: `2.43174693`
- Legal TTT BPB: `1.66993355`
- Standard eval time: `4.995s`
- Sliding eval time: `22.524s`
- Legal TTT eval time: `42.641s`
- Total submission size: `16,014,422` bytes
- Improvement vs the earlier `TTT_LR=0.02` parent: about `0.1484` BPB

## Competition Conclusions

1. `#1529` is now reproducible on 1xH100 with a practical reduced-val loop.
2. The biggest measured quality gain in this batch came from moving
   `PARALLEL_RESIDUAL_START` earlier to `7`, not from optimizer timing knobs.
3. Legal TTT remains the dominant eval gain in the reduced loop.
4. The current reduced-loop parent is only `14,422` bytes over the size cap, so
   compression is now strategically relevant on the exact winning family rather
   than only as a generic sidecar idea.
5. Nearby `MUON_MOMENTUM` and `GPTQ_RESERVE_SECONDS` changes are low leverage on
   this lane and can be deprioritized.
6. Tokenizer work is byte-ready, but the SP8192 neural lane is now strong
   enough that the next sidecar to revisit should be compression, not
   retokenization.
7. The current parent improves legal TTT BPB by about `0.1484` over the
   earlier `TTT_LR=0.02` parent while slightly reducing total size.

## Next Priority Order

1. Evaluate ANS on the exact promoted SP8192 parent, because the current size
   overage is only `14,422` bytes and earlier sidecar analysis showed large ANS
   leverage on SP8192-sized artifacts.
2. If ANS is not sufficient or is too operationally awkward, return to neural
   work only for knobs or ingredients with evidence stronger than the nearby
   `MUON_MOMENTUM` and `GPTQ_RESERVE_SECONDS` variants.
3. After closing the size question on the current family, compare against
   merged `1.0810` and decide whether to port one missing merged ingredient
   rather than continuing local micro-ablations blindly.

## 2026-04-20 New-Family Session

This follow-up session moved off the older `#1529` family and onto the open
VarLen frontier families:

- non-casefold base: [openai/parameter-golf#1626](https://github.com/openai/parameter-golf/pull/1626)
- non-casefold add-on: [openai/parameter-golf#1667](https://github.com/openai/parameter-golf/pull/1667)
- casefold lane: [openai/parameter-golf#1670](https://github.com/openai/parameter-golf/pull/1670)
- tokenizer legality/tooling source: [openai/parameter-golf#1578](https://github.com/openai/parameter-golf/pull/1578)
- normalization policy thread: [openai/parameter-golf#1604](https://github.com/openai/parameter-golf/issues/1604)

### Pod Notes

- Pod access used for this batch: `ssh -i ~/.ssh/id_ed25519 wb5xn9081h38ik-644121a2@ssh.runpod.io`
- Direct TCP was still unreliable, so relay SSH plus `runpodctl send/receive`
  was used for result sync.
- New scratch clones prepared on pod:
  - `/workspace/research/parameter-golf-pr1626`
  - `/workspace/research/parameter-golf-pr1667`
  - `/workspace/research/parameter-golf-pr1670`
- Shared reduced non-casefold root:
  - `/workspace/research/data_roots/pr1626_reduced`
- Public casefold-v2 roots prepared for tooling / provisional bring-up:
  - `/workspace/research/data_roots/casefold_v2_reduced`
  - `/workspace/research/data_roots/casefold_v2_val1m`

### New Local Result Copies

The local ignored `results/` tree now also includes:

- `results/pr1626_smoke_20_r3/`
- `results/pr1626_signal_300_r1/`
- `results/pr1667_smoke_20_r1/`
- `results/pr1667_signal_300_r1/`
- `results/pr1670_casefoldv2_val1m_smoke_20_r1/`
- `results/pr1578_verify_bytes_sample.txt`

### `#1626` smoke on reduced non-casefold loop

Source log: `results/pr1626_smoke_20_r3/console.log`

- Iterations: `20`
- Validation tokens: `1,048,576`
- Quantized submission size: `15,927,748` bytes
- Quantized BPB: `3.23967741`
- Phased-TTT BPB: `3.02490790`
- Total eval time: `406.2s`

Interpretation:

- `#1626` now boots fully on 1xH100 in the reduced-loop setup.
- The record script needed only pod-environment fixes:
  - replace the broken `pyminify` CLI assumption with `python-minifier`
  - install `brotli`
- No model logic changes were needed for the family to run.

### `#1626` reduced signal on non-casefold loop

Source log: `results/pr1626_signal_300_r1/console.log`

- Iterations: `300`
- Validation tokens: `1,048,576`
- Step-300 BPB: `1.3361`
- Post-EMA pre-quant BPB: `1.90821454`
- Quantized BPB: `1.91582115`
- Phased-TTT BPB: `1.75795205`
- Total submission size: `15,954,366` bytes
- Total eval time: `264.5s`

Interpretation:

- This established `#1626` as a credible non-casefold backup family on the
  reduced loop.
- It also set the apples-to-apples comparison target for `#1667`.

### `#1667` smoke on reduced non-casefold loop

Source log: `results/pr1667_smoke_20_r1/console.log`

- Iterations: `20`
- Validation tokens: `1,048,576`
- Quantized submission size: `15,929,950` bytes
- Quantized BPB: `3.24779588`
- TTT-LoRA BPB: `3.03576159`
- Total eval time: `300.9s`

Interpretation:

- The attention-output gate and SmearGate path is real on 1xH100.
- New passthrough weights appear exactly where expected:
  `attn_gate_proj`, `smear_gate.weight`, and `smear_lambda`.
- The 20-step smoke was slightly worse than `#1626`, so the family decision
  had to come from the 300-step run, not from smoke alone.

### `#1667` reduced signal on non-casefold loop

Source log: `results/pr1667_signal_300_r1/console.log`

- Iterations: `300`
- Validation tokens: `1,048,576`
- Step-300 BPB: `1.3270`
- Post-EMA pre-quant BPB: `1.84627172`
- Quantized BPB: `1.85438532`
- TTT-LoRA BPB: `1.72047128`
- Total submission size: `15,960,036` bytes
- Total eval time: `208.9s`

Interpretation:

- `#1667` beat `#1626` cleanly on the same reduced non-casefold loop:
  - pre-quant: `1.84627172` vs `1.90821454`
  - quantized: `1.85438532` vs `1.91582115`
  - post-TTT: `1.72047128` vs `1.75795205`
- The family is still under the 16 MB cap.
- This makes `#1667` the promoted non-casefold backup-submission family.

### `#1578` byte-verification spot check

Source log: `results/pr1578_verify_bytes_sample.txt`

- Documents checked: `200`
- Ground-truth bytes: `1,489,674`
- LUT bytes: `1,489,674`
- Mismatched documents: `0`
- Result: `ALL CHECKS PASSED`

Interpretation:

- The public casefold-v2 tokenizer tooling is byte-accounting correct on the
  bundled verification sample.
- This clears the tooling gate for provisional casefold experiments, but not
  the policy question.

### Provisional casefold-v2 smoke through `#1670`

Source log: `results/pr1670_casefoldv2_val1m_smoke_20_r1/console.log`

Important caveat:

- This is **not** a faithful reproduction of `#1670`'s reported casefold-v4
  result.
- It uses the public casefold-v2 tokenizer and shards from
  `Mikeapedia/fineweb10B-sp8192-casefold-v2`, not an unpublished v4 root.
- It is still useful because it proves the `#1670` code path and phased-TTT
  machinery run on 1xH100 with public casefold artifacts.

Measured result:

- Iterations: `20`
- Validation tokens: `1,046,528`
- Post-EMA pre-quant BPB: `2.89426799`
- Quantized BPB: `2.73055296`
- Phased-TTT BPB: `2.73055296`
- Quantized submission size: under the cap
- Total eval time: `238.2s`

Interpretation:

- The casefold evaluation path is runnable with public artifacts.
- The missing piece for a faithful `#1670` reproduction is the exact v4
  tokenizer/data root, not general CUDA or evaluation incompatibility.
- Issue `#1604` was still open during this batch, so the casefold lane remains
  policy-pending even if a stronger public-compatible root is later built.

## Updated Competition Conclusions

1. The old `#1529` line is no longer the main path. The stronger current
   non-casefold family is `#1667`.
2. `#1667` is the promoted non-casefold backup-submission family on the
   reduced 1xH100 loop, beating `#1626` at the same size budget.
3. The casefold lane is no longer blocked on byte accounting or basic runtime:
   public artifacts plus `#1670` code are enough to run a provisional smoke.
4. A faithful `#1670` reproduction still needs the exact casefold-v4 root, and
   any casefold result remains policy-pending while Issue `#1604` is open.

## Updated Next Priority Order

1. Treat `#1667` as the current safe family:
   rerun on more reduced seeds or fuller validation before turning it into an
   actual backup submission.
2. Keep casefold work in a separate upside lane:
   either locate or build a closer casefold-v4 root before spending more GPU
   time on `#1670`.
3. Only after the safe family is stable and synced should compression or
   submission packaging work be revisited for the new promoted family.

## 2026-04-20 Late Frontier Pivot

After the `#1626`/`#1667`/`#1670` batch, the live open frontier moved again.
The merged README still lists `#1493` at `1.0810`, but several open records now
supersede the earlier working set:

- `#1735`: SP8192 + parallel pre-quant TTT, `1.04290` mean BPB, non-casefold.
- `#1738`: `#1735` + CaseOps tokenizer V15, `1.03540` mean BPB, tokenizer
  policy sidecar required.
- `#1698`: GatedDeltaNet (FLA) + legal score-first TTT, `1.00995` mean BPB,
  non-casefold but a different architecture/dependency stack.
- `#1604`: still open, so casefold / CaseOps-style tokenizer lanes remain
  policy-pending and should not be our only submission path.

This changes the safe-lane priority. `#1667` is still reproduced, but it is no
longer the best non-casefold family to spend pod time on. The new safe
submission-prep target is `#1735`, with `#1698` as the high-upside non-casefold
lane once the dependency stack is stable.

### `#1735` smoke on reduced non-casefold loop

Source logs:

- `results/pr1735_smoke_20_r1/console.log`
- `results/pr1735_smoke_20_r1/record.log`

Run setup:

- Record folder:
  `/workspace/research/parameter-golf-pr1735/records/track_10min_16mb/2026-04-18_SP8192_ParallelPreQuantTTT/`
- Data root: `/workspace/research/data_roots/pr1626_reduced`
- Iterations: `20`
- Validation tokens: `1,048,576`
- Pre-quant TTT: enabled, `21` epochs, `1xH100`

Measured result:

- Step-20 validation BPB: `2.2612`
- Post-EMA pre-quant BPB: `3.24753701`
- Post-prequant-TTT BPB: `2.96192217`
- Quantized BPB: `2.99328537`
- Quantized sliding BPB: `3.02747472`
- Pre-quant TTT time: `89.2s`
- Total submission size without code LZMA-wrap: `16,057,900` bytes

Interpretation:

- The exact `#1735` record code boots on the pod with no model-code changes.
- It reuses the existing SP8192 reduced data root through `DATA_DIR`.
- The only size issue in this scratch run is expected: the PR relies on code
  LZMA wrapping for the final under-cap artifact, while this smoke measured raw
  code bytes in the unwrapped path.

### `#1735` reduced signal on non-casefold loop

Source logs:

- `results/pr1735_signal_300_r1/console.log`
- `results/pr1735_signal_300_r1/record.log`

Measured result:

- Iterations: `300`
- Validation tokens: `1,048,576`
- Step-300 validation BPB: `1.3478`
- Post-EMA pre-quant BPB: `2.32358717`
- Post-prequant-TTT BPB: `0.49677151`
- Quantized BPB: `0.62650335`
- Quantized sliding BPB: `0.88692813`
- Pre-quant TTT time: `116.9s`
- Total submission size without code LZMA-wrap: `16,076,653` bytes

Interpretation:

- `#1735` is now boot- and signal-validated on our 1xH100 setup.
- The reduced 1M-token validation shard is **not** a reliable leaderboard proxy
  for this family because pre-quant TTT trains on the same validation shard and
  can overfit it aggressively.
- Use this run as a systems and compatibility signal, not as a quality claim.
- For real submission prep, the next meaningful validation is a larger shard or
  an actual 8xH100/full-validation run.

### `#1698` dependency and smoke check

Source logs:

- `results/pr1698_smoke_20_r1/console.log`
- `results/pr1698_smoke_20_r1/record.log`

Pod dependency fixes:

- Installed `zstandard`.
- Installed `fla-core==0.4.2` and `flash-linear-attention==0.4.2` with
  `--no-deps` first to avoid destabilizing the pod's PyTorch/Triton stack.
- Installed `transformers`, `tokenizers`, and `safetensors` after the FLA import
  path showed it needed `transformers` indirectly.
- Did not install the literal `transformers==5.5.4` pin from the PR
  requirements because the record script does not directly depend on that exact
  package version in the observed import path.

Measured smoke result:

- Iterations: `20`
- Validation tokens: `1,048,576`
- Training time: `163s`
- EMA BPB: `2.910074`
- Quantized BPB: `3.00975829`
- Legal score-first TTT BPB: `3.00975829`
- TTT eval time: `81.3s`
- Artifact size: `4,553,629` bytes

Interpretation:

- The GatedDeltaNet / FLA stack is runnable on the pod.
- The first smoke was dominated by compile overhead, but it completed the full
  training, quantization, and legal TTT path.
- Artifact size is far below the cap on short runs, so this lane's first risk is
  runtime / quality, not compression.

### `#1698` reduced signal on non-casefold loop

Source logs:

- `results/pr1698_signal_300_r1/console.log`
- `results/pr1698_signal_300_r1/record.log`

Measured result:

- Iterations: `300`
- Validation tokens: `1,048,576`
- Training time: `510s`
- Step-300 validation BPB: `1.8021`
- EMA BPB: `1.937462`
- Quantized BPB: `2.12540557`
- Legal score-first TTT BPB: `2.05553539`
- TTT gain: `-0.069870` BPB
- TTT eval time: `79.7s`
- Artifact size: `6,139,749` bytes

Interpretation:

- `#1698` is now boot- and signal-validated on our 1xH100 setup.
- It is much weaker than the official 8xH100 record at only 300 reduced steps,
  but the score-first TTT path produces a real gain and completes comfortably.
- This should remain a high-upside lane for future larger runs, but it is not a
  better immediate backup than `#1735` without more compute.

## Current Priority Override

1. `#1735` is now the safe non-casefold submission-prep family, superseding
   `#1667`.
2. `#1698` is the high-upside non-casefold architecture lane; keep it prepared
   for more compute, but do not block backup submission prep on it.
3. Casefold and CaseOps lanes (`#1670`, `#1738`, `#1756`) remain
   policy-pending while `#1604` is open.
4. The next compute-efficient step is not more 1M-token pre-quant-TTT tuning.
   It is either:
   - a larger-shard `#1735` sanity run, or
   - an actual 8xH100/full-validation `#1735` reproduction when compute is
     available.

## 2026-04-21 2M-Shard `#1735` Pre-Quant TTT Tuning

This batch stayed on 1xH100 and moved `#1735` off the highly overfit 1M-token
validation loop. A new scratch data root was created on the pod:

- `/workspace/research/data_roots/pr1735_val2m`
- train shard: symlink to the existing SP8192 `fineweb_train_000000.bin`
- tokenizer: symlink to the existing `fineweb_8192_bpe.model`
- validation shard: first `2,097,153` tokens from the full SP8192 validation
  shard with `header[2]` rewritten, yielding `2,097,152` scored validation
  tokens in the record script

The first `2M` run failed late during serialization because the migrated pod was
missing the `brotli` module. Training and pre-quant TTT had already completed.
The environment was fixed with `python3 -m pip install --break-system-packages
brotli`, and the same run was repeated as `r2`.

### `#1735` 2M-shard baseline

Source logs:

- failed environment run: `results/pr1735_signal_300_val2m_r1/record.log`
- clean run: `results/pr1735_signal_300_val2m_r2/record.log`

Run setup:

- Iterations: `300`
- Validation tokens: `2,097,152`
- `PREQUANT_TTT_LR=0.0005`
- `PREQUANT_TTT_FREEZE_BLOCKS=2`
- `PREQUANT_TTT_EPOCHS=21`

Clean `r2` result:

- Step-300 validation BPB: `1.3505`
- Post-EMA pre-quant BPB: `2.32622172`
- Post-prequant-TTT BPB: `0.59151500`
- Quantized BPB: `0.72429508`
- Quantized sliding BPB: `0.92366498`
- Pre-quant TTT time: `175.9s`
- Sliding eval time: `70.194s`
- Raw submission size before code LZMA wrap: `16,074,854` bytes

Interpretation:

- The larger shard reduces the extreme 1M-token overfit signal, as expected.
- It is still not leaderboard-comparable, but it is a better inner-loop proxy
  for pre-quant TTT settings than the 1M shard.
- The raw size warning is still expected because this scratch path measures
  unwrapped code bytes; `#1735` uses code LZMA wrapping for under-cap records.

### `#1758` retune transferred to non-casefold `#1735`

PR `#1758` reports that the `#1738` CaseOps stack improves by changing only:

- `PREQUANT_TTT_LR`: `5e-4` -> `1e-3`
- `PREQUANT_TTT_FREEZE_BLOCKS`: `2` -> `0`

The same config-only retune was tested on the non-casefold `#1735` family using
the 2M validation root.

Source log: `results/pr1735_signal_300_val2m_lr1e3_unfrozen_r1/record.log`

Measured result:

- Validation tokens: `2,097,152`
- `PREQUANT_TTT_LR=0.001`
- `PREQUANT_TTT_FREEZE_BLOCKS=0`
- Post-prequant-TTT BPB: `0.37838465`
- Quantized BPB: `0.49164964`
- Quantized sliding BPB: `0.63312403`
- Pre-quant TTT time: `199.0s`
- Sliding eval time: `39.746s`
- Raw submission size before code LZMA wrap: `16,071,776` bytes

Interpretation:

- The `#1758` retune transfers cleanly to the non-casefold `#1735` family.
- It improves the 2M-shard sliding score by `0.29054095` BPB relative to the
  `5e-4/freeze=2` baseline.
- It also slightly reduces raw submission size in this scratch run.

### Higher-LR exploratory ablation

Because the `1e-3/freeze=0` pre-quant TTT curve was still descending at epoch
21, one additional exploratory run tested `PREQUANT_TTT_LR=0.0015` with
`PREQUANT_TTT_FREEZE_BLOCKS=0`. Upstream `#1758` reports that still-higher LRs
can diverge, so this was treated as a bounded risk.

Source log: `results/pr1735_signal_300_val2m_lr15e4_unfrozen_r1/record.log`

Measured result:

- Validation tokens: `2,097,152`
- `PREQUANT_TTT_LR=0.0015`
- `PREQUANT_TTT_FREEZE_BLOCKS=0`
- Post-prequant-TTT BPB: `0.36132346`
- Quantized BPB: `0.46254170`
- Quantized sliding BPB: `0.58760825`
- Pre-quant TTT time: `186.7s`
- Sliding eval time: `40.014s`
- Raw submission size before code LZMA wrap: `16,072,802` bytes

Interpretation:

- `0.0015/freeze=0` did not diverge on the 2M non-casefold loop.
- It is the current 2M-shard parent, beating `1e-3/freeze=0` by `0.04551578`
  sliding BPB.
- Do not extrapolate this directly to leaderboard quality; the correct next
  step is either a larger validation shard or a TTT-only sweep harness that
  avoids retraining the same 300-step model for each LR.

## Current 1xH100 Parent

For the non-casefold `#1735` safe lane, the current 1xH100 reduced parent is:

- data: `2,097,152` validation tokens
- training: `300` iterations, one SP8192 train shard
- `PREQUANT_TTT_EPOCHS=21`
- `PREQUANT_TTT_LR=0.0015`
- `PREQUANT_TTT_FREEZE_BLOCKS=0`
- quantized sliding BPB: `0.58760825`

Next useful work:

1. Build or scratch-patch a TTT-only sweep harness that saves the pre-TTT EMA
   model once, then sweeps `PREQUANT_TTT_LR` / freeze depth without repeating
   the 300-step training pass.
2. If keeping the simple runner, test `PREQUANT_TTT_LR=0.002` only as a
   bounded divergence check; upstream evidence says this may be unstable.
3. If more compute arrives, run the exact `#1735` or `#1758`-style
   `LR=0.0015/freeze=0` setting on fuller validation / 8xH100 before preparing
   a real submission.

## 2026-04-26 No-Pod Frontier Triage

No pod was running for this pass. The goal was to choose a single next
`1xH100` target before spending more credit.

This section supersedes the April 21 priority override. `#1735` remains useful
as a reduced-loop systems proxy, but it is no longer a safe submission-prep
family. Upstream review now flags its full-validation pre-quant TTT as likely
violating Issue `#1017` score-before-update and causality: the final predictor
is adapted on the same validation stream before scoring that stream, including
future tokens. `#1758` inherits that risk.

Issue `#1604` also remains open, so casefold / CaseOps / custom-normalization
lanes are still policy-pending and should not be the only submission path.

Primary sources refreshed in this pass:

- Official leaderboard source:
  [README](https://github.com/openai/parameter-golf/blob/main/README.md)
- Normalization policy thread:
  [openai/parameter-golf#1604](https://github.com/openai/parameter-golf/issues/1604)
- Pre-quant TTT risk:
  [openai/parameter-golf#1735](https://github.com/openai/parameter-golf/pull/1735),
  [openai/parameter-golf#1758](https://github.com/openai/parameter-golf/pull/1758)
- Apr 25/26 frontier targets:
  [#1812](https://github.com/openai/parameter-golf/pull/1812),
  [#1813](https://github.com/openai/parameter-golf/pull/1813),
  [#1802](https://github.com/openai/parameter-golf/pull/1802),
  [#1791](https://github.com/openai/parameter-golf/pull/1791),
  [#1698](https://github.com/openai/parameter-golf/pull/1698),
  [#1824](https://github.com/openai/parameter-golf/pull/1824),
  [#1787](https://github.com/openai/parameter-golf/pull/1787),
  [#1796](https://github.com/openai/parameter-golf/pull/1796), and
  [#1795](https://github.com/openai/parameter-golf/pull/1795)

### Frontier Table

| Lane | Claimed score | Tokenizer / policy risk | Reproduction status | Decision |
| --- | ---: | --- | --- | --- |
| `#1812` SP8192 + LegalTTT 4ep | `1.07290` | Official SP8192, no tokenizer change, score-first TTT only | Self-contained record folder with logs and command: `SEED=42 TTT_ENABLED=1 TTT_LR=0.005 TTT_EPOCHS=4 torchrun --standalone --nproc_per_node=8 train_gpt.py` | **Primary next pod target** |
| `#1813` Scylla QK5.25 recurrence | `0.94166` | Custom Scylla tokenizer/data path, no TTT | Record code/logs exist, but tokenizer files and data-prep script are not included; PR comments request them | Wait for assets or derive from `#1796` before GPU |
| `#1796` Scylla + LegalTTT | `1.08057` | Custom Scylla tokenizer, less risky than casefold but still extra byte-accounting work | Includes tokenizer assets (`candidate.vocab`, `candidate.meta.npz`) and command-style record | Future Scylla-readiness lane, not first pod target |
| `#1802` SP8192 + multi-phase global TTT | `1.07713` | Official SP8192; multi-phase TTT has more interpretive risk than simple chunk score-first TTT | Self-contained record, no comments yet | Secondary target after `#1812` |
| `#1735/#1758` pre-quant TTT family | `1.04290` / `1.02840` | Official SP8192 / CaseOps variants, but pre-quant TTT on validation is under active legality challenge | Already runnable locally on reduced 2M proxy | Keep only as proxy; do not build sole submission on it |
| `#1791` GDN/FLA K-KVShare-Wider | `1.03386` | Official SP8192; no TTT | Has requirements and record folder, but PR comments show reported logs likely used older non-canonical byte denominator; corrected estimate near `1.2169` | Do not target now |
| `#1698` GatedDeltaNet + TTT | `1.00995` | Official SP8192; score-first TTT | Runnable in our pod history, but PR comments flag decimal size-cap failure and GDN byte-LUT bug; corrected canonical estimate near `1.189` | High-upside architecture only after fixes |
| `#1824` recurrent SP1024 1xH100 | `1.50735` log-level result | Official SP1024, low policy risk | Simple `train_gpt.py` patch and logs, no record folder | Runnable but not competitive enough for current Track B focus |
| `#1787` CaseOps + TTT/RTKD | `1.06335` | CaseOps policy-pending under `#1604`; GPTQ reserve timing also questioned | Self-contained enough to inspect, but not safe-only | Upside lane only |
| `#1795` SP4096 + byte PPM mixture | `1.01252` | Online byte-level adaptive predictor still needs organizer ruling | Strict target-conditioned gate was fixed, but category legality remains open | Read-only idea source for now |

### Target Selection

The next pod session should target `#1812`, not `#1735/#1758`.

Rationale:

1. It uses the official SP8192 tokenizer and dataset path.
2. It avoids pre-quant validation adaptation entirely.
3. Its legality story is the already-merged score-first TTT pattern:
   score each chunk, then train only on already-scored tokens.
4. The PR ships a self-contained record folder, logs, and exact full-run
   command.
5. The reported score is weaker than the risky open frontier but strong enough
   to be a credible backup-submission base if reproduced.

`#1813` is the highest claimed non-casefold target, but it is not the first pod
target because its PR currently lacks the Scylla tokenizer files and dataset
preparation script needed to run independently. `#1796` may provide a path to
that asset stack, but that is a local/tooling task before GPU.

### Next 1xH100 Pod Contract

Use a fresh scratch clone and leave `/workspace/parameter-golf` untouched:

```bash
cd /workspace/research
git clone https://github.com/openai/parameter-golf.git parameter-golf-pr1812
cd parameter-golf-pr1812
git fetch origin pull/1812/head:pr1812
git checkout pr1812

python3 -m pip install brotli sentencepiece
python3 -m pip install flash_attn_3 --no-deps \
  --find-links https://windreamer.github.io/flash-attention3-wheels/cu128_torch291/

MATCHED_FINEWEB_REPO_ID=kevclark/parameter-golf \
  python3 data/cached_challenge_fineweb.py --variant sp8192 --train-shards 1

git clone --branch research/sp8192-neural-reproduction \
  https://github.com/jaydenpiao/parameter-golf.git /workspace/research/parameter-golf-tools

python3 /workspace/research/parameter-golf-tools/scripts/research/write_reduced_shard.py \
  --input /workspace/research/parameter-golf-pr1812/data/datasets/fineweb10B_sp8192/fineweb_val_000000.bin \
  --output /workspace/research/parameter-golf-pr1812/data/datasets/fineweb10B_sp8192_val2m/fineweb_val_000000.bin \
  --num-tokens 2097153 \
  --symlink-train-from /workspace/research/parameter-golf-pr1812/data/datasets/fineweb10B_sp8192/fineweb_train_000000.bin

RECORD_DIR=records/track_10min_16mb/2026-04-25_SP8192_3LayerRecur_LegalTTT_4ep
cd "$RECORD_DIR"
```

The packed `#1812` script already supports `ITERATIONS`,
`MAX_WALLCLOCK_SECONDS`, `VAL_LOSS_EVERY`, `SEED`, `TOKENIZER_PATH`,
`TRAIN_FILES`, `VAL_FILES`, and TTT env vars. It does **not** support
`DATA_PATH` or `OUT_DIR` as-is. Do not patch model logic. If run isolation is
needed, either run from a per-run copy of the record folder or add an
`OUT_DIR`-only scratch patch before launching multiple runs.

Allowed scratch-interface knobs are:

- `DATA_DIR`
- `TRAIN_FILES`
- `VAL_FILES`
- `TOKENIZER_PATH`
- `OUT_DIR` if added as an artifact-isolation patch
- `ITERATIONS`
- `VAL_LOSS_EVERY`
- `MAX_WALLCLOCK_SECONDS`
- `SEED`
- `NPROC_PER_NODE`

Run order:

```bash
RUN_ID=pr1812_smoke_20 \
SEED=42 \
TRAIN_FILES=/workspace/research/parameter-golf-pr1812/data/datasets/fineweb10B_sp8192_val2m/fineweb_train_*.bin \
VAL_FILES=/workspace/research/parameter-golf-pr1812/data/datasets/fineweb10B_sp8192_val2m/fineweb_val_*.bin \
TOKENIZER_PATH=/workspace/research/parameter-golf-pr1812/data/tokenizers/fineweb_8192_bpe.model \
ITERATIONS=20 \
MAX_WALLCLOCK_SECONDS=600 \
VAL_LOSS_EVERY=0 \
TTT_ENABLED=1 \
TTT_LR=0.005 \
TTT_EPOCHS=4 \
torchrun --standalone --nproc_per_node=1 train_gpt.py

RUN_ID=pr1812_signal_300_val2m \
SEED=42 \
TRAIN_FILES=/workspace/research/parameter-golf-pr1812/data/datasets/fineweb10B_sp8192_val2m/fineweb_train_*.bin \
VAL_FILES=/workspace/research/parameter-golf-pr1812/data/datasets/fineweb10B_sp8192_val2m/fineweb_val_*.bin \
TOKENIZER_PATH=/workspace/research/parameter-golf-pr1812/data/tokenizers/fineweb_8192_bpe.model \
ITERATIONS=300 \
MAX_WALLCLOCK_SECONDS=600 \
VAL_LOSS_EVERY=0 \
TTT_ENABLED=1 \
TTT_LR=0.005 \
TTT_EPOCHS=4 \
torchrun --standalone --nproc_per_node=1 train_gpt.py
```

Acceptance for the smoke:

- CUDA/FA3 imports work.
- The official SP8192 tokenizer loads.
- Training reaches artifact export.
- Standard, sliding, and TTT metrics are emitted.
- Logs and artifacts are copied back immediately.

Acceptance for the 300-step signal:

- Same `2,097,152`-token reduced validation proxy as the latest `#1735` runs.
- Artifact remains below or close enough to the 16 MB cap to be actionable.
- Eval stays score-first and under the reduced-session time budget.
- Result is compared only against its own `#1812` reduced parent, not against
  leaderboard scores.

### Updated Priority Order

1. Run `#1812` smoke and 300-step reduced signal on the next `1xH100` pod.
2. If `#1812` boots cleanly, optionally compare `#1802` on the same proxy to
   measure whether multi-phase global TTT is worth legal review.
3. In parallel without GPU, inspect `#1796` to determine whether the Scylla
   tokenizer/data stack can make `#1813` runnable.
4. Do not spend more GPU on `#1735/#1758` unless staff explicitly permits
   pre-quant validation TTT or we only need it as a non-submission proxy.
5. Keep `#1698`, `#1787`, and `#1795` as idea sources until their metric,
   artifact-size, or legality blockers are resolved.

## 2026-04-26 `#1812` 1xH100 Reproduction

This batch used the Runpod direct TCP endpoint
`root@103.207.149.110 -p 16307` on a fresh `1xH100 80GB` pod. The checkout
under `/workspace/parameter-golf` was left untouched; all work happened in
`/workspace/research/parameter-golf-pr1812`.

Pod preflight:

- GPU: `NVIDIA H100 80GB HBM3`
- Free `/workspace`: about `50 GB`
- PyTorch: `2.9.1+cu128`
- CUDA available: `True`
- Existing deps: `sentencepiece`, `flash_attn_interface`, `flash_attn`
- Missing dep fixed before runs: `brotli`

Local result copies:

- `results/pr1812_smoke_20/`
- `results/pr1812_signal_300_val2m_failed/`
- `results/pr1812_signal_300_val2m_3shards/`
- `results/pr1812_signal_300_val2m_3shards_chunk32k/`

### Setup

The `sp8192` data root was downloaded from `kevclark/parameter-golf`. The
existing reduced-shard helper created a valid 2M-token validation proxy:

- validation path:
  `/workspace/research/parameter-golf-pr1812/data/datasets/fineweb10B_sp8192_val2m/fineweb_val_000000.bin`
- stored tokens: `2,097,153`
- scored tokens in the record script: `2,097,152`

The first setup used one train shard because that matched prior reduced-loop
habits. That was sufficient for smoke but not for 300 training iterations with
this record loader.

### Smoke: 20 steps, one train shard

Source log: `results/pr1812_smoke_20/pr1812_smoke_20.txt`

- Train steps: `20`
- Train shard count: `1`
- Validation tokens: `2,097,152`
- Step-20 BPB: `2.2843`
- Pre-quant post-EMA BPB: `3.28529543`
- Quantized BPB: `3.28576826`
- Quantized sliding BPB: `3.28539856`
- Quantized TTT BPB: `2.94771200`
- TTT chunks: `32`
- TTT eval time: `103.275s`
- Quantized model bytes: `15,937,482`

Interpretation:

- `#1812` boots cleanly on 1xH100 with official SP8192 data.
- The score-first TTT path runs and improves BPB even at 20 train steps.
- The smoke artifact is under the decimal 16 MB model-only threshold.

### Failed 300-step attempt: one train shard

Source logs:

- `results/pr1812_signal_300_val2m_failed/console_signal.log`
- `results/pr1812_signal_300_val2m_failed/pr1812_signal_300_val2m.txt`

Failure:

```text
IndexError: index 11 is out of bounds for axis 0 with size 11
```

Root cause:

- The record script's `ShuffledSequenceLoader.next_batch` builds a
  per-microbatch `shard_plan`.
- With one train shard, the loader runs out of remaining sequence starts around
  step `127`, micro-step `1`.
- At that point `shard_plan` has only `11` entries while the device batch wants
  `48`, causing the out-of-bounds access.
- This is a reduced-data setup issue, not a model or CUDA issue.

Fix:

- Download `--train-shards 3`.
- Point `TRAIN_FILES` at the full
  `fineweb10B_sp8192/fineweb_train_*.bin` pattern.
- Keep `VAL_FILES` on the 2M validation proxy.

Capacity check:

- Three shards provide `146,484` first-epoch sequence starts.
- The 300-step run including warmups needs about `130,560` sequence starts.

### Signal: 300 steps, three train shards

Source log:
`results/pr1812_signal_300_val2m_3shards/pr1812_signal_300_val2m_3shards.txt`

- Train steps: `300`
- Train shard count: `3`
- Validation tokens: `2,097,152`
- Step-300 BPB: `1.3521`
- Pre-quant post-EMA BPB: `2.04854828`
- Quantized BPB: `2.05388719`
- Quantized sliding BPB: `2.04933629`
- Quantized TTT BPB: `1.72333777`
- TTT chunks: `32`
- TTT eval time: `77.913s`
- Quantized model bytes: `16,003,213`

Interpretation:

- The three-shard setup fixes the loader failure and completes the reduced run.
- `#1812` is now a reproducible 1xH100 reduced-loop lane.
- The reduced-loop result is close to the previous `#1667` reduced signal
  (`1.72047128`) but slightly worse on this proxy.
- The compressed model is `3,213` bytes over the decimal 16 MB cap before code
  bytes, so this is not submission-ready.

### Probe: `TTT_CHUNK_TOKENS=32768`

Source log:
`results/pr1812_signal_300_val2m_3shards_chunk32k/pr1812_signal_300_val2m_3shards_chunk32k.txt`

Only the TTT chunk-size env was changed from the successful three-shard signal:

- `TTT_CHUNK_TOKENS=32768`

Measured result:

- Train steps: `300`
- Train shard count: `3`
- Validation tokens: `2,097,152`
- Step-300 BPB: `1.3515`
- Pre-quant post-EMA BPB: `2.04893225`
- Quantized BPB: `2.05455175`
- Quantized sliding BPB: `2.05042081`
- Quantized TTT BPB: `1.66858393`
- TTT chunks: `64`
- TTT eval time: `80.710s`
- Quantized model bytes: `16,003,606`

Interpretation:

- Halving the TTT chunk size is a clear reduced-loop win:
  `1.72333777` -> `1.66858393`, an improvement of `0.05475384` BPB.
- Eval time stays comfortably under the 600s budget on the 2M proxy.
- The artifact remains slightly over cap, by `3,606` bytes model-only, so the
  next move should be a size-aware follow-up rather than another pure-quality
  probe.

## Updated `#1812` Priority

1. Keep `#1812` as the current legal official-SP8192 reproduction lane.
2. Treat `TTT_CHUNK_TOKENS=32768` as the new reduced-loop parent for this lane.
3. Do not open a submission branch yet: the model artifact is still a few KB
   over the decimal 16 MB cap before code bytes.
4. Next GPU-efficient step should be a narrow size fix on the same parent, not
   `#1790` or another frontier family.
5. Candidate size knobs to inspect before spending more GPU:
   `GPTQ_CALIBRATION_BATCHES`, `matrix_clip_sigmas`, `embed_clip_sigmas`,
   compressor settings, and whether the record's packed-code path measures
   total bytes differently from this scratch copy.
