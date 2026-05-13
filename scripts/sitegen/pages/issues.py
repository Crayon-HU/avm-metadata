"""Known issues page."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..util import safe, severity_badge, type_badge

TITLE = "Known Issues - AVM Intelligence Portal"
SEVERITIES = ("critical", "high", "medium", "low", "unknown")


def render(
    modules: list[dict[str, Any]],
    *,
    module_issues: list[dict[str, Any]] | None = None,
    **_: Any,
) -> tuple[str, str, str]:
    """Render known issues as a severity kanban board."""
    issues = module_issues or []
    domains = sorted({issue.get("domain", "") for issue in issues if issue.get("domain")})
    domain_opts = "".join(f'<option value="{safe(domain)}">{safe(domain)}</option>' for domain in domains)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for issue in issues:
        severity = str(issue.get("severity") or "unknown").lower()
        if severity not in SEVERITIES:
            severity = "unknown"
        grouped[severity].append(issue)

    columns = ""
    for severity in SEVERITIES:
        items = grouped.get(severity, [])
        if not items and severity == "unknown":
            continue
        cards = ""
        for issue in sorted(items, key=lambda item: (item.get("domain", ""), item.get("module", ""))):
            title = issue.get("title") or f"Issue #{issue.get('number', '')}"
            url = issue.get("url", "")
            title_html = (
                f'<a href="{safe(url)}" target="_blank" rel="noopener">{safe(title)}</a>'
                if url
                else safe(title)
            )
            workaround = issue.get("workaround", "")
            cards += f"""
<details class="kanban-card" data-domain="{safe(issue.get("domain", ""))}">
  <summary>{title_html}</summary>
  <div class="detail-row"><div class="detail-key">Module</div><div class="name">{safe(issue.get("module", ""))}</div></div>
  <div class="detail-row"><div class="detail-key">Domain</div><div>{safe(issue.get("domain", ""))} {type_badge(issue.get("type", ""))}</div></div>
  <div class="detail-row"><div class="detail-key">Source</div><div>{safe(issue.get("source", ""))}</div></div>
  <div class="detail-row"><div class="detail-key">Status</div><div>{safe(issue.get("status", "open"))}</div></div>
  <div class="detail-row"><div class="detail-key">Workaround</div><div>{safe(workaround) if workaround else '<span class="muted">--</span>'}</div></div>
</details>
"""
        columns += f"""
<section class="kanban-column">
  <h2>{severity_badge(severity)} {safe(severity.title())} <span class="muted">({len(items)})</span></h2>
  {cards or '<div class="muted">No issues.</div>'}
</section>
"""

    if not issues:
        columns = '<div class="empty-state">No harvested module issues or enrichment known issues found.</div>'

    body = f"""
<h1>Known Issues</h1>
<p class="subtitle">Aggregated from <code>enrichment.known_issues</code> and harvested <code>module_issues</code>.</p>
<div class="filter-bar">
  <label>Domain<select id="issue-domain-filter"><option value="">All domains</option>{domain_opts}</select></label>
</div>
<div class="kanban">{columns}</div>
"""
    extra_body = """
<script>
  (() => {
    const filter = document.getElementById("issue-domain-filter");
    if (!filter) return;
    filter.addEventListener("input", () => {
      const domain = filter.value;
      document.querySelectorAll(".kanban-card").forEach(card => {
        card.style.display = (!domain || card.dataset.domain === domain) ? "" : "none";
      });
    });
  })();
</script>
"""
    return body, "", extra_body

