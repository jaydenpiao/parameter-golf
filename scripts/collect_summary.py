#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


STEP_VAL_RE = re.compile(r"^step:\d+/\d+ val_loss:[0-9.]+ val_bpb:([0-9.]+) train_time:(\d+)ms")
STANDARD_FINAL_RE = re.compile(
    r"^final_int8_zlib_roundtrip(?:_exact)? val_loss:[0-9.]+ val_bpb:([0-9.]+)(?: eval_time:(\d+)ms)?$"
)
SLIDING_FINAL_RE = re.compile(
    r"^final_sliding_window_eval(?:_exact)? stride:(\d+) val_loss:[0-9.]+ val_bpb:([0-9.]+)(?: eval_time:(\d+)ms)?$"
)
TTT_FINAL_RE = re.compile(
    r"^final_ttt_eval(?:_exact)? chunk_tokens:(\d+) epochs:(\d+) lr:([0-9.]+) "
    r"val_loss:[0-9.]+ val_bpb:([0-9.]+)(?: eval_time:(\d+)ms)?$"
)
MODEL_BYTES_RE = re.compile(r"^(?:Serialized model int8\+zlib|serialized_model_int8_zlib):\s*(\d+)\s*bytes")
CODE_BYTES_RE = re.compile(r"^Code size:\s*(\d+)\s*bytes$")
ARTIFACT_BYTES_RE = re.compile(r"^Total submission size int8\+zlib:\s*(\d+)\s*bytes$")
TRAIN_TIME_RE = re.compile(r"train_time:(\d+)ms")


def parse_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def validate_summary(summary: dict[str, object]) -> None:
    required = {
        "track": str,
        "seed": int,
        "train_seconds": (int, float),
        "eval_seconds": (int, float),
        "artifact_bytes": int,
        "code_bytes": int,
        "model_bytes": int,
        "pre_quant_bpb": (int, float),
        "post_quant_bpb": (int, float),
        "eval_mode": str,
        "config_name": str,
        "git_sha": str,
    }
    for key, expected_type in required.items():
        if key not in summary:
            raise ValueError(f"missing summary field: {key}")
        if not isinstance(summary[key], expected_type):
            raise ValueError(f"invalid type for {key}: {type(summary[key]).__name__}")


def current_git_sha(repo_root: Path) -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True)
        .strip()
    )


def current_git_dirty(repo_root: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            text=True,
        ).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a run log into results/<run-id>/summary.json")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    env = parse_env(args.config)

    run_id = env.get("RUN_ID", args.log.stem)
    out_path = args.out or repo_root / "results" / run_id / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pre_quant_bpb: float | None = None
    train_ms: int | None = None
    standard_post_quant_bpb: float | None = None
    standard_eval_ms: int | None = None
    sliding_post_quant_bpb: float | None = None
    sliding_eval_ms: int | None = None
    sliding_stride: int | None = None
    ttt_post_quant_bpb: float | None = None
    ttt_eval_ms: int | None = None
    ttt_chunk_tokens: int | None = None
    ttt_epochs: int | None = None
    ttt_lr: float | None = None
    model_bytes: int | None = None
    code_bytes: int | None = None
    artifact_bytes: int | None = None

    for line in args.log.read_text().splitlines():
        step_match = STEP_VAL_RE.match(line)
        if step_match:
            pre_quant_bpb = float(step_match.group(1))
            train_ms = int(step_match.group(2))
            continue

        standard_match = STANDARD_FINAL_RE.match(line)
        if standard_match:
            standard_post_quant_bpb = float(standard_match.group(1))
            if standard_match.group(2):
                standard_eval_ms = int(standard_match.group(2))
            continue

        sliding_match = SLIDING_FINAL_RE.match(line)
        if sliding_match:
            sliding_stride = int(sliding_match.group(1))
            sliding_post_quant_bpb = float(sliding_match.group(2))
            if sliding_match.group(3):
                sliding_eval_ms = int(sliding_match.group(3))
            continue

        ttt_match = TTT_FINAL_RE.match(line)
        if ttt_match:
            ttt_chunk_tokens = int(ttt_match.group(1))
            ttt_epochs = int(ttt_match.group(2))
            ttt_lr = float(ttt_match.group(3))
            ttt_post_quant_bpb = float(ttt_match.group(4))
            if ttt_match.group(5):
                ttt_eval_ms = int(ttt_match.group(5))
            continue

        if model_bytes is None:
            model_match = MODEL_BYTES_RE.match(line)
            if model_match:
                model_bytes = int(model_match.group(1))
                continue

        if code_bytes is None:
            code_match = CODE_BYTES_RE.match(line)
            if code_match:
                code_bytes = int(code_match.group(1))
                continue

        if artifact_bytes is None:
            artifact_match = ARTIFACT_BYTES_RE.match(line)
            if artifact_match:
                artifact_bytes = int(artifact_match.group(1))
                continue

        if train_ms is None:
            train_match = TRAIN_TIME_RE.search(line)
            if train_match:
                train_ms = int(train_match.group(1))

    if pre_quant_bpb is None:
        raise ValueError("could not parse pre-quant val_bpb from log")
    if train_ms is None:
        raise ValueError("could not parse train_time from log")
    if model_bytes is None:
        raise ValueError("could not parse compressed model bytes from log")
    if code_bytes is None:
        code_bytes = args.source.stat().st_size
    if artifact_bytes is None:
        artifact_bytes = model_bytes + code_bytes
    requested_eval_stride = int(env.get("EVAL_STRIDE", "0"))
    requested_ttt = bool(int(env.get("TTT_ENABLED", "0")))
    if requested_ttt:
        if ttt_post_quant_bpb is None:
            raise ValueError("config requested TTT eval but no final_ttt_eval metric was found")
        eval_mode = "score_first_ttt"
        post_quant_bpb = ttt_post_quant_bpb
        eval_ms = ttt_eval_ms or 0
    elif requested_eval_stride > 0:
        if sliding_post_quant_bpb is None:
            raise ValueError("config requested sliding eval but no final_sliding_window_eval metric was found")
        eval_mode = "sliding_window"
        post_quant_bpb = sliding_post_quant_bpb
        eval_ms = sliding_eval_ms or 0
    else:
        if standard_post_quant_bpb is None:
            raise ValueError("could not parse final standard post-quant val_bpb from log")
        eval_mode = "standard_roundtrip"
        post_quant_bpb = standard_post_quant_bpb
        eval_ms = standard_eval_ms or 0

    command_path = out_path.parent / "command.sh"
    repro_command = command_path.read_text().strip() if command_path.exists() else ""

    summary = {
        "track": env.get("TRACK", "track_a"),
        "seed": int(env.get("SEED", "1337")),
        "train_seconds": round(train_ms / 1000.0, 3),
        "eval_seconds": round(eval_ms / 1000.0, 3),
        "artifact_bytes": artifact_bytes,
        "code_bytes": code_bytes,
        "model_bytes": model_bytes,
        "pre_quant_bpb": pre_quant_bpb,
        "post_quant_bpb": post_quant_bpb,
        "eval_mode": eval_mode,
        "eval_stride": requested_eval_stride,
        "config_name": env.get("CONFIG_NAME", args.config.stem),
        "git_sha": current_git_sha(repo_root),
        "git_dirty": current_git_dirty(repo_root),
        "repro_command": repro_command,
    }
    if standard_post_quant_bpb is not None:
        summary["standard_post_quant_bpb"] = standard_post_quant_bpb
    if standard_eval_ms is not None:
        summary["standard_eval_seconds"] = round(standard_eval_ms / 1000.0, 3)
    if sliding_post_quant_bpb is not None:
        summary["sliding_post_quant_bpb"] = sliding_post_quant_bpb
    if sliding_eval_ms is not None:
        summary["sliding_eval_seconds"] = round(sliding_eval_ms / 1000.0, 3)
    if sliding_stride is not None:
        summary["sliding_stride"] = sliding_stride
    if ttt_post_quant_bpb is not None:
        summary["ttt_post_quant_bpb"] = ttt_post_quant_bpb
    if ttt_eval_ms is not None:
        summary["ttt_eval_seconds"] = round(ttt_eval_ms / 1000.0, 3)
    if ttt_chunk_tokens is not None:
        summary["ttt_chunk_tokens"] = ttt_chunk_tokens
    if ttt_epochs is not None:
        summary["ttt_epochs"] = ttt_epochs
    if ttt_lr is not None:
        summary["ttt_lr"] = ttt_lr

    validate_summary(summary)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
