# Self-Review Checklist

Run this checklist before treating a result as signal and again before opening an
upstream submission PR.

## Required Evidence

1. Exact config path
2. Exact training script path
3. Exact `results/<run-id>/command.sh`
4. Exact git SHA in `summary.json`
5. `git_dirty=false` in `summary.json`
6. Exact legality review in `results/<run-id>/legality.json`

## Gate Checks

1. `scripts/check_metric.sh <config> <log> <source>`
2. `scripts/check_artifact.sh results/<run-id>/summary.json`
3. `scripts/check_legality.sh results/<run-id> <source>`
4. `scripts/check_promote.sh <config> <log> <source>`

## Questions To Answer

1. Does the BPB path use tokenizer byte accounting and the full validation split?
2. Does the run preserve validation ordering?
3. If Track B, where exactly does scoring happen before update?
4. Are train and eval both within budget for the target tier?
5. Is the result better than the closest trusted baseline for this lane?
