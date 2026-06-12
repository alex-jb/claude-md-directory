"""pin_commits.py — resolve every entry's source_url to a frozen commit.

The 2026-06-11 Fable 5 audit caught that every `entries/*.yaml` has
`source_commit: pending` and the README simultaneously promises "exact
commit hash" pinning. This script closes that gap.

For each entry whose `source_commit` is "pending" (or missing), call
the GitHub commits API to resolve the current HEAD commit on the
linked file's branch, fetch the file content at that commit, write
`source_commit: <SHA>` and `source_sha256: <hash>` back to the YAML.

Subsequent `audit.py` runs MUST refuse if the resolved hash drifts —
that's a follow-up commit to audit.py once this lands.

Usage:
    python3 scripts/pin_commits.py             # pin all pending entries
    python3 scripts/pin_commits.py --slug X    # one entry by slug
    python3 scripts/pin_commits.py --check     # exit 1 if any pending remain
    python3 scripts/pin_commits.py --refresh   # re-resolve even already-pinned
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
ENTRIES = REPO / "entries"

GH_API = "https://api.github.com"


def _gh_get(path: str, token: str | None = None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "claude-md-directory pin_commits/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{GH_API}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def _fetch_raw(owner: str, repo: str, ref: str, path: str) -> str:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "pin_commits/0.1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")


_BLOB_RE = re.compile(
    r"https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+?)(?:\?|#|$)"
)


def parse_blob_url(url: str) -> tuple[str, str, str, str] | None:
    """Return (owner, repo, ref, path) from a github.com /blob/ URL."""
    m = _BLOB_RE.match(url.strip())
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3), m.group(4)


def resolve_commit(owner: str, repo: str, ref: str, path: str,
                    token: str | None) -> tuple[str, str]:
    """Return (commit_sha, sha256_of_file_text)."""
    # Newest commit touching this path on this ref
    commits = _gh_get(
        f"/repos/{owner}/{repo}/commits?path={path}&sha={ref}&per_page=1", token
    )
    if not isinstance(commits, list) or not commits:
        raise RuntimeError(f"no commits found for {owner}/{repo}@{ref}:{path}")
    sha = commits[0]["sha"]
    body = _fetch_raw(owner, repo, sha, path)
    sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return sha, sha256


def pin_one(entry_path: Path, token: str | None, refresh: bool) -> bool:
    """Return True if a write occurred."""
    raw = entry_path.read_text()
    entry = yaml.safe_load(raw)
    current = entry.get("source_commit", "pending")
    if current and current != "pending" and not refresh:
        return False
    source_url = entry.get("source_url")
    if not source_url:
        print(f"  skip {entry_path.name}: no source_url")
        return False
    parsed = parse_blob_url(source_url)
    if parsed is None:
        print(f"  skip {entry_path.name}: source_url not a github.com blob URL")
        return False
    owner, repo, ref, path = parsed
    try:
        sha, sha256 = resolve_commit(owner, repo, ref, path, token)
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as e:
        print(f"  ✗ {entry_path.name}: {e}")
        return False

    # Replace fields in raw text instead of round-tripping yaml.dump
    # (which reorders keys and rewrites multi-line strings ugly).
    raw = re.sub(
        r"^source_commit:.*$",
        f"source_commit: {sha}",
        raw,
        count=1,
        flags=re.MULTILINE,
    )
    if "source_sha256:" in raw:
        raw = re.sub(
            r"^source_sha256:.*$",
            f"source_sha256: {sha256}",
            raw,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        raw = re.sub(
            r"^(source_commit: .+)$",
            r"\1\nsource_sha256: " + sha256,
            raw,
            count=1,
            flags=re.MULTILINE,
        )
    entry_path.write_text(raw)
    print(f"  ✓ {entry_path.name}: {sha[:7]} sha256={sha256[:8]}…")
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slug", default=None, help="only this entry's slug")
    p.add_argument("--check", action="store_true",
                   help="exit 1 if any entry still has pending source_commit")
    p.add_argument("--refresh", action="store_true",
                   help="re-resolve even already-pinned commits")
    args = p.parse_args()

    if args.check:
        pending = []
        for f in sorted(ENTRIES.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            e = yaml.safe_load(f.read_text())
            if (e or {}).get("source_commit", "pending") in ("pending", None, ""):
                pending.append(f.name)
        if pending:
            print(f"{len(pending)} pending: {', '.join(pending[:10])}", file=sys.stderr)
            return 1
        return 0

    import os
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("Note: no GITHUB_TOKEN — rate-limited to 60/hour", file=sys.stderr)

    paths = sorted(ENTRIES.glob("*.yaml"))
    if args.slug:
        paths = [p for p in paths if args.slug in p.name]

    written = 0
    for path in paths:
        if path.name.startswith("_"):
            continue
        if pin_one(path, token, args.refresh):
            written += 1
            time.sleep(0.3)  # be polite to gh api

    print(f"\nPinned {written} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
