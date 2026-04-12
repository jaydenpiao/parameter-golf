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
