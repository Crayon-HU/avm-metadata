"""Provider currency page."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..data import module_resource_symbols
from ..util import safe, severity_badge

TITLE = "Provider Currency - AVM Intelligence Portal"
SEVERITY_ORDER = ("critical", "high", "medium", "low", "unknown")


def _symbol_modules(modules: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build a Terraform symbol -> modules lookup."""
    lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for module in modules:
        for symbol in module_resource_symbols(module):
            lookup[symbol].append(module)
    return lookup


def render(
    modules: list[dict[str, Any]],
    *,
    resources: list[dict[str, Any]] | None = None,
    **_: Any,
) -> tuple[str, str, str]:
    """Render provider release and issue findings."""
    resources = resources or []
    by_symbol = _symbol_modules(modules)
    findings: list[dict[str, Any]] = []
    for resource in resources:
        linked_modules = by_symbol.get(resource["type"], [])
        for finding in resource.get("findings", []):
            severity = str(finding.get("criticality") or "unknown").lower()
            findings.append(
                {
                    "resource": resource,
                    "finding": finding,
                    "severity": severity,
                    "modules": linked_modules,
                }
            )
        for issue in resource.get("issues", []):
            labels = issue.get("labels", [])
            label_text = ",".join(labels) if isinstance(labels, list) else str(labels)
            findings.append(
                {
                    "resource": resource,
                    "finding": {
                        "version": "provider issue",
                        "type": label_text or "issue",
                        "summary": issue.get("title", ""),
                        "url": issue.get("url", ""),
                    },
                    "severity": "medium",
                    "modules": linked_modules,
                }
            )

    counts = Counter(item["severity"] for item in findings)
    stat_cards = "".join(
        f'<div class="stat-card"><div class="val">{counts.get(sev, 0)}</div>'
        f'<div class="lbl">{safe(sev.title())}</div></div>'
        for sev in SEVERITY_ORDER[:4]
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in findings:
        grouped[item["severity"]].append(item)

    sections = ""
    for severity in SEVERITY_ORDER:
        items = grouped.get(severity, [])
        if not items:
            continue
        rows = ""
        for item in sorted(
            items,
            key=lambda value: (
                value["resource"].get("provider", ""),
                value["resource"].get("type", ""),
                value["finding"].get("summary", ""),
            ),
        ):
            resource = item["resource"]
            finding = item["finding"]
            module_links = "".join(
                f'<span class="mod-chip">{safe(module["name"])}</span>'
                for module in item["modules"][:12]
            )
            if len(item["modules"]) > 12:
                module_links += f'<span class="muted">+{len(item["modules"]) - 12} more</span>'
            url = finding.get("url", "")
            summary = safe(finding.get("summary", ""))
            summary_html = (
                f'<a href="{safe(url)}" target="_blank" rel="noopener">{summary}</a>'
                if url
                else summary
            )
            rows += f"""
<details>
  <summary>{severity_badge(severity)} {safe(resource["type"])} <span class="domain-stats"><span>{len(item["modules"])} modules</span></span></summary>
  <div class="panel">
    <div class="detail-row"><div class="detail-key">Provider</div><div>{safe(resource.get("provider", ""))}</div></div>
    <div class="detail-row"><div class="detail-key">Version</div><div>{safe(finding.get("version", ""))}</div></div>
    <div class="detail-row"><div class="detail-key">Type</div><div>{safe(finding.get("type", ""))}</div></div>
    <div class="detail-row"><div class="detail-key">Summary</div><div>{summary_html}</div></div>
    <div class="detail-row"><div class="detail-key">Modules</div><div>{module_links or '<span class="muted">No direct module references found</span>'}</div></div>
  </div>
</details>
"""
        sections += f"<section><h2>{safe(severity.title())}</h2>{rows}</section>"

    if not findings:
        sections = '<div class="empty-state">No provider findings or issues found in resource stubs.</div>'

    body = f"""
<h1>Provider Currency</h1>
<p class="subtitle">Provider release findings and open provider issues grouped by severity.</p>
<div class="stats">{stat_cards}</div>
{sections}
"""
    return body, "", ""

