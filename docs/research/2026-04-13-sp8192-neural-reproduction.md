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
