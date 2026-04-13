#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


ENV_GET_RE = re.compile(
    r'os\.environ\.get\("([A-Z0-9_]+)"'
    r"|os\.environ\.get\('([A-Z0-9_]+)'"
    r'|os\.environ\["([A-Z0-9_]+)"\]'
    r"|os\.environ\['([A-Z0-9_]+)'\]"
)

WRAPPER_ONLY_VARS = {
    "CONFIG_NAME",
    "TRACK",
    "TOKENIZER_VARIANT",
    "TARGET_HARDWARE_TIER",
    "RESULTS_TAG",
    "TRAIN_SHARDS",
    "NPROC_PER_NODE",
}


def parse_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def extract_supported_vars(path: Path) -> set[str]:
    supported: set[str] = set()
    for match in ENV_GET_RE.finditer(path.read_text()):
        for group in match.groups():
            if group:
                supported.add(group)
    return supported


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail if a config uses env vars that the training source does not consume."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()

    env = parse_env(args.config)
    supported = extract_supported_vars(args.source)
    unsupported = sorted(set(env) - WRAPPER_ONLY_VARS - supported)

    if unsupported:
        unsupported_list = ", ".join(unsupported)
        raise SystemExit(
            "config support check failed: "
            f"{args.config.name} sets unsupported env vars for {args.source.name}: {unsupported_list}"
        )

    print(
        "config support check passed: "
        f"{args.config.name} is compatible with {args.source.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
