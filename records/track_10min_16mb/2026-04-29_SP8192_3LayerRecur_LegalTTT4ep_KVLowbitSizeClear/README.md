# SP8192 3-Layer Recurrence + Legal TTT 4ep + KV Lowbit Size Clear

**val_bpb = 1.07585987** on seed 42 only | 15,961,508 raw script+model bytes | 8xH100

This is a size-clearing fallback submission candidate built from
[`#1812`](https://github.com/openai/parameter-golf/pull/1812). It is not claimed
as a new SOTA over `#1812`; it trades a small amount of BPB for a wider artifact
margin by quantizing only the final block's attention K/V matrices to int5.

## Result

| Seed | Pre-quant BPB | Quantized BPB | Sliding BPB | TTT BPB | Model B | Raw script+model B | Train | Eval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | 1.08297128 | 1.09380490 | 1.07717917 | **1.07585987** | 15,941,863 | 15,961,508 | 600.015s | 446.947s |

Seed 314 was started during validation, but the Runpod direct TCP endpoint
dropped during post-training quantization and the result was not copied back.
This PR intentionally reports only the completed seed 42 run.

## Changes From `#1812`

- Brotli compression uses `lgwin=24`.
- TTT chunk size is set to `32768`.
- GPTQ uses `LOWBIT_LAYERS=blocks.10.attn.c_k.weight:5,blocks.10.attn.c_v.weight:5`.

All other architecture, optimizer, data, tokenizer, and legal score-first TTT
logic are inherited from `#1812`.

## Reproduction

```bash
pip install brotli sentencepiece
pip install flash_attn_3 --no-deps \
  --find-links https://windreamer.github.io/flash-attention3-wheels/cu128_torch291/

MATCHED_FINEWEB_REPO_ID=kevclark/parameter-golf \
  python3 data/cached_challenge_fineweb.py --variant sp8192

RUN_ID=pr1812_full8_seed42_lgwin24_lowbit_attn10_kv \
SEED=42 \
MATCHED_FINEWEB_REPO_ID=kevclark/parameter-golf \
TOKENIZER_PATH=./data/tokenizers/fineweb_8192_bpe.model \
TRAIN_FILES=./data/datasets/fineweb10B_sp8192/fineweb_train_*.bin \
VAL_FILES=./data/datasets/fineweb10B_sp8192/fineweb_val_*.bin \
MAX_WALLCLOCK_SECONDS=600 \
GPTQ_CALIBRATION_BATCHES=64 \
LOWBIT_LAYERS=blocks.10.attn.c_k.weight:5,blocks.10.attn.c_v.weight:5 \
TTT_ENABLED=1 \
TTT_LR=0.005 \
TTT_EPOCHS=4 \
TTT_CHUNK_TOKENS=32768 \
torchrun --standalone --nproc_per_node=8 train_gpt.py
```

## Compliance Notes

- Official SP8192 tokenizer and FineWeb data; no tokenizer changes.
- Legal score-first TTT: score each chunk before updating on already-scored
  tokens.
- Full normalized softmax distribution; no n-gram cache, ETLB, or SLOT.
- No pre-quant validation TTT.
- Model artifact is below 16,000,000 bytes.
- Raw packed script plus model is below 16,000,000 bytes for the recorded seed.

## Included Files

- `README.md`
- `submission.json`
- `train_gpt.py`
- `seed42.log`
- `command_seed42.txt`
