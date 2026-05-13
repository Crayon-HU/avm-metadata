"""Activity feed page."""

from __future__ import annotations

from typing import Any

from ..util import json_script, safe

TITLE = "Activity Feed - AVM Intelligence Portal"


def render(
    modules: list[dict[str, Any]],
    *,
    activity: dict[str, Any] | None = None,
    **_: Any,
) -> tuple[str, str, str]:
    """Render commit activity data if pre-computed JSON exists."""
    del modules
    if not activity:
        body = """
<h1>Activity Feed</h1>
<p class="subtitle">Commit heatmap for cloned module repositories.</p>
<div class="empty-state">
  No <code>data/activity.json</code> file found. Generate it locally with
  <code>./avm.sh activity --since 90d --json data/activity.json</code> after cloning modules.
</div>
"""
        return body, "", ""

    rows_data = activity.get("modules", [])
    since = activity.get("since", "")
    generated = activity.get("generated_at", "")
    rows = "".join(
        f"<tr><td class=\"name\">{safe(row.get('name', ''))}</td><td>{safe(row.get('domain', ''))}</td><td>{row.get('commits', 0)}</td><td>{safe(row.get('last_commit', '') or '--')}</td></tr>"
        for row in sorted(rows_data, key=lambda item: (-int(item.get("commits", 0)), item.get("name", "")))
    )
    body = f"""
<h1>Activity Feed</h1>
<p class="subtitle">Recent git activity since {safe(since)}. Data generated: {safe(generated or '--')}.</p>
<div class="chart-card">
  <h2>Commits by module</h2>
  <div id="activity-chart"></div>
</div>
<div class="table-wrap">
  <table>
    <thead><tr><th>Module</th><th>Domain</th><th>Commits</th><th>Last commit</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
{json_script("activity-data", rows_data[:80])}
"""
    extra_head = """
  <script type="module">
    import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.17/+esm";
    const data = JSON.parse(document.getElementById("activity-data").textContent);
    const target = document.getElementById("activity-chart");
    if (target) {
      target.append(Plot.plot({
        height: 520,
        marginLeft: 260,
        x: { grid: true, label: "Commits" },
        y: { label: null },
        marks: [Plot.barX(data, { x: "commits", y: "name", sort: { y: "-x" }, fill: "#3fb950" })]
      }));
    }
  </script>
"""
    return body, extra_head, ""

