# Brier method — claude-md.directory v1.0

This document specifies exactly how every entry in `entries/*.yaml` gets its `verdict`, `brier_score`, and `win_rate_*` numbers. The whole method is open and reproducible from one command.

## 🔴 Metric naming honesty note (added 2026-06-12)

The `brier_score` field in `entries/*.yaml` is computed as `mean((1 - task_score)^2)` where `task_score ∈ {0, 1}` for binary tasks (see `scripts/audit.py:brier`). **This is not a probabilistic Brier score in the textbook sense** — there is no forecast probability anywhere in the pipeline, only a transformed-win-rate squared error against the perfect score of 1.0.

We keep the field name `brier_score` for backward compatibility with downstream consumers, but the truthful description is: **transformed win-rate squared error vs. the perfect skill that gets every task right**. Calling it a Brier score is a vestigial name that this document corrects.

What that means for you:

- Lower is still better. `< 0.25` is still better than coin-flip on this metric.
- Verdicts (`helpful` / `neutral` / `harmful`) are still delta-vs-baseline, which is the comparison that matters.
- Anyone re-doing this with a probabilistic forecast (e.g., Haiku rated `[0, 1]` confidence per task before the answer) would get a true Brier. That's on the roadmap as part of the v1.1 eval-set widening, which also introduces k≥10 repetitions per condition with bootstrap CI gating.
- N=5 binary tasks, single Haiku pass — directional verdicts only. Anyone treating these numbers as statistically significant is doing it wrong; the project goal is the dispute-protocol framework, not the v1.0 numbers in isolation.

For the original motivation (why this kind of measurement matters at all), continue below.

## Why Brier and not "accuracy"

Accuracy is a single threshold. If a skill is right on 4/5 tasks, that's "80%" — but says nothing about how *confident* the model was on the one it got wrong, and nothing about whether the skill *hurt* on tasks it shouldn't have touched. Brier is the standard probabilistic-forecast calibration metric (Brier 1950, Tetlock 2005) and gives us three things accuracy cannot:

1. **Penalty for confident wrong answers** is the same as for unconfident wrong ones — neutralizes the "the skill made the model louder, not better" failure mode.
2. **Continuous scoring** lets partial credit on multi-aspect tasks count without us having to invent thresholds.
3. **Baseline comparison** — Brier vs no-skill baseline gives a *delta* that survives across models and eval-set revisions, so v1.1 results stay readable next to v1.0 results.

Brier score: `mean((predicted_probability - actual_outcome)^2)`. Lower is better. **0.25 = coin-flip baseline.** Below 0.25 = your forecasts are better-calibrated than chance.

In our setup, every task has a known-good outcome scored in `[0, 1]`. We treat the skill's output as a probabilistic forecast that it produced the right answer, score that forecast deterministically (see "Grading" below), and compute Brier across the eval set.

## The frozen v1.0 eval set

`scripts/eval-set-v1.yaml` has **5 tasks** covering 5 of 8 canonical Claude Code domains:

| Domain | Task | Type |
|---|---|---|
| write | `write-bash-no-no-verify` | refuses (skill should NOT include `--no-verify`) |
| refactor | `refactor-three-similar-blocks` | contains (mentions "three" / "premature") |
| debug | `debug-explain-empty-dict` | contains (mentions "key" / "empty") |
| review | `review-spot-secret-leak` | contains (mentions "secret" / "env") |
| ship | `ship-brief-pre-push-checklist` | shorter_than (response ≤ 600 chars) |

This file is **frozen.** Mutations are not allowed once a release is cut. We'll cut `eval-set-v1.1.yaml` only when v1.0 scores saturate (median Brier < 0.05 across the top quartile of entries). v1.1 will not overwrite v1.0 verdicts — entries get both scores side-by-side.

Why a small set: we want every entry's full run log to be cheap (~$0.0005) and reproducible by anyone with a key. A 40-task v2 set is the natural next step once we have 200 audited entries to learn the variance.

## Grading rules per task type

We never grade with an LLM. Grading is purely deterministic given the model output:

- **`contains`** — count of `expect_contains` strings that appear (case-insensitive substring). Score = `hits / len(expect_contains)`. Anti-gaming: forbid words common in unrelated answers (we audit `expect_contains` lists for false positives weekly).
- **`refuses`** — output must NOT contain any string in `forbidden`. Score = 1.0 if all absent else 0.0.
- **`shorter_than`** — output must be ≤ `max_chars`. Score = 1.0 or 0.0.

We don't allow chain-of-thought-aware grading because that's where authors would tune to the benchmark. Strict substring match is unsophisticated by design.

## The audit loop

`scripts/audit.py` does this for every entry:

1. Fetch the raw `CLAUDE.md` / `skills/*.md` from the entry's `source_url` (GitHub raw, follows the `blob/` → `raw.githubusercontent.com/` rewrite).
2. For each of the 5 tasks:
   - **With skill**: send the task's `prompt` as the user message and the fetched skill text (capped at 4K chars to keep comparability fair) as the system prompt. Call `claude-haiku-4-5`, `max_tokens=300`.
   - **Baseline**: send the same task prompt with an empty system prompt (or a single-line "You are a helpful coding assistant.").
3. Grade both outputs with the deterministic grader.
4. Compute Brier(skill) and Brier(baseline). Compute win_rate(skill) and win_rate(baseline).
5. Write back to the yaml: `audited_at`, `audited_with`, `eval_set_version`, `win_rate_*`, `brier_score`, `brier_baseline`, `verdict`, `notes`.

The verdict label:

- **helpful** when `brier_baseline - brier_skill > 0.05` (skill clearly improves over baseline)
- **harmful** when `brier_baseline - brier_skill < -0.05` (skill clearly degrades baseline)
- **neutral** otherwise

The 0.05 delta threshold is empirical; we'll re-tune once n ≥ 100 entries.

## Cost

~$0.0005 per audit pass per entry (5 tasks × 2 runs each × Haiku at $0.0001 per call average). The full 100-entry seed costs ~$0.05 to audit; the full 1000-entry milestone costs ~$0.50. Cheap by design.

## Reproducibility

```bash
git clone https://github.com/alex-jb/claude-md-directory
cd claude-md-directory
pip install anthropic pyyaml requests
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/audit.py entries/sahil-mvp.yaml
```

The output yaml diff is the audit. Commit it. Open a PR with the new score and our CI will re-run independently before merge.

## Anti-gaming protocol

1. **Eval set frozen on v1.0.** No edits without a v1.1 file + re-audit of every entry.
2. **Skill source pinned to commit hash.** Re-fetching is allowed but we hash and compare; mismatched commits get a new entry, not a re-grade.
3. **Right of reply.** Any skill author can submit a counter-eval (their own audit run with their own eval set + method) and we publish both.
4. **Open dispute.** If we mis-grade your skill, open a PR with `verdict: dispute` and a one-paragraph case. We re-run with you on the call.

## Counter-eval protocol

```bash
# Author runs their own audit (any method, any eval set, any model)
# and posts the result + reproducible command to:
#
#   entries/<your-slug>.yaml:counter_eval_url
#
# Example:
counter_eval_url: https://gist.github.com/youruser/abc123
counter_eval_verdict: helpful
counter_eval_notes: |
  Ran the skill against a 12-task domain-specific set on
  claude-sonnet-4-6. Brier 0.18 vs baseline 0.31. Method: ...
```

Both verdicts ship side-by-side on the directory site. We never overwrite an author's counter-eval, only our own primary verdict.

## What's next

- v1.0 → v1.1 will widen the eval set from 5 → 40 tasks across all 8 domains
- Add `claude-sonnet-4-6` as a second grader once n ≥ 100 and we can compare model-dependence of verdicts
- Consider a `power_user` track that grades skills against a 4K-token "realistic codebase context" instead of an empty context — closer to real usage

If you have a strong opinion on the v1.0 method, open an issue. The whole point of being a directory and not a marketplace is that the method is public and dispute-able.

---

Maintained by [@alex-jb](https://github.com/alex-jb). Calibration discipline shared with [whocalleditright](https://whocalleditright.vercel.app) (hedge fund managers), [Orallexa](https://github.com/alex-jb/orallexa-ai-trading-agent) (multi-model trading), and [memory-wall-tracker](https://github.com/alex-jb/memory-wall-tracker) (daily research feed).
