# HN Show

**Title** (≤80 chars):
Show HN: I built a Brier-audited directory of Claude.md and skills files

**URL**:
https://github.com/alex-jb/claude-md-directory

**Body**:

In March 2026 Sahil Lavingia tweeted 9 Claude Code skills and hit 4.8k stars in days. In May 2026 Anthropic launched their Skills Marketplace with 600+ free skills. Karpathy's CLAUDE.md got 109k stars from a single tweet.

The market has skills. What it doesn't have is an honest answer to "does this skill actually help, or am I cargo-culting?" My friends keep installing skills on faith and then wondering why their Claude Code session feels different on Tuesday than Monday.

I built a third-party Brier-audited directory of CLAUDE.md and skills/*.md files. Every entry comes with:

- Source URL + exact commit hash
- Frozen 5-task v1.0 eval set (will grow to 40)
- Brier score (lower = better calibrated, < 0.25 = better than coin flip)
- Verdict: helpful / neutral / harmful relative to no-skill baseline
- Author counter-eval published next to ours if they disagree

The eval set is frozen on purpose so authors can't tune to the benchmark. Method: run skill against the eval set with `claude-haiku-4-5`, deterministic grading per task type (refuses certain strings / contains expected concepts / response stays short), Brier-score against the ideal. Reproducible from a single `python scripts/audit.py entries/<slug>.yaml`.

It's intentionally not a marketplace and not an awesome-list:
- Marketplaces sell their own products (conflict of interest re ranking)
- Awesome-lists are taste-driven (no grading, no method)
- A directory is the third option — third-party, public method, public dispute

The 7 seed entries are Karpathy's CLAUDE.md, three of Sahil's nine skills (find-community / mvp / pricing), Anthropic's cybersecurity-skills bundle, and one popular community CLAUDE.md. Hundred-entry seed lands this week.

Repo: https://github.com/alex-jb/claude-md-directory · MIT · single developer · feedback welcome on the eval set itself.

What I'd love feedback on:
1. Is the 5-task v1.0 eval set the right shape? Should it be 40 tasks like I'm planning, or should it stay small + community-extended via subdomain v1-write.yaml / v1-debug.yaml etc?
2. How do you handle gaming? Right now I freeze the eval set and publish counter-eval claims; what else would you add?
3. What skills should I prioritize seeding next? I'm pulling from `slavingia/skills`, `anthropics/cybersecurity-skills`, and the awesome-claude-code wong2 list; what am I missing?

Sister project: github.com/alex-jb/whocalleditright — same Brier discipline applied to hedge fund manager forecasts.
