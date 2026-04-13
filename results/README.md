# Results Layout

Each concrete run should emit its own folder:

```text
results/<run-id>/
  summary.json
  train.log
  eval.log
  command.sh
```

`summary.json` is the canonical machine-readable record for dashboards, checks,
promotion decisions, and PR preparation. The schema lives in
`results/summary.schema.json`.

When a run enables an alternate evaluation mode such as sliding-window eval,
`post_quant_bpb` and `eval_seconds` should reflect the configured canonical mode.
Preserve the standard roundtrip metrics in separate fields such as
`standard_post_quant_bpb` and `standard_eval_seconds` so comparisons stay explicit.

Runs should record both `git_sha` and `git_dirty`. A SHA without dirty-state
information is not enough to reproduce a run from an uncommitted worktree.

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
