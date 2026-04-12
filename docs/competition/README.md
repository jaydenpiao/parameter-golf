# Parameter Golf Operating Model

This fork is organized around one rule: a run only counts once it is reproducible,
metric-correct, legal under Issue #1017, under the artifact cap, and within the
training and evaluation wallclock budgets.

## Source Of Truth

- Challenge page: https://openai.com/index/parameter-golf/
- Upstream repo: https://github.com/openai/parameter-golf
- Evaluation compliance checklist: https://github.com/openai/parameter-golf/issues/1017
- Illegal submissions megathread: https://github.com/openai/parameter-golf/issues/677

Challenge window confirmed from upstream README: March 18, 2026 to April 30, 2026.

## Repository Workflow

- `origin` is this fork: `jaydenpiao/parameter-golf`
- `upstream` is the official repo: `openai/parameter-golf`
- Keep `main` as a sync point with upstream.
- Do infrastructure and research work on short-lived branches.
- Keep submission branches clean: one upstream PR should add only one
  `records/...` folder plus the exact dependencies that folder requires.

Recommended sync flow:

```bash
git checkout main
git fetch upstream
git rebase upstream/main
git push origin main
```

## Delivery Slices

- PR 1: bootstrap docs, config interface, result schema
- PR 2: MLX smoke harness and tiny-data sanity path
- PR 3: metric, legality, artifact, and timing checks
- PR 4: 1xH100 wrappers, log capture, and result collation
- PR 5+: one method family per PR

Do not combine tokenizer, eval, compression, and architecture changes in one PR
unless the changes are inseparable.

## Competitive Priorities

Work Track B first. The mainline ladder is:

1. official baseline (`sp1024`)
2. sliding-window eval
3. merged frontier components one at a time
4. live frontier ideas one at a time
5. speculative lane kept separate from the mainline

Current merged README SOTA reference:

- PR #1493: `1.0810`

Live frontier PRs to monitor, not trust blindly:

- PR #1561: `1.0783`
- PR #1557: `1.07730`
- PR #1560: `1.07406`
- PR #1575: `1.01671`

## Promotion Policy

- Local Mac runs are plumbing-only.
- 1xH100 is the ablation tier.
- 8xH100 is reserved for promoted candidates.
- Promote a change to 8xH100 only after a reduced run shows a real quality delta
  or a real speed win.
- Require 3 seeds before any submission candidate is treated as real.

## Required Review Checklist

Every candidate that might influence strategy or submissions must answer:

1. Does the run record an exact reproducibility command and git SHA?
2. Does the run pass the Issue #1017 legality checks?
3. Does the BPB path use full validation shards, preserved order, and actual
   tokenizer byte counts?
4. Is `code_bytes + model_bytes < 16_000_000`?
5. Are train and eval wallclocks both explicitly recorded?
