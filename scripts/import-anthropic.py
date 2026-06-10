"""
import-anthropic.py — bulk-import anthropics/skills repo as directory entries.

Mirrors import-sahil.py for the official Anthropic skills bundle (May 2026
Marketplace launch repo, 600+ skills shipped at launch).

Usage:
    python scripts/import-anthropic.py
    python scripts/import-anthropic.py --dry-run

Pure GitHub API, $0 cost. Audit runs separately via scripts/audit.py.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml  # type: ignore[import-not-found]
import requests

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "entries"
GITHUB_API = "https://api.github.com/repos/anthropics/skills/contents/skills"
GITHUB_RAW = "https://raw.githubusercontent.com/anthropics/skills/main/skills"

# Map Anthropic skill slugs to canonical domains in our 8-domain taxonomy.
# Unknown skills default to "spec" — closest neutral fit until we widen the
# eval set to grade them properly.
DOMAIN_HINTS = {
    "code-review": "review",
    "code-explanation": "explain",
    "debugging": "debug",
    "refactoring": "refactor",
    "writing-docs": "write",
    "writing-tests": "write",
    "git-workflow": "ship",
    "shell-helper": "ship",
    "incident-triage": "triage",
}


def list_skills() -> list[str]:
    r = requests.get(GITHUB_API, timeout=20)
    r.raise_for_status()
    return sorted(d["name"] for d in r.json() if d["type"] == "dir")


def fetch_skill_md(slug: str) -> str:
    """SKILL.md is the standard filename. Fall back to README.md if needed."""
    for fname in ("SKILL.md", "README.md", "skill.md"):
        url = f"{GITHUB_RAW}/{slug}/{fname}"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                return r.text
        except Exception:
            continue
    raise RuntimeError(f"no SKILL.md or README.md in skills/{slug}/")


def extract_purpose(skill_md: str) -> str:
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", skill_md, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1))
            desc = fm.get("description") if isinstance(fm, dict) else None
            if desc:
                return str(desc).strip().split(".")[0].strip()
        except Exception:
            pass
    for line in skill_md.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("---"):
            return s.split(".")[0].strip()
    return "Anthropic official skill"


def write_entry(slug: str, skill_md: str, dry_run: bool = False) -> Path:
    domain = DOMAIN_HINTS.get(slug, "spec")
    purpose = extract_purpose(skill_md)
    entry = {
        "slug": f"anthropic-{slug}",
        "name": f"Anthropic /{slug}",
        "source_url": f"https://github.com/anthropics/skills/blob/main/skills/{slug}/SKILL.md",
        "source_commit": "pending",
        "purpose": purpose,
        "domain": domain,
        "type": "skill_md",
        "author": "anthropics",
        "author_note": (
            "Part of the official Anthropic Skills bundle that shipped with "
            "the Skills Marketplace launch May 2026."
        ),
    }
    path = ENTRIES / f"anthropic-{slug}.yaml"
    if path.exists() and not dry_run:
        print(f"  skip (exists): {path.name}")
        return path
    if dry_run:
        print(f"[dry-run] would write {path.name} — domain={domain} — purpose: {purpose}")
        return path
    with open(path, "w") as f:
        yaml.safe_dump(entry, f, sort_keys=False, allow_unicode=True)
    print(f"  wrote {path.name} — domain={domain}")
    return path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=20, help="cap on number of skills to import")
    args = p.parse_args()

    skills = list_skills()
    print(f"anthropics/skills exposes {len(skills)} skill directories (capping at {args.limit})\n")

    written = 0
    for slug in skills[: args.limit]:
        try:
            md = fetch_skill_md(slug)
            write_entry(slug, md, dry_run=args.dry_run)
            written += 1
        except Exception as e:
            print(f"  fail {slug}: {e}")

    total = len(list(ENTRIES.glob("*.yaml")))
    print(f"\ndone — {written} processed (entries/ now ~{total} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
