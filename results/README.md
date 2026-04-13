# Results Layout

Each concrete run should emit its own folder:

```text
results/<run-id>/
  summary.json
  train.log
  eval.log
  command.sh
  artifacts/
```

`summary.json` is the canonical machine-readable record for dashboards, checks,
promotion decisions, and PR preparation. The schema lives in
`results/summary.schema.json`.

When a run enables an alternate evaluation mode such as sliding-window eval,
`post_quant_bpb` and `eval_seconds` should reflect the configured canonical mode.
Preserve the standard roundtrip metrics in separate fields such as
`standard_post_quant_bpb` and `standard_eval_seconds` so comparisons stay explicit.
Score-first TTT runs should keep both the standard roundtrip and sliding metrics in
separate fields while making the TTT result canonical.

Binary runtime artifacts from CUDA runs should live under
`results/<run-id>/artifacts/`, not in repo root, so a clean checkout stays clean
through summary collection.

Runs should record both `git_sha` and `git_dirty`. A SHA without dirty-state
information is not enough to reproduce a run from an uncommitted worktree.

Treat `git_dirty=false` as a promotion requirement. Exploratory runs can still be
dirty, but `scripts/check_promote.sh` should reject them.

Every run that might influence strategy should also carry a manual legality review:

```text
results/<run-id>/
  legality.json
```

Start from `results/legality.template.json` and fill in concrete evidence tied to
the exact config, source file, and evaluation path used by the run. Promotion
checks require this file.

Runs should not be committed by default. Only committed artifacts that are meant
for upstream consumption should go into `records/...`.
