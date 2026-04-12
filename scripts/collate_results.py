#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    rows = []
    for path in sorted((repo_root / "results").glob("*/summary.json")):
      data = json.loads(path.read_text())
      rows.append(
          (
              path.parent.name,
              data["config_name"],
              data["track"],
              data["seed"],
              data["pre_quant_bpb"],
              data["post_quant_bpb"],
              data["artifact_bytes"],
              data["train_seconds"],
              data["eval_seconds"],
          )
      )

    if not rows:
        print("no results found")
        return 0

    header = (
        "run_id",
        "config",
        "track",
        "seed",
        "pre_quant_bpb",
        "post_quant_bpb",
        "artifact_bytes",
        "train_s",
        "eval_s",
    )
    widths = [len(h) for h in header]
    for row in rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(str(value)))

    def render(values: tuple[object, ...]) -> str:
        return "  ".join(str(value).ljust(widths[i]) for i, value in enumerate(values))

    print(render(header))
    print(render(tuple("-" * w for w in widths)))
    for row in rows:
        print(render(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
