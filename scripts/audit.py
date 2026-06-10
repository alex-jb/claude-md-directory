"""
audit.py — standardized Brier eval harness for claude-md.directory entries.

Runs each skill (CLAUDE.md or skills/*.md content) against a frozen 5-task
eval set on `claude-haiku-4-5`. Compares output to expected outcome,
computes Brier score, and writes the verdict back to the entry's yaml.

Usage:
    # Audit one entry:
    python scripts/audit.py entries/karpathy-claude-md.yaml

    # Audit all entries:
    python scripts/audit.py --all

    # Dry-run (skip the API call, print the prompt):
    python scripts/audit.py entries/karpathy-claude-md.yaml --dry-run

Requires:
    - ANTHROPIC_API_KEY in env
    - pip install anthropic pyyaml requests

Cost: ~$0.0005 per audit pass (5 tasks × Haiku, max_tokens=300).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import yaml  # type: ignore[import-not-found]
import requests

try:
    from anthropic import Anthropic  # type: ignore[import-not-found]
except ImportError:
    print("missing: pip install anthropic", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
EVAL_SET = ROOT / "scripts" / "eval-set-v1.yaml"
MODEL = "claude-haiku-4-5"

# --- Eval mechanics -----------------------------------------------------

def load_eval_set() -> list[dict]:
    """Frozen 5-task v1 eval set covering 5 of 8 canonical domains."""
    with open(EVAL_SET) as f:
        return yaml.safe_load(f)["tasks"]


def fetch_skill_text(source_url: str) -> str:
    """Pull the raw CLAUDE.md or skill text from GitHub."""
    raw = source_url.replace("github.com", "raw.githubusercontent.com").replace(
        "/blob/", "/"
    )
    r = requests.get(raw, timeout=20, headers={"User-Agent": "claude-md-directory/0.1"})
    r.raise_for_status()
    return r.text


def run_task(client: Anthropic, skill_text: str, task: dict) -> tuple[str, float]:
    """Run one task; return (model output, score 0..1 vs expected)."""
    system = skill_text[:4000]  # cap at 4K chars to keep eval comparable
    user = task["prompt"]
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system if system.strip() else "You are a helpful coding assistant.",
        messages=[{"role": "user", "content": user}],
    )
    text_block = next((b for b in resp.content if b.type == "text"), None)
    out = text_block.text if text_block else ""
    score = grade(out, task)
    return out, score


def grade(output: str, task: dict) -> float:
    """
    Deterministic grading per task type.
      - 'contains': all `expect_contains` strings must appear (any-cased), gives
        ratio matched.
      - 'refuses': output must NOT contain `forbidden` strings, gives 1.0 if
        all forbidden are absent.
      - 'shorter_than': output token count must be <= `max_tokens`.
    """
    typ = task.get("type", "contains")
    lower = output.lower()
    if typ == "contains":
        wanted = [s.lower() for s in task.get("expect_contains", [])]
        if not wanted:
            return 0.0
        hits = sum(1 for w in wanted if w in lower)
        return hits / len(wanted)
    if typ == "refuses":
        forbidden = [s.lower() for s in task.get("forbidden", [])]
        return 1.0 if all(s not in lower for s in forbidden) else 0.0
    if typ == "shorter_than":
        return 1.0 if len(output) <= int(task.get("max_chars", 500)) else 0.0
    return 0.0


def brier(scores: list[float]) -> float:
    """
    Brier score against the "ideal" prediction of 1.0 for every task.
    Lower is better. < 0.25 = better than coin-flip baseline.
    """
    if not scores:
        return 1.0
    return sum((1.0 - s) ** 2 for s in scores) / len(scores)


def verdict_from_brier(b: float, baseline: float) -> str:
    """Helpful / neutral / harmful relative to no-skill baseline."""
    delta = baseline - b
    if delta > 0.05:
        return "helpful"
    if delta < -0.05:
        return "harmful"
    return "neutral"


# --- CLI -----------------------------------------------------------------

def audit_entry(path: Path, client: Anthropic, dry_run: bool = False) -> dict:
    with open(path) as f:
        entry = yaml.safe_load(f)

    source_url = entry.get("source_url")
    if not source_url:
        print(f"  skip: source_url missing — {path.name}")
        return entry

    print(f"\n=== auditing {entry.get('slug')} ===")
    print(f"  source: {source_url}")

    try:
        skill_text = fetch_skill_text(source_url)
    except Exception as e:
        print(f"  fetch failed: {e}")
        return entry

    print(f"  fetched {len(skill_text)} chars")

    tasks = load_eval_set()
    skill_scores: list[float] = []
    baseline_scores: list[float] = []

    for i, task in enumerate(tasks, 1):
        print(f"  task {i}/{len(tasks)}: {task['name']}")
        if dry_run:
            print(f"    [dry-run] would call {MODEL}")
            continue

        # With skill
        _, s_skill = run_task(client, skill_text, task)
        skill_scores.append(s_skill)
        # Baseline (no skill)
        _, s_base = run_task(client, "", task)
        baseline_scores.append(s_base)
        print(f"    skill={s_skill:.2f}  baseline={s_base:.2f}")

    if dry_run:
        return entry

    b_skill = brier(skill_scores)
    b_base = brier(baseline_scores)
    win_rate_skill = sum(skill_scores) / len(skill_scores)
    win_rate_base = sum(baseline_scores) / len(baseline_scores)
    v = verdict_from_brier(b_skill, b_base)

    entry["audited_at"] = dt.date.today().isoformat()
    entry["audited_with"] = MODEL
    entry["eval_set_version"] = "1.0"
    entry["win_rate_baseline"] = round(win_rate_base, 3)
    entry["win_rate_with_skill"] = round(win_rate_skill, 3)
    entry["brier_score"] = round(b_skill, 3)
    entry["brier_baseline"] = round(b_base, 3)
    entry["verdict"] = v
    entry["notes"] = (
        f"Brier {b_skill:.3f} vs baseline {b_base:.3f}; "
        f"win-rate {win_rate_skill:.1%} vs {win_rate_base:.1%}. "
        f"5 tasks, Haiku, frozen v1.0 eval set."
    )

    print(f"  → verdict: {v}  brier {b_skill:.3f} (baseline {b_base:.3f})")

    with open(path, "w") as f:
        yaml.safe_dump(entry, f, sort_keys=False, allow_unicode=True)
    print(f"  wrote {path}")
    return entry


def main() -> int:
    p = argparse.ArgumentParser(description="Brier audit for claude-md-directory entries")
    p.add_argument("path", nargs="?", help="entry yaml to audit, or omit + use --all")
    p.add_argument("--all", action="store_true", help="audit every entry in entries/")
    p.add_argument("--dry-run", action="store_true", help="print prompts, skip API")
    args = p.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    client = Anthropic(api_key=api_key) if api_key else None  # type: ignore[arg-type]

    if args.all:
        targets = sorted((ROOT / "entries").glob("*.yaml"))
        targets = [t for t in targets if not t.name.startswith("_")]
    elif args.path:
        targets = [Path(args.path)]
    else:
        print("provide a path or --all", file=sys.stderr)
        return 1

    for t in targets:
        audit_entry(t, client, dry_run=args.dry_run)  # type: ignore[arg-type]

    return 0


if __name__ == "__main__":
    sys.exit(main())
