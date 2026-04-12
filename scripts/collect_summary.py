#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


STEP_VAL_RE = re.compile(r"^step:\d+/\d+ val_loss:[0-9.]+ val_bpb:([0-9.]+) train_time:(\d+)ms")
FINAL_RE = re.compile(
    r"^final_int8_zlib_roundtrip(?:_exact)? val_loss:[0-9.]+ val_bpb:([0-9.]+)(?: eval_time:(\d+)ms)?$"
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
    post_quant_bpb: float | None = None
    eval_ms: int | None = None
    model_bytes: int | None = None
    code_bytes: int | None = None
    artifact_bytes: int | None = None

    for line in args.log.read_text().splitlines():
        step_match = STEP_VAL_RE.match(line)
        if step_match:
            pre_quant_bpb = float(step_match.group(1))
            train_ms = int(step_match.group(2))
            continue

        final_match = FINAL_RE.match(line)
        if final_match:
            post_quant_bpb = float(final_match.group(1))
            if final_match.group(2):
                eval_ms = int(final_match.group(2))
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
    if post_quant_bpb is None:
        raise ValueError("could not parse final post-quant val_bpb from log")
    if train_ms is None:
        raise ValueError("could not parse train_time from log")
    if model_bytes is None:
        raise ValueError("could not parse compressed model bytes from log")
    if code_bytes is None:
        code_bytes = args.source.stat().st_size
    if artifact_bytes is None:
        artifact_bytes = model_bytes + code_bytes
    if eval_ms is None:
        eval_ms = 0

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
        "config_name": env.get("CONFIG_NAME", args.config.stem),
        "git_sha": current_git_sha(repo_root),
        "repro_command": repro_command,
    }

    validate_summary(summary)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
