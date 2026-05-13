"""Module catalog page."""

from __future__ import annotations

from typing import Any

from ..scoring import DIM_ORDER, compute_score, staleness_days
from ..util import safe, score_class, stale_badge, status_badge, type_badge

TITLE = "Module Catalog - AVM Intelligence Portal"


def _row(module: dict[str, Any]) -> str:
    score, dim_statuses = compute_score(module["analysis"])
    has_data = any(value != "--" for value in dim_statuses.values())
    score_text = f"{score:.0f}%" if has_data else "--"
    cls = score_class(score, has_data)
    repo_url = module.get("repo_url", "")
    name = module["name"]
    name_html = (
        f'<a href="{safe(repo_url)}" target="_blank" rel="noopener">{safe(name)}</a>'
        if repo_url
        else safe(name)
    )
    badges = "".join(status_badge(dim_statuses.get(dim, "--")) for dim in DIM_ORDER)
    version = safe(module.get("version_pinned") or "--")
    synced = safe(module.get("last_synced") or "--")
    return f"""
<tr data-domain="{safe(module.get("domain"))}" data-type="{safe(module.get("type"))}" data-status="{safe(module.get("status"))}" data-score="{score:.1f}" data-name="{safe(name.lower())}">
  <td class="name">{name_html}{stale_badge(staleness_days(module["analysis"]))}</td>
  <td>{type_badge(module.get("type", ""))}</td>
  <td>{safe(module.get("domain", ""))}</td>
  <td>{safe(module.get("status", ""))}</td>
  <td><span class="score {cls}">{score_text}</span></td>
  <td>{badges}</td>
  <td class="version">{version}</td>
  <td class="version">{synced}</td>
</tr>
"""


def render(modules: list[dict[str, Any]], **_: Any) -> tuple[str, str, str]:
    """Render the Catalog page."""
    domains = sorted({m.get("domain") or "unknown" for m in modules})
    types = sorted({m.get("type") or "unknown" for m in modules})
    statuses = sorted({m.get("status") or "unknown" for m in modules})
    rows = "".join(_row(module) for module in modules)
    domain_opts = "".join(f'<option value="{safe(d)}">{safe(d)}</option>' for d in domains)
    type_opts = "".join(f'<option value="{safe(t)}">{safe(t)}</option>' for t in types)
    status_opts = "".join(f'<option value="{safe(s)}">{safe(s)}</option>' for s in statuses)

    body = f"""
<h1>Module Catalog</h1>
<p class="subtitle"><span id="catalog-count">{len(modules)}</span> modules found. Filter by text, domain, type, or status; click Score to sort.</p>
<div class="filter-bar" role="search">
  <label>Search<input id="catalog-search" type="search" placeholder="module name or description"></label>
  <label>Domain<select id="domain-filter"><option value="">All domains</option>{domain_opts}</select></label>
  <label>Type<select id="type-filter"><option value="">All types</option>{type_opts}</select></label>
  <label>Status<select id="status-filter"><option value="">All statuses</option>{status_opts}</select></label>
  <button id="clear-filters" type="button">Clear</button>
</div>
<div class="table-wrap">
  <table id="catalog-table">
    <thead>
      <tr>
        <th>Module</th><th>Type</th><th>Domain</th><th>Status</th>
        <th><button type="button" id="sort-score">Score</button></th>
        <th>Dimensions</th><th>Version</th><th>Synced</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""
    extra_body = """
<script>
  (() => {
    const rows = Array.from(document.querySelectorAll("#catalog-table tbody tr"));
    const search = document.getElementById("catalog-search");
    const domain = document.getElementById("domain-filter");
    const type = document.getElementById("type-filter");
    const status = document.getElementById("status-filter");
    const count = document.getElementById("catalog-count");
    const clear = document.getElementById("clear-filters");
    const tbody = document.querySelector("#catalog-table tbody");
    let ascending = false;

    function applyFilters() {
      const q = (search.value || "").toLowerCase();
      let visible = 0;
      rows.forEach(row => {
        const ok = (!q || row.dataset.name.includes(q))
          && (!domain.value || row.dataset.domain === domain.value)
          && (!type.value || row.dataset.type === type.value)
          && (!status.value || row.dataset.status === status.value);
        row.style.display = ok ? "" : "none";
        if (ok) visible += 1;
      });
      count.textContent = visible;
    }
    [search, domain, type, status].forEach(el => el.addEventListener("input", applyFilters));
    clear.addEventListener("click", () => {
      search.value = "";
      domain.value = "";
      type.value = "";
      status.value = "";
      applyFilters();
    });
    document.getElementById("sort-score").addEventListener("click", () => {
      ascending = !ascending;
      rows.sort((a, b) => {
        const left = Number(a.dataset.score);
        const right = Number(b.dataset.score);
        return ascending ? left - right : right - left;
      }).forEach(row => tbody.append(row));
    });
  })();
</script>
"""
    return body, "", extra_body

