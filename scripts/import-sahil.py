"""
import-sahil.py — bulk-import slavingia/skills (10 skills) as directory entries.

Pulls each skill directory's SKILL.md from the slavingia/skills repo, parses
the front-matter, and writes a yaml entry under entries/. Skip-if-exists.

Usage:
    python scripts/import-sahil.py
    python scripts/import-sahil.py --dry-run

Requires:
    pip install requests pyyaml

Cost: $0 (pure GitHub API + raw text fetch). No Claude calls; audit.py is
the separate step that grades each entry.
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
GITHUB_API = "https://api.github.com/repos/slavingia/skills/contents/skills"
GITHUB_RAW = "https://raw.githubusercontent.com/slavingia/skills/main/skills"

# Domain mapping per Sahil's skill semantics.
DOMAIN_MAP = {
    "company-values": "spec",
    "find-community": "spec",
    "first-customers": "spec",
    "grow-sustainably": "spec",
    "marketing-plan": "spec",
    "minimalist-review": "review",
    "mvp": "spec",
    "pricing": "spec",
    "processize": "ship",
    "validate-idea": "spec",
}


def list_skills() -> list[str]:
    r = requests.get(GITHUB_API, timeout=20)
    r.raise_for_status()
    return sorted(d["name"] for d in r.json() if d["type"] == "dir")


def fetch_skill_md(slug: str) -> str:
    url = f"{GITHUB_RAW}/{slug}/SKILL.md"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.text


def extract_purpose(skill_md: str) -> str:
    """
    Pull the one-line skill description. Prefer YAML front-matter
    `description:` field, fall back to first non-blank prose line.
    """
    # Front-matter: --- ... description: "..." ... ---
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", skill_md, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1))
            desc = fm.get("description") if isinstance(fm, dict) else None
            if desc:
                # First sentence only
                return str(desc).strip().split(".")[0].strip()
        except Exception:
            pass

    # Fall back: first non-header non-blank line
    for line in skill_md.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("---"):
            return s.split(".")[0].strip()
    return f"slavingia/skills/{ROOT}"


def write_entry(slug: str, skill_md: str, dry_run: bool = False) -> Path:
    domain = DOMAIN_MAP.get(slug, "spec")
    purpose = extract_purpose(skill_md)

    entry = {
        "slug": f"sahil-{slug}",
        "name": f"Sahil /{slug}",
        "source_url": f"https://github.com/slavingia/skills/blob/main/skills/{slug}/SKILL.md",
        "source_commit": "pending",  # fill in on first audit
        "purpose": purpose,
        "domain": domain,
        "type": "skill_md",
        "author": "slavingia",
        "author_note": (
            "One of 10 skills Sahil distilled from his book The Minimalist "
            "Entrepreneur. Viral on X March 2026 (459K views in 1 week)."
        ),
    }

    path = ENTRIES / f"sahil-{slug}.yaml"
    if path.exists() and not dry_run:
        # Skip if already exists — don't blow away existing audit results
        print(f"  skip (exists): {path.name}")
        return path

    if dry_run:
        print(f"[dry-run] would write {path.name} — purpose: {purpose}")
        return path

    with open(path, "w") as f:
        yaml.safe_dump(entry, f, sort_keys=False, allow_unicode=True)
    print(f"  wrote {path.name} — domain={domain}")
    return path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    skills = list_skills()
    print(f"slavingia/skills has {len(skills)} skill directories: {skills}\n")

    written = 0
    for slug in skills:
        try:
            md = fetch_skill_md(slug)
            write_entry(slug, md, dry_run=args.dry_run)
            written += 1
        except Exception as e:
            print(f"  fail {slug}: {e}")

    print(f"\ndone — {written} entries processed (entries/ now ~{len(list(ENTRIES.glob('*.yaml')))} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
