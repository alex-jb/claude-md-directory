"""
build-site.py — generates a single static HTML page rendering entries/*.yaml.

Output: site/index.html (no JS framework, just sortable HTML table + a bit of
inline CSS/JS). Suitable for GitHub Pages or any static host. Zero build deps
beyond pyyaml.

Usage:
    python scripts/build-site.py
    # → writes site/index.html

GitHub Pages setup (one-time, Alex side):
    Settings → Pages → Source: deploy from `main` branch, folder `/site`.
    URL becomes alex-jb.github.io/claude-md-directory
"""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path

import yaml  # type: ignore[import-not-found]

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "entries"
SITE = ROOT / "docs"  # GitHub Pages serves from /docs (only root or /docs allowed)


VERDICT_COLOR = {
    "helpful": ("#10B981", "#064E3B"),
    "neutral": ("#A1A1AA", "#27272A"),
    "harmful": ("#EF4444", "#7F1D1D"),
}


def load_entries() -> list[dict]:
    rows: list[dict] = []
    for f in sorted(ENTRIES.glob("*.yaml")):
        if f.name.startswith("_"):
            continue
        with open(f) as fp:
            entry = yaml.safe_load(fp)
        rows.append(entry)
    return rows


def tally(rows: list[dict]) -> dict[str, int]:
    counts = {"helpful": 0, "neutral": 0, "harmful": 0, "unaudited": 0}
    for r in rows:
        v = r.get("verdict")
        counts[v if v in counts else "unaudited"] += 1
    return counts


def row_html(r: dict) -> str:
    name = html.escape(r.get("name", r.get("slug", "?")))
    verdict = r.get("verdict", "unaudited")
    brier = r.get("brier_score")
    base = r.get("brier_baseline")
    delta = (base - brier) if (isinstance(brier, (int, float)) and isinstance(base, (int, float))) else None
    domain = html.escape(r.get("domain", ""))
    author = html.escape(r.get("author", ""))
    source_url = html.escape(r.get("source_url", "#"))
    bg, fg = VERDICT_COLOR.get(verdict, ("#3F3F46", "#18181B"))

    brier_cell = f"{brier:.3f}" if isinstance(brier, (int, float)) else "—"
    base_cell = f"{base:.3f}" if isinstance(base, (int, float)) else "—"
    delta_cell = ""
    if delta is not None:
        sign = "+" if delta >= 0 else ""
        delta_cell = f'<span style="color:{bg};font-weight:600">{sign}{delta:.3f}</span>'

    verdict_pill = (
        f'<span style="display:inline-block;padding:2px 10px;'
        f"border-radius:999px;background:{bg}22;color:{bg};font-weight:600;"
        f'font-size:12px;text-transform:uppercase;letter-spacing:1px">{verdict}</span>'
    )

    return f"""<tr data-verdict="{verdict}" data-brier="{brier or ''}">
  <td><a href="{source_url}" target="_blank" rel="noopener" style="color:#E8E8EC;text-decoration:none;font-weight:500">{name}</a></td>
  <td>{verdict_pill}</td>
  <td style="font-family:ui-monospace,SFMono-Regular,monospace;font-size:13px;text-align:right">{brier_cell}</td>
  <td style="font-family:ui-monospace,SFMono-Regular,monospace;font-size:13px;text-align:right;color:#71717A">{base_cell}</td>
  <td style="font-family:ui-monospace,SFMono-Regular,monospace;font-size:13px;text-align:right">{delta_cell}</td>
  <td style="color:#A1A1AA;font-size:13px">{domain}</td>
  <td style="color:#A1A1AA;font-size:13px">@{author}</td>
</tr>"""


def build_html(rows: list[dict]) -> str:
    counts = tally(rows)
    audited_total = counts["helpful"] + counts["neutral"] + counts["harmful"]
    today = dt.date.today().isoformat()

    table_rows = "\n".join(row_html(r) for r in rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>claude-md.directory — Brier-audited Claude.md and skills</title>
<meta name="description" content="Brier-audited directory of CLAUDE.md and skills/*.md files. {audited_total} entries audited so far ({counts['helpful']} helpful · {counts['neutral']} neutral · {counts['harmful']} harmful)." />
<meta property="og:title" content="claude-md.directory" />
<meta property="og:description" content="{audited_total} skills Brier-audited. {counts['helpful']} helpful · {counts['neutral']} neutral · {counts['harmful']} harmful." />
<style>
:root {{
  --bg-deep:#0A0A0C; --bg-elev:#161619; --text:#E8E8EC; --muted:#A1A1AA;
  --border:#3F3F46; --accent:#6366F1; --amber:#F59E0B;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg-deep); color:var(--text);
  font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
  line-height:1.5; padding:32px 24px;
}}
.wrap {{ max-width:1100px; margin:0 auto; }}
.kicker {{ font-family:ui-monospace,SFMono-Regular,monospace; font-size:10px; letter-spacing:0.4em; color:var(--muted); text-transform:uppercase; }}
h1 {{ margin:8px 0 16px; font-size:42px; line-height:1.1; letter-spacing:-0.5px; }}
h1 .accent {{ color:var(--accent); }}
.lead {{ color:var(--muted); max-width:680px; font-size:16px; }}
.stats {{ display:flex; gap:8px; flex-wrap:wrap; margin:24px 0 8px; }}
.stat {{ padding:8px 14px; border-radius:10px; border:1px solid var(--border); background:var(--bg-elev); font-size:14px; }}
.stat strong {{ font-size:20px; display:block; }}
.stat.helpful strong {{ color:#10B981; }}
.stat.neutral strong {{ color:#A1A1AA; }}
.stat.harmful strong {{ color:#EF4444; }}
.filters {{ display:flex; gap:8px; margin:16px 0; flex-wrap:wrap; align-items:center; }}
.filters button {{
  background:transparent; border:1px solid var(--border); color:var(--text);
  padding:6px 14px; border-radius:999px; font-family:inherit; font-size:13px;
  cursor:pointer; transition:.12s;
}}
.filters button.active {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
.filters button:hover {{ border-color:var(--accent); }}
.filters input[type=search] {{
  background:var(--bg-elev); border:1px solid var(--border); color:var(--text);
  padding:6px 12px; border-radius:8px; font-family:inherit; font-size:13px;
  width:200px;
}}
table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
th {{
  text-align:left; padding:10px 12px; border-bottom:1px solid var(--border);
  color:var(--muted); font-weight:500; font-size:11px; text-transform:uppercase;
  letter-spacing:1.5px; cursor:pointer; user-select:none;
}}
th:hover {{ color:var(--text); }}
th.right {{ text-align:right; }}
td {{ padding:14px 12px; border-bottom:1px solid #1C1C20; font-size:14px; vertical-align:middle; }}
tr:hover {{ background:var(--bg-elev); }}
.footer {{ margin-top:60px; padding:20px 0; border-top:1px solid var(--border); color:var(--muted); font-size:13px; line-height:1.7; }}
a {{ color:var(--accent); }}
.harmful-callout {{
  margin:24px 0; padding:16px 20px; background:rgba(239,68,68,0.08);
  border:1px solid rgba(239,68,68,0.3); border-radius:12px; font-size:14px;
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="kicker">claude-md.directory · v1.0 frozen eval</div>
  <h1>Which Claude skill <span class="accent">actually helps?</span></h1>
  <p class="lead">Third-party Brier-audited directory of <code>CLAUDE.md</code> and <code>skills/*.md</code> files. Every entry is scored against a frozen 5-task eval set on <code>claude-haiku-4-5</code>. Reproducible from <code>python scripts/audit.py entries/&lt;slug&gt;.yaml</code>.</p>

  <div class="stats">
    <div class="stat helpful"><strong>{counts['helpful']}</strong><span>helpful</span></div>
    <div class="stat neutral"><strong>{counts['neutral']}</strong><span>neutral</span></div>
    <div class="stat harmful"><strong>{counts['harmful']}</strong><span>harmful ⚠️</span></div>
    <div class="stat"><strong>{audited_total}</strong><span>audited</span></div>
  </div>

  {"<div class='harmful-callout'><strong>⚠️ 3 entries audit as harmful</strong> against no-skill baseline on the frozen v1.0 eval set — including 2 of Anthropic's own official skills (<code>algorithmic-art</code>, <code>doc-coauthoring</code>) and Sahil's <code>grow-sustainably</code>. Almost certainly domain mismatch (algorithmic-art is not built for code-review tasks). v1.1 widens to 40 tasks across 8 domains. Author counter-eval slot is open per <a href='https://github.com/alex-jb/claude-md-directory/blob/main/docs/brier-method.md'>docs/brier-method.md</a>.</div>" if counts['harmful'] > 0 else ""}

  <div class="filters">
    <button class="active" data-filter="all">All ({audited_total})</button>
    <button data-filter="helpful">✓ Helpful ({counts['helpful']})</button>
    <button data-filter="neutral">Neutral ({counts['neutral']})</button>
    <button data-filter="harmful">⚠️ Harmful ({counts['harmful']})</button>
    <input type="search" id="search" placeholder="Filter by name, author, domain..." />
  </div>

  <table id="tbl">
    <thead>
      <tr>
        <th data-sort="name">Skill</th>
        <th data-sort="verdict">Verdict</th>
        <th data-sort="brier" class="right">Brier</th>
        <th data-sort="brier" class="right">Baseline</th>
        <th data-sort="brier" class="right">Δ</th>
        <th data-sort="domain">Domain</th>
        <th data-sort="author">Author</th>
      </tr>
    </thead>
    <tbody>
{table_rows}
    </tbody>
  </table>

  <div class="footer">
    Method: <a href="https://github.com/alex-jb/claude-md-directory/blob/main/docs/brier-method.md">brier-method.md</a> · Source: <a href="https://github.com/alex-jb/claude-md-directory">github.com/alex-jb/claude-md-directory</a> · Submit a skill: <a href="https://github.com/alex-jb/claude-md-directory/blob/main/entries/_template.yaml">copy the template + open a PR</a>. CI auto-audits.<br/>
    Built {today} by <a href="https://github.com/alex-jb">@alex-jb</a>. Sister projects: <a href="https://whocalleditright.vercel.app">whocalleditright</a> · <a href="https://github.com/alex-jb/orallexa-ai-trading-agent">Orallexa</a> · <a href="https://github.com/alex-jb/memory-wall-tracker">memory-wall-tracker</a>.
  </div>
</div>

<script>
const buttons = document.querySelectorAll('[data-filter]');
const search = document.getElementById('search');
const rows = document.querySelectorAll('#tbl tbody tr');
let activeFilter = 'all';

function apply() {{
  const q = search.value.toLowerCase().trim();
  rows.forEach(r => {{
    const v = r.dataset.verdict;
    const text = r.textContent.toLowerCase();
    const verdictMatch = activeFilter === 'all' || v === activeFilter;
    const textMatch = !q || text.includes(q);
    r.style.display = (verdictMatch && textMatch) ? '' : 'none';
  }});
}}

buttons.forEach(b => b.addEventListener('click', () => {{
  buttons.forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  activeFilter = b.dataset.filter;
  apply();
}}));
search.addEventListener('input', apply);

// Click-to-sort
document.querySelectorAll('th[data-sort]').forEach((th, idx) => {{
  let asc = true;
  th.addEventListener('click', () => {{
    const tbody = document.querySelector('#tbl tbody');
    const sorted = Array.from(tbody.querySelectorAll('tr')).sort((a, b) => {{
      const va = a.cells[idx].textContent.trim();
      const vb = b.cells[idx].textContent.trim();
      const na = parseFloat(va);
      const nb = parseFloat(vb);
      if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
      return asc ? va.localeCompare(vb) : vb.localeCompare(va);
    }});
    sorted.forEach(r => tbody.appendChild(r));
    asc = !asc;
  }});
}});
</script>
</body>
</html>
"""


def main() -> int:
    rows = load_entries()
    SITE.mkdir(exist_ok=True)
    out = SITE / "index.html"
    out.write_text(build_html(rows), encoding="utf-8")
    print(f"✓ wrote {out} ({len(rows)} entries)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
