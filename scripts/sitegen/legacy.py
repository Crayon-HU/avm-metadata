"""Legacy single-file dashboard renderer for --output compatibility."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .css import SITE_CSS
from .scoring import DIM_ABBREV, DIM_ORDER, compute_score, staleness_days
from .util import safe, score_class, stale_badge, status_badge, type_badge


def _module_row(module: dict[str, Any]) -> str:
    score, dim_statuses = compute_score(module["analysis"])
    has_data = any(value != "--" for value in dim_statuses.values())
    repo_url = module.get("repo_url", "")
    name_html = (
        f'<a href="{safe(repo_url)}" target="_blank" rel="noopener">{safe(module["name"])}</a>'
        if repo_url
        else safe(module["name"])
    )
    badges = "".join(status_badge(dim_statuses.get(dim, "--")) for dim in DIM_ORDER)
    return (
        "<tr>"
        f'<td class="name">{name_html}{stale_badge(staleness_days(module["analysis"]))}</td>'
        f"<td>{type_badge(module.get('type', ''))}</td>"
        f'<td><span class="score {score_class(score, has_data)}">'
        f'{score:.0f}%' if has_data else "--"
    ) + (
        "</span></td>"
        f"<td>{badges}</td>"
        f'<td class="version">{safe(module.get("version_pinned") or "--")}</td>'
        f'<td class="version">{safe(module.get("last_synced") or "--")}</td>'
        "</tr>\n"
    )


def _domain_section(domain: str, modules: list[dict[str, Any]]) -> str:
    rows = "".join(_module_row(module) for module in modules)
    scores = [compute_score(module["analysis"])[0] for module in modules if module.get("analysis")]
    avg = sum(scores) / len(scores) if scores else 0.0
    return f"""
<details open>
  <summary>{safe(domain.title())}<span class="domain-stats"><span>{len(modules)} modules</span><span class="score {score_class(avg, bool(scores))}">avg {avg:.0f}%</span></span></summary>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Module</th><th>Type</th><th>Score</th><th>Dimensions</th><th>Version</th><th>Synced</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</details>
"""


def _domain_heatmap(by_domain: dict[str, list[dict[str, Any]]]) -> str:
    headers = "".join(
        f'<th title="{safe(dim)}">{safe(DIM_ABBREV[dim])}</th>' for dim in DIM_ORDER
    )
    rows = ""
    for domain, modules in sorted(by_domain.items()):
        cells = ""
        for dim in DIM_ORDER:
            total = 0
            passing = 0
            partial = 0
            failing = 0
            for module in modules:
                data = module.get("analysis", {}).get(dim)
                if not data:
                    continue
                total += 1
                status = data.get("status", "")
                if status == "pass":
                    passing += 1
                elif status in ("partial", "unchecked", "skip"):
                    partial += 1
                elif status in ("fail", "failed", "missing"):
                    failing += 1
            if total == 0:
                cells += '<td class="hm-grey">--</td>'
            elif failing:
                cells += f'<td class="hm-red">{passing}/{total}</td>'
            elif partial:
                cells += f'<td class="hm-orange">{passing}/{total}</td>'
            else:
                cells += f'<td class="hm-green">{passing}/{total}</td>'
        rows += f'<tr><td class="dom-name">{safe(domain.title())}</td>{cells}</tr>\n'
    return f"""
<details open>
  <summary>Domain x Dimension Heatmap</summary>
  <div class="table-wrap">
    <table class="heatmap"><thead><tr><th>Domain</th>{headers}</tr></thead><tbody>{rows}</tbody></table>
  </div>
</details>
"""


def render_legacy(modules: list[dict[str, Any]]) -> str:
    """Render a single-file dashboard for existing --output workflows."""
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_type: dict[str, int] = defaultdict(int)
    for module in modules:
        by_domain[module.get("domain") or "unknown"].append(module)
        by_type[module.get("type") or "unknown"] += 1
    scores = [compute_score(module["analysis"])[0] for module in modules if module.get("analysis")]
    avg = sum(scores) / len(scores) if scores else 0.0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sections = "".join(_domain_section(domain, items) for domain, items in sorted(by_domain.items()))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AVM Intelligence Dashboard</title>
  <style>{SITE_CSS}</style>
</head>
<body>
  <main class="page">
    <h1>AVM Intelligence Dashboard</h1>
    <p class="subtitle">Generated: {safe(now)} · legacy single-file output</p>
    <div class="stats">
      <div class="stat-card"><div class="val">{len(modules)}</div><div class="lbl">Modules</div></div>
      <div class="stat-card"><div class="val">{len(by_domain)}</div><div class="lbl">Domains</div></div>
      <div class="stat-card"><div class="val">{by_type.get("res", 0)}</div><div class="lbl">res</div></div>
      <div class="stat-card"><div class="val">{by_type.get("ptn", 0)}</div><div class="lbl">ptn</div></div>
      <div class="stat-card"><div class="val">{by_type.get("utl", 0)}</div><div class="lbl">utl</div></div>
      <div class="stat-card"><div class="val score {score_class(avg, bool(scores))}">{avg:.0f}%</div><div class="lbl">Avg score</div></div>
    </div>
    {_domain_heatmap(by_domain)}
    {sections}
    <footer class="footer">Auto-generated by <code>scripts/generate_site.py</code> · Crayon-HU/avm-metadata</footer>
  </main>
</body>
</html>
"""

