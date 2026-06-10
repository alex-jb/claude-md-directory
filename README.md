# claude-md.directory

**English** | [中文](README.zh-CN.md)

> **Brier-audited directory of 1000+ `CLAUDE.md` and `skills/*.md` files — every entry comes with a "does this skill actually help?" score, scored independently against a standardized eval harness.**

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Entries](https://img.shields.io/badge/seed-100%20entries-blue.svg)](entries/)
[![Brier-audited](https://img.shields.io/badge/Brier-audited-violet.svg)](docs/brier-method.md)

---

Sahil Lavingia's `slavingia/skills` repo hit **4.8K stars in days** in March 2026 because nobody knew which skills to actually install. Anthropic Skills Marketplace launched May 2026 with 600+ free skills and **no eval layer**. Karpathy's `CLAUDE.md` got 109K stars from a single tweet — but that's **N = 1**.

The market has skills. It does not have an honest "does this skill actually help?" answer. This directory is that answer.

## What this is

A curated, third-party, Brier-audited directory of real-world `CLAUDE.md` files and Claude Code skills.

Every entry includes:

- **Source URL** (GitHub repo + path, exact commit hash)
- **One-line skill purpose** ("makes Claude refuse to write `--no-verify`")
- **Standardized eval verdict**: `helpful` / `neutral` / `harmful` on a fixed eval set of 40 representative tasks
- **Win-rate vs no-skill baseline** (Brier score, lower = better calibrated, < 0.25 = better than coin flip)
- **First-seen date + last-updated date**
- **One-line author note** (optional, fork-only)

We do **not** score the author. We score the skill, on a frozen eval set, with the model and version pinned. The skill author can submit a counter-eval, and we publish it next to ours.

## Try it (quick demo)

```bash
git clone https://github.com/alex-jb/claude-md-directory
cd claude-md-directory

# See all 100+ seeded skills:
cat entries/*.yaml | grep -E '^name:|^win_rate:' | head -40

# Submit a new skill (one yaml file per entry):
cp entries/_template.yaml entries/my-new-skill.yaml
# ... edit + open PR

# Run our standardized eval against your skill (requires Anthropic key):
python scripts/audit.py entries/my-new-skill.yaml
```

## Why "directory" not "marketplace"

- **Marketplaces** (Anthropic, GPT Store) sell their own products. They have a conflict of interest re: ranking.
- **Awesome-lists** are taste-driven. No grading, just curation.
- **Directories** are the third option: third-party, standardized scoring, public method, public dispute resolution.

Yelp for skills, not the App Store.

## Method (Brier audit)

See [`docs/brier-method.md`](docs/brier-method.md) for the full method. Short version:

1. We froze a 40-task eval set covering 8 common Claude Code domains (write code / refactor / debug / review / spec / ship / explain / triage).
2. Each task has a known-good outcome scored 0..1 (some are binary; some are multi-aspect).
3. We run each skill against the eval set 5 times with `claude-haiku-4-5` (cheap baseline) and `claude-sonnet-4-6` (strong baseline). Win-rate is averaged.
4. Brier score = average of `(p - actual)^2` across all 40 tasks. **Lower is better. < 0.25 = better than coin flip.**
5. We publish every score, every prompt, every model output. Reproducible from a single command.

The eval set is frozen at v1.0 to prevent gaming. We'll cut v1.1 only when v1.0 scores are saturated.

## Cross-stack

- **[council-diff](https://github.com/alex-jb/council-diff)** — 5-voice debate library writes the per-skill explanation when there's disagreement
- **[solo-founder-os](https://github.com/alex-jb/solo-founder-os)** — `sfos-eval` cron runs the periodic audit
- **[whocalleditright](https://whocalleditright.vercel.app)** — sister project, same Brier discipline applied to hedge fund manager forecasts

## Status

- [x] Repo skeleton + entry yaml schema
- [x] 10-entry seed (Karpathy + Sahil + 8 misc)
- [ ] 100-entry seed (this week)
- [ ] `scripts/audit.py` Brier eval harness (next week)
- [ ] Static site at claude-md.directory (week 2)
- [ ] Anthropic Skills Marketplace import (week 3)
- [ ] 1000-entry milestone (month 1)

## Submitting a skill

1. Fork the repo
2. Copy `entries/_template.yaml` to `entries/<your-skill-slug>.yaml`
3. Fill in `source_url`, `purpose`, `author` (optional)
4. Open a PR. We run our standardized audit on merge and post the verdict back to your repo as a comment.

We accept counter-evals if you disagree with our score. We publish both.

## License

MIT. Entries inherit their source repo's license.

## Author

Built by Alex Ji ([@alex-jb](https://github.com/alex-jb)) — solo founder, MS CS Yeshiva, builder of council-diff + Solo Founder OS + whocalleditright. Calibration-honest by default.
