#!/usr/bin/env python3
"""Write a smaller Parameter Golf shard with a valid 256-int32 header.

This is for local research loops only. It preserves the shard magic/version,
updates the token count in header[2], and copies the requested number of
uint16 tokens from the source shard.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


HEADER_DTYPE = np.dtype("<i4")
TOKEN_DTYPE = np.dtype("<u2")
HEADER_INTS = 256
MAGIC = 20240520
VERSION = 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Source shard path")
    parser.add_argument("--output", required=True, help="Destination shard path")
    parser.add_argument(
        "--num-tokens",
        required=True,
        type=int,
        help="Number of uint16 tokens to keep",
    )
    parser.add_argument(
        "--symlink-train-from",
        help=(
            "Optional train shard path to symlink beside --output. "
            "Useful when building a reduced validation dataset directory."
        ),
    )
    return parser.parse_args()


def read_header(path: Path) -> np.ndarray:
    header = np.fromfile(path, dtype=HEADER_DTYPE, count=HEADER_INTS)
    if header.size != HEADER_INTS:
        raise ValueError(f"{path} is missing the full shard header")
    if int(header[0]) != MAGIC or int(header[1]) != VERSION:
        raise ValueError(
            f"{path} has unexpected shard header: magic={int(header[0])} version={int(header[1])}"
        )
    return header


def write_reduced_shard(src: Path, dst: Path, num_tokens: int) -> None:
    if num_tokens <= 0:
        raise ValueError("--num-tokens must be positive")

    header = read_header(src)
    src_tokens = int(header[2])
    if num_tokens > src_tokens:
        raise ValueError(
            f"--num-tokens={num_tokens} exceeds source shard token count {src_tokens}"
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    header = header.copy()
    header[2] = num_tokens

    header_bytes = HEADER_INTS * HEADER_DTYPE.itemsize
    token_bytes = num_tokens * TOKEN_DTYPE.itemsize

    with src.open("rb") as handle:
        handle.seek(header_bytes)
        tokens = handle.read(token_bytes)

    if len(tokens) != token_bytes:
        raise ValueError(
            f"Short read from {src}: expected {token_bytes} token bytes, got {len(tokens)}"
        )

    with dst.open("wb") as handle:
        handle.write(header.tobytes())
        handle.write(tokens)


def maybe_symlink_train(output_shard: Path, train_src: Path) -> Path:
    dst = output_shard.parent / train_src.name
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    dst.symlink_to(train_src.resolve())
    return dst


def main() -> None:
    args = parse_args()
    src = Path(args.input)
    dst = Path(args.output)
    write_reduced_shard(src, dst, args.num_tokens)

    print(
        {
            "output": str(dst),
            "size_bytes": dst.stat().st_size,
            "num_tokens": args.num_tokens,
        }
    )

    if args.symlink_train_from:
        linked = maybe_symlink_train(dst, Path(args.symlink_train_from))
        print({"train_symlink": str(linked), "target": str(linked.resolve())})


if __name__ == "__main__":
    main()
