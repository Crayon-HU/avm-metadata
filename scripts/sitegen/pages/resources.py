"""Resource explorer page."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..data import module_resource_symbols
from ..scoring import compute_score
from ..util import json_script, safe, score_class

TITLE = "Resource Explorer - AVM Intelligence Portal"


def _resource_usage(
    modules: list[dict[str, Any]], resources: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Aggregate Terraform resource usage across modules."""
    resource_meta = {resource["type"]: resource for resource in resources}
    counts: Counter[str] = Counter()
    module_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for module in modules:
        for symbol in module_resource_symbols(module):
            counts[symbol] += 1
            module_refs[symbol].append(module)

    rows: list[dict[str, Any]] = []
    for symbol, count in counts.items():
        linked_modules = module_refs[symbol]
        scores = [
            compute_score(module["analysis"])[0]
            for module in linked_modules
            if module.get("analysis")
        ]
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        meta = resource_meta.get(symbol, {})
        provider = meta.get("provider") or symbol.split("_", 1)[0]
        rows.append(
            {
                "symbol": symbol,
                "provider": provider,
                "count": count,
                "avg_score": avg,
                "modules": [module["name"] for module in linked_modules],
            }
        )
    return sorted(rows, key=lambda row: (-row["count"], row["symbol"]))


def render(
    modules: list[dict[str, Any]],
    *,
    resources: list[dict[str, Any]] | None = None,
    **_: Any,
) -> tuple[str, str, str]:
    """Render the Resource Explorer page."""
    data = _resource_usage(modules, resources or [])
    tiles = ""
    max_count = max((row["count"] for row in data), default=1)
    for row in data[:60]:
        width = max(1, int((row["count"] / max_count) * 100))
        cls = score_class(row["avg_score"], True)
        tiles += f"""
<button class="resource-tile" type="button" data-symbol="{safe(row["symbol"])}" data-modules="{safe("|".join(row["modules"]))}">
  <strong>{safe(row["symbol"])}</strong>
  <div class="label">{safe(row["provider"])} · {row["count"]} modules · <span class="score {cls}">{row["avg_score"]:.0f}% avg</span></div>
  <div style="height:4px;background:var(--bg3);margin-top:8px;border-radius:4px"><div style="height:4px;width:{width}%;background:var(--blue);border-radius:4px"></div></div>
</button>
"""
    rows = "".join(
        f"<tr><td class=\"name\">{safe(row['symbol'])}</td><td>{safe(row['provider'])}</td><td>{row['count']}</td><td><span class=\"score {score_class(row['avg_score'], True)}\">{row['avg_score']:.0f}%</span></td></tr>"
        for row in data
    )
    body = f"""
<h1>Resource Explorer</h1>
<p class="subtitle">Terraform resource and datasource usage across AVM modules. Select a tile to list referencing modules.</p>
<div class="chart-card">
  <h2>Top Resource Usage</h2>
  <div id="resource-usage-chart" aria-label="Resource usage chart"></div>
</div>
<div class="tile-grid">{tiles}</div>
<section class="panel">
  <h2>Selected resource modules</h2>
  <div id="resource-detail" class="muted">Select a resource tile to show module references.</div>
</section>
<div class="table-wrap">
  <table>
    <thead><tr><th>Symbol</th><th>Provider</th><th>Modules</th><th>Avg score</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
{json_script("resource-usage-data", data[:30])}
"""
    extra_head = """
  <script type="module">
    import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.17/+esm";
    const data = JSON.parse(document.getElementById("resource-usage-data").textContent);
    const target = document.getElementById("resource-usage-chart");
    if (target) {
      target.append(Plot.plot({
        height: 420,
        marginLeft: 210,
        x: { grid: true, label: "Modules" },
        y: { label: null },
        marks: [
          Plot.barX(data, { x: "count", y: "symbol", sort: { y: "-x" }, fill: "#58a6ff" })
        ]
      }));
    }
  </script>
"""
    extra_body = """
<script>
  (() => {
    const detail = document.getElementById("resource-detail");
    document.querySelectorAll(".resource-tile").forEach(tile => {
      tile.addEventListener("click", () => {
        const modules = (tile.dataset.modules || "").split("|").filter(Boolean);
        detail.textContent = "";
        modules.forEach(name => {
          const chip = document.createElement("span");
          chip.className = "mod-chip";
          chip.textContent = name;
          detail.append(chip, " ");
        });
      });
    });
  })();
</script>
"""
    return body, extra_head, extra_body
