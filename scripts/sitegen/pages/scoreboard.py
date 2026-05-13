"""Quality scoreboard page."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..scoring import DIM_ABBREV, DIM_ORDER, compute_score
from ..util import safe, score_class, status_cell_class

TITLE = "Quality Scoreboard - AVM Intelligence Portal"


def _module_heatmap(modules: list[dict[str, Any]]) -> str:
    """Render module-by-dimension quality heatmap."""
    headers = "".join(
        f'<th title="{safe(dim)}">{safe(DIM_ABBREV[dim])}</th>' for dim in DIM_ORDER
    )
    ranked = sorted(
        modules,
        key=lambda module: compute_score(module.get("analysis", {}))[0],
        reverse=True,
    )
    rows = ""
    for module in ranked:
        score, statuses = compute_score(module.get("analysis", {}))
        has_data = any(value != "--" for value in statuses.values())
        cells = "".join(
            f'<td class="{status_cell_class(statuses.get(dim, "--"))}" title="{safe(dim)}: {safe(statuses.get(dim, "--"))}">{safe(statuses.get(dim, "--"))}</td>'
            for dim in DIM_ORDER
        )
        rows += (
            f"<tr><td class=\"module-name name\">{safe(module['name'])}</td>"
            f"<td><span class=\"score {score_class(score, has_data)}\">"
            f"{score:.0f}%</span></td>{cells}</tr>\n"
        )
    return f"""
<div class="table-wrap">
  <table class="heatmap">
    <thead><tr><th style="text-align:left">Module</th><th>Score</th>{headers}</tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""


def _domain_heatmap(modules: list[dict[str, Any]]) -> str:
    """Render domain-by-dimension aggregate heatmap."""
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for module in modules:
        by_domain[module.get("domain") or "unknown"].append(module)
    headers = "".join(
        f'<th title="{safe(dim)}">{safe(DIM_ABBREV[dim])}</th>' for dim in DIM_ORDER
    )
    rows = ""
    for domain in sorted(by_domain):
        domain_modules = by_domain[domain]
        scores = [
            compute_score(module["analysis"])[0]
            for module in domain_modules
            if module.get("analysis")
        ]
        avg = sum(scores) / len(scores) if scores else 0.0
        cells = ""
        for dim in DIM_ORDER:
            counts = {"pass": 0, "partial": 0, "fail": 0}
            total = 0
            for module in domain_modules:
                data = module.get("analysis", {}).get(dim)
                if not data:
                    continue
                total += 1
                status = data.get("status", "")
                if status == "pass":
                    counts["pass"] += 1
                elif status in ("partial", "unchecked", "skip"):
                    counts["partial"] += 1
                elif status in ("fail", "failed", "missing"):
                    counts["fail"] += 1
            if total == 0:
                cells += '<td class="hm-grey">--</td>'
            elif counts["fail"] > 0:
                cells += f'<td class="hm-red" title="{counts["fail"]} fail; {counts["partial"]} partial; {counts["pass"]} pass">{counts["pass"]}/{total}</td>'
            elif counts["partial"] > 0:
                cells += f'<td class="hm-orange" title="{counts["partial"]} partial; {counts["pass"]} pass">{counts["pass"]}/{total}</td>'
            else:
                cells += f'<td class="hm-green" title="all pass">{counts["pass"]}/{total}</td>'
        rows += (
            f'<tr><td class="dom-name">{safe(domain)} '
            f'<span class="score {score_class(avg, bool(scores))}">{avg:.0f}%</span>'
            f"</td>{cells}</tr>\n"
        )
    return f"""
<details open>
  <summary>Domain x Dimension Heatmap<span class="domain-stats"><span>pass count / analyzed</span></span></summary>
  <div class="table-wrap">
    <table class="heatmap">
      <thead><tr><th style="text-align:left">Domain</th>{headers}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</details>
"""


def _owner_map(modules: list[dict[str, Any]]) -> str:
    """Render the primary owner map."""
    by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for module in modules:
        handle = (
            module.get("owners", {})
            .get("primary", {})
            .get("handle", "")
            .strip()
            or "unassigned"
        )
        by_owner[handle].append(module)
    rows = ""
    for handle in sorted(by_owner, key=lambda owner: (-len(by_owner[owner]), owner)):
        owner_modules = by_owner[handle]
        primary_name = next(
            (
                module.get("owners", {}).get("primary", {}).get("name", "")
                for module in owner_modules
                if module.get("owners", {}).get("primary", {}).get("name", "")
            ),
            "",
        )
        no_secondary = sum(
            1
            for module in owner_modules
            if not module.get("owners", {}).get("secondary", {}).get("handle", "").strip()
        )
        chips = "".join(
            f'<span class="mod-chip">{safe(module["name"])}</span>'
            for module in sorted(owner_modules, key=lambda item: item["name"])
        )
        handle_html = (
            f'<a href="https://github.com/{safe(handle)}" target="_blank" rel="noopener">{safe(handle)}</a>'
            if handle != "unassigned"
            else '<span class="muted">unassigned</span>'
        )
        rows += (
            f'<tr><td><span class="owner-handle">{handle_html}</span><br>'
            f'<span class="owner-name">{safe(primary_name)}</span></td>'
            f"<td>{len(owner_modules)}</td>"
            f'<td><span class="{"no-secondary" if no_secondary else "muted"}">{no_secondary or "--"}</span></td>'
            f"<td>{chips}</td></tr>\n"
        )
    return f"""
<details>
  <summary>Owner Map<span class="domain-stats"><span>{len(modules)} modules · {len(by_owner)} owners</span></span></summary>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Owner</th><th>Modules</th><th>No 2nd owner</th><th>Module list</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</details>
"""


def render(modules: list[dict[str, Any]], **_: Any) -> tuple[str, str, str]:
    """Render the Quality Scoreboard page."""
    scores = [compute_score(module["analysis"])[0] for module in modules if module.get("analysis")]
    avg = sum(scores) / len(scores) if scores else 0.0
    low = sum(1 for score in scores if score < 60)
    partial = sum(1 for score in scores if 60 <= score < 80)
    high = sum(1 for score in scores if score >= 80)
    body = f"""
<h1>Quality Scoreboard</h1>
<p class="subtitle">Weighted quality ranking across the seven AVM analysis dimensions.</p>
<div class="stats">
  <div class="stat-card"><div class="val score {score_class(avg, bool(scores))}">{avg:.0f}%</div><div class="lbl">Average score</div></div>
  <div class="stat-card"><div class="val score score-green">{high}</div><div class="lbl">80%+</div></div>
  <div class="stat-card"><div class="val score score-orange">{partial}</div><div class="lbl">60-79%</div></div>
  <div class="stat-card"><div class="val score score-red">{low}</div><div class="lbl">Below 60%</div></div>
</div>
{_domain_heatmap(modules)}
<section class="panel">
  <h2>Module Leaderboard</h2>
  {_module_heatmap(modules)}
</section>
{_owner_map(modules)}
"""
    return body, "", ""

