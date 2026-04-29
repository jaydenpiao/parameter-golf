#!/usr/bin/env python3
"""Patch packed Parameter Golf record scripts for scratch research runs.

Several competitive record folders store train scripts as a tiny wrapper around
an lzma-compressed base85 payload. This helper unpacks that payload, applies
exact string replacements, and writes a repacked script. It is intended for
scratch clones only; do not use it to make silent submission changes.
"""

from __future__ import annotations

import argparse
import base64
import json
import lzma
import re
from pathlib import Path


PACKED_RE = re.compile(
    r'import lzma as L,base64 as B\n'
    r'exec\(L\.decompress\(B\.b85decode\("(?P<payload>.*)"\),'
    r'format=L\.FORMAT_RAW,filters=\[\{"id":L\.FILTER_LZMA2\}\]\)\)',
    re.DOTALL,
)
FILTERS = [{"id": lzma.FILTER_LZMA2}]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Packed record script to read")
    parser.add_argument("--output", help="Packed script path to write")
    parser.add_argument("--unpack-to", help="Optional path for the unpacked payload")
    parser.add_argument(
        "--replace",
        nargs=2,
        metavar=("OLD", "NEW"),
        action="append",
        default=[],
        help=(
            "Exact string replacement to apply to the unpacked payload. "
            "Each OLD string must occur exactly once."
        ),
    )
    return parser.parse_args()


def unpack_packed_script(path: Path) -> str:
    packed = path.read_text()
    match = PACKED_RE.fullmatch(packed.strip())
    if not match:
        raise ValueError(f"{path} does not match the expected packed-script wrapper")

    payload = base64.b85decode(match.group("payload"))
    return lzma.decompress(payload, format=lzma.FORMAT_RAW, filters=FILTERS).decode()


def apply_replacements(source: str, replacements: list[tuple[str, str]]) -> tuple[str, int]:
    total = 0
    for old, new in replacements:
        count = source.count(old)
        if count != 1:
            raise ValueError(
                f"replacement target must occur exactly once; found {count}: {old!r}"
            )
        source = source.replace(old, new, 1)
        total += 1
    return source, total


def pack_script(source: str) -> str:
    compressed = lzma.compress(
        source.encode(),
        format=lzma.FORMAT_RAW,
        filters=FILTERS,
    )
    payload = base64.b85encode(compressed).decode()
    return (
        "import lzma as L,base64 as B\n"
        f'exec(L.decompress(B.b85decode("{payload}"),'
        'format=L.FORMAT_RAW,filters=[{"id":L.FILTER_LZMA2}]))\n'
    )


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    source = unpack_packed_script(input_path)
    source, replacement_count = apply_replacements(source, args.replace)

    if args.unpack_to:
        unpack_path = Path(args.unpack_to)
        unpack_path.parent.mkdir(parents=True, exist_ok=True)
        unpack_path.write_text(source)

    output_path = None
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(pack_script(source))

    print(
        json.dumps(
            {
                "input": str(input_path),
                "output": str(output_path) if output_path else None,
                "unpack_to": args.unpack_to,
                "replacements": replacement_count,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
