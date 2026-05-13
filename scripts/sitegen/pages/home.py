"""Home page for the AVM Intelligence Portal."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..scoring import DIM_ORDER, compute_score
from ..util import json_script, safe, score_class

TITLE = "AVM Intelligence Portal"


def _module_stats(modules: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute high-level portal statistics."""
    by_domain = Counter(m.get("domain") or "unknown" for m in modules)
    by_type = Counter(m.get("type") or "unknown" for m in modules)
    scores = [compute_score(m["analysis"])[0] for m in modules if m.get("analysis")]
    no_secondary = sum(
        1
        for module in modules
        if not module.get("owners", {}).get("secondary", {}).get("handle", "").strip()
    )
    low_scores = sum(1 for score in scores if score < 60)
    return {
        "total": len(modules),
        "domains": len(by_domain),
        "by_type": by_type,
        "avg_score": (sum(scores) / len(scores)) if scores else 0.0,
        "analyzed": len(scores),
        "no_secondary": no_secondary,
        "low_scores": low_scores,
    }


def _domain_health_data(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate average score and count by domain."""
    grouped: dict[str, list[float]] = defaultdict(list)
    counts: Counter[str] = Counter()
    for module in modules:
        domain = module.get("domain") or "unknown"
        counts[domain] += 1
        if module.get("analysis"):
            grouped[domain].append(compute_score(module["analysis"])[0])
    rows = []
    for domain, count in counts.items():
        scores = grouped.get(domain, [])
        rows.append(
            {
                "domain": domain,
                "count": count,
                "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            }
        )
    return sorted(rows, key=lambda row: (row["avg_score"], row["domain"]))


def _score_distribution(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return score-band counts for a histogram."""
    bands = {
        "0-39": 0,
        "40-59": 0,
        "60-79": 0,
        "80-100": 0,
        "No data": 0,
    }
    for module in modules:
        if not module.get("analysis"):
            bands["No data"] += 1
            continue
        score = compute_score(module["analysis"])[0]
        if score < 40:
            bands["0-39"] += 1
        elif score < 60:
            bands["40-59"] += 1
        elif score < 80:
            bands["60-79"] += 1
        else:
            bands["80-100"] += 1
    return [{"band": key, "count": value} for key, value in bands.items()]


def _dimension_gaps(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return dimensions with the most non-pass statuses."""
    gaps = []
    for dim in DIM_ORDER:
        total = 0
        passing = 0
        for module in modules:
            data = module.get("analysis", {}).get(dim)
            if not data:
                continue
            total += 1
            if data.get("status") == "pass":
                passing += 1
        gaps.append(
            {
                "dimension": dim,
                "pass": passing,
                "gap": max(total - passing, 0),
                "total": total,
            }
        )
    return gaps


def render(modules: list[dict[str, Any]], **_: Any) -> tuple[str, str, str]:
    """Render the Home page."""
    stats = _module_stats(modules)
    avg_cls = score_class(stats["avg_score"], stats["analyzed"] > 0)
    type_counts = stats["by_type"]
    domain_data = _domain_health_data(modules)
    score_data = _score_distribution(modules)
    dimension_data = _dimension_gaps(modules)

    stat_cards = f"""
<div class="stats">
  <div class="stat-card"><div class="val">{stats["total"]}</div><div class="lbl">Modules</div></div>
  <div class="stat-card"><div class="val">{stats["domains"]}</div><div class="lbl">Domains</div></div>
  <div class="stat-card"><div class="val">{type_counts.get("res", 0)}</div><div class="lbl">res</div></div>
  <div class="stat-card"><div class="val">{type_counts.get("ptn", 0)}</div><div class="lbl">ptn</div></div>
  <div class="stat-card"><div class="val">{type_counts.get("utl", 0)}</div><div class="lbl">utl</div></div>
  <div class="stat-card"><div class="val">{stats["analyzed"]}</div><div class="lbl">Analyzed</div></div>
  <div class="stat-card"><div class="val score {avg_cls}">{stats["avg_score"]:.0f}%</div><div class="lbl">Avg score</div></div>
  <div class="stat-card"><div class="val score score-orange">{stats["no_secondary"]}</div><div class="lbl">No 2nd owner</div></div>
</div>
"""

    domain_rows = "".join(
        f"<tr><td>{safe(row['domain'])}</td><td>{row['count']}</td>"
        f"<td><span class=\"score {score_class(row['avg_score'], True)}\">"
        f"{row['avg_score']:.0f}%</span></td></tr>"
        for row in domain_data
    )
    dimension_rows = "".join(
        f"<tr><td>{safe(row['dimension'])}</td><td>{row['pass']}/{row['total']}</td>"
        f"<td>{row['gap']}</td></tr>"
        for row in dimension_data
    )

    body = f"""
<h1>AVM Intelligence Portal</h1>
<p class="subtitle">Catalog health, quality coverage, provider currency, known issues, and activity for Azure Verified Modules.</p>
{stat_cards}
<div class="chart-grid">
  <section class="chart-card">
    <h2>Domain Health Overview</h2>
    <div id="domain-health-chart" aria-label="Average score by domain"></div>
    <noscript><div class="table-wrap"><table><tbody>{domain_rows}</tbody></table></div></noscript>
  </section>
  <section class="chart-card">
    <h2>Score Distribution</h2>
    <div id="score-distribution-chart" aria-label="Score distribution"></div>
  </section>
</div>
<section class="panel">
  <h2>Dimension Gaps</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Dimension</th><th>Pass</th><th>Gap</th></tr></thead>
      <tbody>{dimension_rows}</tbody>
    </table>
  </div>
</section>
<div class="quick-grid">
  <a class="quick-card" href="scoreboard.html"><strong>{stats["low_scores"]} modules below 60%</strong><div class="label">Open Quality Scoreboard</div></a>
  <a class="quick-card" href="catalog.html"><strong>{stats["total"]} modules searchable</strong><div class="label">Open Module Catalog</div></a>
  <a class="quick-card" href="issues.html"><strong>Known issue rollup</strong><div class="label">Open Issues board</div></a>
  <a class="quick-card" href="provider.html"><strong>Provider currency</strong><div class="label">Open findings view</div></a>
</div>
{json_script("domain-health-data", domain_data)}
{json_script("score-distribution-data", score_data)}
"""
    extra_head = """
  <script type="module">
    import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.17/+esm";
    const domainData = JSON.parse(document.getElementById("domain-health-data").textContent);
    const scoreData = JSON.parse(document.getElementById("score-distribution-data").textContent);
    const domainTarget = document.getElementById("domain-health-chart");
    const scoreTarget = document.getElementById("score-distribution-chart");
    if (domainTarget) {
      domainTarget.append(Plot.plot({
        height: 320,
        marginLeft: 130,
        x: { grid: true, label: "Average score" },
        y: { label: null },
        marks: [
          Plot.barX(domainData, { x: "avg_score", y: "domain", sort: { y: "x" }, fill: "#58a6ff" }),
          Plot.text(domainData, { x: "avg_score", y: "domain", text: d => `${Math.round(d.avg_score)}%`, dx: 18, fill: "#e6edf3" })
        ]
      }));
    }
    if (scoreTarget) {
      scoreTarget.append(Plot.plot({
        height: 320,
        x: { label: "Score band" },
        y: { grid: true, label: "Modules" },
        marks: [Plot.barY(scoreData, { x: "band", y: "count", fill: "#3fb950" })]
      }));
    }
  </script>
"""
    return body, extra_head, ""

