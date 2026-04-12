#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np


HEADER_DTYPE = np.dtype("<i4")
TOKEN_DTYPE = np.dtype("<u2")
HEADER_WORDS = 256


def read_header(path: Path) -> np.ndarray:
    header = np.fromfile(path, dtype=HEADER_DTYPE, count=HEADER_WORDS)
    if header.size != HEADER_WORDS:
        raise ValueError(f"short header: {path}")
    if int(header[0]) != 20240520 or int(header[1]) != 1:
        raise ValueError(f"unexpected shard header: {path}")
    return header


def read_tokens(path: Path, limit: int | None = None) -> np.ndarray:
    header = read_header(path)
    num_tokens = int(header[2])
    if limit is not None:
        num_tokens = min(num_tokens, limit)
    return np.fromfile(
        path,
        dtype=TOKEN_DTYPE,
        count=num_tokens,
        offset=HEADER_WORDS * HEADER_DTYPE.itemsize,
    )


def write_shard(path: Path, header: np.ndarray, tokens: np.ndarray) -> None:
    out_header = header.copy()
    out_header[2] = int(tokens.size)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        out_header.astype(HEADER_DTYPE).tofile(f)
        tokens.astype(TOKEN_DTYPE, copy=False).tofile(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a tiny smoke dataset from a full FineWeb export")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--val-tokens", required=True, type=int)
    args = parser.parse_args()

    source_root = args.source_root
    target_root = args.target_root

    train_src = source_root / "fineweb_train_000000.bin"
    val_src = source_root / "fineweb_val_000000.bin"
    if not train_src.exists() or not val_src.exists():
        raise FileNotFoundError("expected fineweb_train_000000.bin and fineweb_val_000000.bin in source root")

    target_root.mkdir(parents=True, exist_ok=True)

    train_dst = target_root / train_src.name
    if train_dst.exists() or train_dst.is_symlink():
        train_dst.unlink()
    os.symlink(os.path.relpath(train_src, start=target_root), train_dst)

    val_header = read_header(val_src)
    val_tokens = read_tokens(val_src, limit=args.val_tokens)
    write_shard(target_root / val_src.name, val_header, val_tokens)

    print(target_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
