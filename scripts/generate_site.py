#!/usr/bin/env python3
"""generate_site.py — Generate a static HTML health dashboard for the AVM catalog.

Reads all data/modules/ YAMLs and writes a single-file static HTML scorecard
to docs/site/index.html. No external dependencies — the output is self-contained
with inline CSS. No build step required.

Usage:
    python3 scripts/generate_site.py [options]
    ./avm.sh site [options]    # operator alias

Options:
    --output FILE    Output path (default: docs/site/index.html).
    --domains LIST   Comma-separated domain slugs (or 'all').
    --types LIST     Comma-separated module types: res, ptn, utl (or 'all').
    --open           Open the output file in the default browser after generation.
"""

import os
import re
import sys
import webbrowser
from datetime import datetime, timezone
from html import escape

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT    = os.path.dirname(SCRIPT_DIR)
MODULES_DIR  = os.path.join(REPO_ROOT, "data", "modules")
DEFAULT_OUT  = os.path.join(REPO_ROOT, "docs", "site", "index.html")

# ---------------------------------------------------------------------------
# Severity weights (kept in sync with analyze_module.py + report.py)
# ---------------------------------------------------------------------------
DIMENSION_SEVERITY: dict[str, dict] = {
    "security-hardening":       {"level": "critical", "weight": 4},
    "avm-interface-compliance": {"level": "high",     "weight": 3},
    "dependency-health":        {"level": "high",     "weight": 3},
    "provider-currency":        {"level": "high",     "weight": 3},
    "test-coverage":            {"level": "medium",   "weight": 2},
    "doc-quality":              {"level": "medium",   "weight": 2},
    "terraform-metadata":       {"level": "low",      "weight": 1},
}

STATUS_VALUE: dict[str, float] = {
    "pass":      1.0,
    "partial":   0.5,
    "unchecked": 0.5,
    "fail":      0.0,
    "missing":   0.0,
    "failed":    0.0,
    "skip":      0.5,
}

_KEY_TO_DIM: dict[str, str] = {
    "analysis_terraform_metadata":       "terraform-metadata",
    "analysis_avm_interface_compliance": "avm-interface-compliance",
    "analysis_security_hardening":       "security-hardening",
    "analysis_test_coverage":            "test-coverage",
    "analysis_doc_quality":              "doc-quality",
    "analysis_dependency_health":        "dependency-health",
    "analysis_provider_currency":        "provider-currency",
}

_DIM_ABBREV: dict[str, str] = {
    "terraform-metadata":       "TM",
    "avm-interface-compliance": "AI",
    "security-hardening":       "SH",
    "test-coverage":            "TC",
    "doc-quality":              "DQ",
    "dependency-health":        "DH",
    "provider-currency":        "PC",
}

# ---------------------------------------------------------------------------
# YAML parsers (stdlib only)
# ---------------------------------------------------------------------------

def _read_raw(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _extract_catalog_fields(content: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    in_catalog = False
    for line in content.splitlines():
        if line.strip() == "# BEGIN CATALOG":
            in_catalog = True
            continue
        if line.strip() == "# END CATALOG":
            break
        if not in_catalog:
            continue
        m = re.match(r'^  (name|domain|type|status|display_name|repo_url|last_synced):\s+"?([^"#\n]+)"?', line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"')
    return fields


def _extract_analysis_blocks(content: str) -> dict[str, dict]:
    """Return {yaml_key: {status, checked_at}} for each analysis block."""
    results: dict[str, dict] = {}
    current_key: str | None  = None
    in_block = False
    data: dict = {}

    for line in content.splitlines():
        if line.startswith("# BEGIN ANALYSIS:"):
            in_block = True
            data = {}
            current_key = None
            continue
        if line.startswith("# END ANALYSIS:"):
            if current_key:
                results[current_key] = data
            in_block = False
            current_key = None
            continue
        if not in_block:
            continue
        if current_key is None:
            m = re.match(r'^(analysis_\w+):', line)
            if m:
                current_key = m.group(1)
            continue
        m = re.match(r'^\s{2}checked_at:\s+"([^"]+)"', line)
        if m:
            data["checked_at"] = m.group(1)
            continue
        m = re.match(r'^\s{2}status:\s+(\S+)', line)
        if m:
            data["status"] = m.group(1)

    return results


def _extract_version_pinned(content: str) -> str:
    m = re.search(r'^\s+version_pinned:\s*"([^"]*)"', content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _extract_last_synced(content: str) -> str:
    m = re.search(r'^  last_synced:\s*"([^"]+)"', content, re.MULTILINE)
    return m.group(1)[:10] if m else ""


def _extract_owners(content: str) -> dict[str, dict[str, str]]:
    """Parse the catalog owners block.

    Returns {'primary': {'handle': ..., 'name': ...}, 'secondary': {'handle': ..., 'name': ...}}.
    """
    owners: dict[str, dict[str, str]] = {
        "primary":   {"handle": "", "name": ""},
        "secondary": {"handle": "", "name": ""},
    }
    in_catalog  = False
    in_owners   = False
    current_key = ""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "# BEGIN CATALOG":
            in_catalog = True
            continue
        if stripped == "# END CATALOG":
            break
        if not in_catalog:
            continue
        if stripped == "owners:":
            in_owners = True
            continue
        if in_owners:
            if re.match(r"^  \w", line) and not line.startswith("    "):
                # back to catalog-level key — owners block ended
                in_owners = False
                continue
            m_key = re.match(r"^\s{4}(primary|secondary):", line)
            if m_key:
                current_key = m_key.group(1)
                continue
            m_val = re.match(r'^\s{6}(handle|name):\s*"?([^"#\n]*)"?', line)
            if m_val and current_key in owners:
                owners[current_key][m_val.group(1)] = m_val.group(2).strip().strip('"')
    return owners


# ---------------------------------------------------------------------------
# Module loader
# ---------------------------------------------------------------------------

def load_modules(
    filter_domains: list[str] | None = None,
    filter_types:   list[str] | None = None,
) -> list[dict]:
    modules: list[dict] = []
    for mod_type in ("res", "ptn", "utl"):
        if filter_types and mod_type not in filter_types:
            continue
        type_dir = os.path.join(MODULES_DIR, mod_type)
        if not os.path.isdir(type_dir):
            continue
        for fname in sorted(os.listdir(type_dir)):
            if not fname.endswith(".yaml"):
                continue
            filepath = os.path.join(type_dir, fname)
            content  = _read_raw(filepath)
            if not content:
                continue
            catalog = _extract_catalog_fields(content)
            domain  = catalog.get("domain", "")
            if filter_domains and domain not in filter_domains:
                continue
            raw_analysis = _extract_analysis_blocks(content)
            analysis: dict[str, dict] = {
                _KEY_TO_DIM[k]: v
                for k, v in raw_analysis.items()
                if k in _KEY_TO_DIM
            }
            modules.append({
                "name":          catalog.get("name", fname[:-5]),
                "domain":        domain,
                "type":          mod_type,
                "status":        catalog.get("status", ""),
                "display_name":  catalog.get("display_name", ""),
                "repo_url":      catalog.get("repo_url", ""),
                "last_synced":   _extract_last_synced(content),
                "version_pinned": _extract_version_pinned(content),
                "analysis":      analysis,
                "owners":        _extract_owners(content),
            })
    return modules


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def compute_score(analysis: dict[str, dict]) -> tuple[float, dict[str, str]]:
    """Return (score 0–100, {dim: status}) for a module."""
    total_weight = 0.0
    weighted_sum = 0.0
    dim_statuses: dict[str, str] = {}
    for dim, meta in DIMENSION_SEVERITY.items():
        data   = analysis.get(dim)
        if data is None:
            dim_statuses[dim] = "—"
            continue
        status = data.get("status", "")
        value  = STATUS_VALUE.get(status, 0.5)
        weight = meta["weight"]
        weighted_sum  += weight * value
        total_weight  += weight
        dim_statuses[dim] = status
    score = (weighted_sum / total_weight * 100.0) if total_weight > 0 else 0.0
    return round(score, 1), dim_statuses


def _staleness_days(analysis: dict[str, dict]) -> int | None:
    now    = datetime.now(timezone.utc)
    oldest: int | None = None
    for data in analysis.values():
        checked = data.get("checked_at")
        if not checked:
            continue
        try:
            ts  = datetime.fromisoformat(checked.replace("Z", "+00:00"))
            age = (now - ts).days
            if oldest is None or age > oldest:
                oldest = age
        except ValueError:
            pass
    return oldest


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

_CSS = """
:root {
  --bg:       #0d1117;
  --bg2:      #161b22;
  --bg3:      #21262d;
  --border:   #30363d;
  --text:     #e6edf3;
  --muted:    #8b949e;
  --green:    #3fb950;
  --orange:   #d29922;
  --red:      #f85149;
  --blue:     #58a6ff;
  --purple:   #bc8cff;
  color-scheme: dark;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 14px;
  background: var(--bg);
  color: var(--text);
  padding: 24px;
}
h1 { font-size: 22px; font-weight: 600; margin-bottom: 4px; }
.subtitle { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
.stats {
  display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 28px;
}
.stat-card {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px 18px; min-width: 120px;
}
.stat-card .val { font-size: 22px; font-weight: 700; line-height: 1.2; }
.stat-card .lbl { color: var(--muted); font-size: 12px; margin-top: 2px; }
details { margin-bottom: 16px; }
summary {
  list-style: none; cursor: pointer;
  display: flex; align-items: center; gap: 8px;
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 16px;
  font-weight: 600; font-size: 15px;
  user-select: none;
}
details[open] > summary { border-radius: 8px 8px 0 0; border-bottom-color: transparent; }
summary::before { content: "▶"; font-size: 11px; color: var(--muted); transition: transform .15s; }
details[open] summary::before { transform: rotate(90deg); }
.domain-stats { margin-left: auto; font-size: 12px; color: var(--muted); font-weight: 400; display: flex; gap: 10px; }
table {
  width: 100%; border-collapse: collapse;
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 0 0 8px 8px; overflow: hidden;
}
th, td { padding: 7px 12px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
tr:last-child td { border-bottom: none; }
th { background: var(--bg3); color: var(--muted); font-size: 12px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }
td.name { font-family: monospace; font-size: 12px; white-space: nowrap; }
td.name a { color: var(--blue); text-decoration: none; }
td.name a:hover { text-decoration: underline; }
.score { font-weight: 700; font-size: 13px; }
.score-green  { color: var(--green);  }
.score-orange { color: var(--orange); }
.score-red    { color: var(--red);    }
.score-grey   { color: var(--muted);  }
.badge {
  display: inline-block; padding: 1px 5px; border-radius: 4px;
  font-size: 11px; font-weight: 600; line-height: 1.5;
}
.pass    { background: rgba(63,185,80,.15);  color: var(--green);  }
.partial { background: rgba(210,153,34,.15); color: var(--orange); }
.fail    { background: rgba(248,81,73,.15);  color: var(--red);    }
.none    { background: rgba(139,148,158,.1); color: var(--muted);  }
.stale-badge { font-size: 11px; padding: 1px 5px; border-radius: 4px; margin-left: 4px; }
.stale-warn  { background: rgba(210,153,34,.2); color: var(--orange); }
.stale-crit  { background: rgba(248,81,73,.2);  color: var(--red);    }
.type-badge  { font-size: 11px; padding: 1px 5px; border-radius: 4px; background: rgba(188,140,255,.15); color: var(--purple); }
.version     { font-size: 12px; color: var(--muted); font-family: monospace; }
footer       { margin-top: 32px; color: var(--muted); font-size: 12px; text-align: center; }
/* --- Heatmap --- */
.heatmap { border-collapse: collapse; margin-bottom: 0; border-radius: 0 0 8px 8px; }
.heatmap th, .heatmap td { padding: 6px 10px; text-align: center; border: 1px solid var(--border); font-size: 12px; }
.heatmap th { background: var(--bg3); color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.heatmap td.dom-name { text-align: left; font-weight: 500; min-width: 140px; white-space: nowrap; }
.hm-green  { background: rgba(63,185,80,.18);  color: var(--green);  font-weight: 600; }
.hm-orange { background: rgba(210,153,34,.18); color: var(--orange); font-weight: 600; }
.hm-red    { background: rgba(248,81,73,.18);  color: var(--red);    font-weight: 600; }
.hm-grey   { background: transparent;          color: var(--muted);  }
/* --- Owner map --- */
.owner-handle { font-family: monospace; font-size: 12px; color: var(--blue); }
.owner-name   { font-size: 12px; color: var(--muted); }
.no-secondary { color: var(--red); font-size: 11px; }
.mod-chip {
  display: inline-block; font-family: monospace; font-size: 11px;
  background: var(--bg3); border: 1px solid var(--border);
  border-radius: 4px; padding: 1px 5px; margin: 1px 2px;
  color: var(--text); white-space: nowrap;
}
.mod-chip a { color: var(--blue); text-decoration: none; }
.mod-chip a:hover { text-decoration: underline; }
"""

_DIM_ORDER = [
    "security-hardening",
    "avm-interface-compliance",
    "dependency-health",
    "provider-currency",
    "test-coverage",
    "doc-quality",
    "terraform-metadata",
]


def _score_class(score: float, has_data: bool) -> str:
    if not has_data:
        return "score-grey"
    if score >= 80:
        return "score-green"
    if score >= 60:
        return "score-orange"
    return "score-red"


def _badge(status: str) -> str:
    abbrev = _DIM_ABBREV.get(status, "")
    if status == "pass":
        return f'<span class="badge pass">✓</span>'
    if status in ("partial", "unchecked", "skip"):
        return f'<span class="badge partial">⚠</span>'
    if status in ("fail", "missing", "failed"):
        return f'<span class="badge fail">✗</span>'
    return f'<span class="badge none">–</span>'


def _stale_badge(days: int | None) -> str:
    if days is None:
        return ""
    if days > 30:
        return f'<span class="stale-badge stale-crit">stale {days}d</span>'
    if days > 14:
        return f'<span class="stale-badge stale-warn">stale {days}d</span>'
    return ""


def _render_module_row(mod: dict) -> str:
    score, dim_statuses = compute_score(mod["analysis"])
    has_data = any(v != "—" for v in dim_statuses.values())
    score_cls = _score_class(score, has_data)
    score_str = f"{score:.0f}%" if has_data else "—"

    stale = _staleness_days(mod["analysis"])
    stale_html = _stale_badge(stale)

    repo_url = mod.get("repo_url", "")
    name_html = (
        f'<a href="{escape(repo_url)}" target="_blank">{escape(mod["name"])}</a>'
        if repo_url else escape(mod["name"])
    )

    badges_html = "".join(_badge(dim_statuses.get(d, "—")) for d in _DIM_ORDER)
    version_html = escape(mod["version_pinned"]) if mod["version_pinned"] else '<span style="color:var(--muted)">—</span>'
    synced_html  = escape(mod["last_synced"]) if mod["last_synced"] else '<span style="color:var(--muted)">—</span>'
    type_html    = f'<span class="type-badge">{escape(mod["type"])}</span>'

    return (
        f'<tr>'
        f'<td class="name">{name_html}{stale_html}</td>'
        f'<td>{type_html}</td>'
        f'<td><span class="score {score_cls}">{score_str}</span></td>'
        f'<td>{badges_html}</td>'
        f'<td class="version">{version_html}</td>'
        f'<td class="version">{synced_html}</td>'
        f'</tr>\n'
    )


def _render_domain(domain: str, mods: list[dict]) -> str:
    rows = "".join(_render_module_row(m) for m in mods)
    scores = [compute_score(m["analysis"])[0] for m in mods if m["analysis"]]
    avg_score = (sum(scores) / len(scores)) if scores else 0.0
    score_cls = _score_class(avg_score, bool(scores))

    dim_headers = "".join(
        f'<th title="{escape(d)}">{escape(_DIM_ABBREV[d])}</th>' for d in _DIM_ORDER
    )
    dom_name = escape(domain.replace("-", " ").title())
    stats_html = (
        f'<span class="domain-stats">'
        f'<span>{len(mods)} modules</span>'
        f'<span class="score {score_cls}">avg {avg_score:.0f}%</span>'
        f'</span>'
    )

    return f"""
<details open>
  <summary>{dom_name}{stats_html}</summary>
  <table>
    <thead>
      <tr>
        <th>Module</th><th>Type</th><th>Score</th>
        <th style="font-size:11px">SH&nbsp;AI&nbsp;DH&nbsp;PC&nbsp;TC&nbsp;DQ&nbsp;TM</th>
        <th>Version</th><th>Synced</th>
      </tr>
    </thead>
    <tbody>
{rows}    </tbody>
  </table>
</details>
"""


def _render_coverage_heatmap(by_domain: dict[str, list[dict]]) -> str:
    """Render a domain × dimension heatmap panel.

    Each cell shows how many modules in the domain have pass/partial/fail for
    a given dimension and is colour-coded accordingly.
    """
    dim_headers = "".join(
        f'<th title="{escape(d)}">{escape(_DIM_ABBREV[d])}</th>'
        for d in _DIM_ORDER
    )

    rows_html = ""
    for domain in sorted(by_domain.keys()):
        mods = by_domain[domain]
        dom_label = escape(domain.replace("-", " ").title())
        scores = [compute_score(m["analysis"])[0] for m in mods if m["analysis"]]
        avg = (sum(scores) / len(scores)) if scores else 0.0
        avg_cls = _score_class(avg, bool(scores))
        avg_html = f'<span class="score {avg_cls}" style="font-size:11px">{avg:.0f}%</span>'

        cells_html = ""
        for dim in _DIM_ORDER:
            counts = {"pass": 0, "partial": 0, "fail": 0, "unchecked": 0, "missing": 0, "other": 0}
            total_with_data = 0
            for m in mods:
                dim_data = m["analysis"].get(dim)
                if dim_data is None:
                    continue
                total_with_data += 1
                st = dim_data.get("status", "")
                if st == "pass":
                    counts["pass"] += 1
                elif st in ("partial", "unchecked", "skip"):
                    counts["partial"] += 1
                elif st in ("fail", "failed", "missing"):
                    counts["fail"] += 1
                else:
                    counts["other"] += 1

            if total_with_data == 0:
                cells_html += '<td class="hm-grey">—</td>'
            elif counts["fail"] > 0:
                cells_html += f'<td class="hm-red" title="{counts["fail"]} fail · {counts["partial"]} partial · {counts["pass"]} pass">{counts["pass"]}/{total_with_data}</td>'
            elif counts["partial"] > 0:
                cells_html += f'<td class="hm-orange" title="{counts["partial"]} partial · {counts["pass"]} pass">{counts["pass"]}/{total_with_data}</td>'
            else:
                cells_html += f'<td class="hm-green" title="all pass">{counts["pass"]}/{total_with_data}</td>'

        rows_html += (
            f"<tr>"
            f'<td class="dom-name">{dom_label} {avg_html}</td>'
            f"{cells_html}"
            f"</tr>\n"
        )

    return f"""
<details open>
  <summary>Domain × Dimension Heatmap<span class="domain-stats"><span>pass count / analyzed</span></span></summary>
  <table class="heatmap">
    <thead>
      <tr>
        <th style="text-align:left">Domain</th>
        {dim_headers}
      </tr>
    </thead>
    <tbody>
{rows_html}    </tbody>
  </table>
</details>
"""


def _render_owner_map(modules: list[dict]) -> str:
    """Render a collapsible owner map panel.

    Groups modules by primary owner; highlights those missing a secondary owner.
    """
    # Build owner → [module, ...] map
    by_owner: dict[str, list[dict]] = {}
    for m in modules:
        owners = m.get("owners", {})
        primary = owners.get("primary", {})
        handle  = primary.get("handle", "").strip()
        if not handle:
            handle = "unassigned"
        by_owner.setdefault(handle, []).append(m)

    # Sort by module count descending, then by handle alphabetically
    sorted_owners = sorted(by_owner.keys(), key=lambda h: (-len(by_owner[h]), h))

    rows_html = ""
    for handle in sorted_owners:
        owner_mods = by_owner[handle]
        # Primary owner name from first module that has it
        primary_name = ""
        for m in owner_mods:
            name = m.get("owners", {}).get("primary", {}).get("name", "").strip()
            if name:
                primary_name = name
                break

        handle_html = (
            f'<a href="https://github.com/{escape(handle)}" target="_blank">{escape(handle)}</a>'
            if handle != "unassigned"
            else '<span style="color:var(--muted)">unassigned</span>'
        )

        chips_html = ""
        for m in sorted(owner_mods, key=lambda x: x["name"]):
            sec_handle = m.get("owners", {}).get("secondary", {}).get("handle", "").strip()
            missing    = not sec_handle
            chip_title = "" if not missing else ' title="No secondary owner"'
            chip_style = ' style="border-color:rgba(248,81,73,.4)"' if missing else ""
            repo_url   = m.get("repo_url", "")
            short_name = m["name"].replace("avm-res-", "").replace("avm-ptn-", "").replace("avm-utl-", "")
            mod_link   = (
                f'<a href="{escape(repo_url)}" target="_blank">{escape(short_name)}</a>'
                if repo_url
                else escape(short_name)
            )
            chips_html += f'<span class="mod-chip"{chip_style}{chip_title}>{mod_link}</span>'

        no_sec_count = sum(
            1 for m in owner_mods
            if not m.get("owners", {}).get("secondary", {}).get("handle", "").strip()
        )
        no_sec_html = (
            f'<span class="no-secondary">{no_sec_count} missing</span>'
            if no_sec_count > 0
            else '<span style="color:var(--muted)">—</span>'
        )

        rows_html += (
            f"<tr>"
            f'<td><span class="owner-handle">{handle_html}</span><br>'
            f'<span class="owner-name">{escape(primary_name)}</span></td>'
            f"<td>{len(owner_mods)}</td>"
            f"<td>{no_sec_html}</td>"
            f"<td>{chips_html}</td>"
            f"</tr>\n"
        )

    return f"""
<details>
  <summary>Owner Map<span class="domain-stats"><span>{len(modules)} modules · {len(sorted_owners)} owners</span></span></summary>
  <table>
    <thead>
      <tr>
        <th>Owner</th><th>Modules</th><th>No 2nd owner</th><th>Module list</th>
      </tr>
    </thead>
    <tbody>
{rows_html}    </tbody>
  </table>
</details>
"""


def generate_site(
    filter_domains: list[str] | None = None,
    filter_types:   list[str] | None = None,
    output:         str = DEFAULT_OUT,
    open_browser:   bool = False,
) -> None:
    modules = load_modules(filter_domains, filter_types)
    if not modules:
        print("No modules found.", file=sys.stderr)
        sys.exit(1)

    # Group by domain
    by_domain: dict[str, list[dict]] = {}
    for m in modules:
        by_domain.setdefault(m["domain"] or "unknown", []).append(m)

    # Stats
    total   = len(modules)
    by_type: dict[str, int] = {}
    for m in modules:
        by_type[m["type"]] = by_type.get(m["type"], 0) + 1

    all_scores = [compute_score(m["analysis"])[0] for m in modules if m["analysis"]]
    avg_overall = (sum(all_scores) / len(all_scores)) if all_scores else 0.0
    analyzed_n  = sum(1 for m in modules if m["analysis"])

    no_secondary_n = sum(
        1 for m in modules
        if not m.get("owners", {}).get("secondary", {}).get("handle", "").strip()
    )

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    stats_html = f"""
    <div class="stat-card"><div class="val">{total}</div><div class="lbl">Modules</div></div>
    <div class="stat-card"><div class="val">{len(by_domain)}</div><div class="lbl">Domains</div></div>
    <div class="stat-card"><div class="val">{by_type.get('res', 0)}</div><div class="lbl">res</div></div>
    <div class="stat-card"><div class="val">{by_type.get('ptn', 0)}</div><div class="lbl">ptn</div></div>
    <div class="stat-card"><div class="val">{by_type.get('utl', 0)}</div><div class="lbl">utl</div></div>
    <div class="stat-card"><div class="val">{analyzed_n}</div><div class="lbl">Analyzed</div></div>
    <div class="stat-card"><div class="val">{avg_overall:.0f}%</div><div class="lbl">Avg score</div></div>
    <div class="stat-card"><div class="val" style="color:var(--orange)">{no_secondary_n}</div><div class="lbl">No 2nd owner</div></div>
"""

    heatmap_html  = _render_coverage_heatmap(by_domain)
    owner_map_html = _render_owner_map(modules)

    domains_html = "".join(
        _render_domain(dom, mods)
        for dom, mods in sorted(by_domain.items())
    )

    legend_html = "".join(
        f'<span class="badge pass">✓ pass</span> '
        f'<span class="badge partial">⚠ partial</span> '
        f'<span class="badge fail">✗ fail</span> '
        f'<span class="badge none">– no data</span>'
    )

    dim_legend = " &nbsp;·&nbsp; ".join(
        f'<b>{_DIM_ABBREV[d]}</b> = {d}' for d in _DIM_ORDER
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AVM Intelligence Dashboard</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>⚡ AVM Intelligence Dashboard</h1>
  <p class="subtitle">Generated: {escape(now_str)} &nbsp;·&nbsp; {legend_html}</p>
  <div class="stats">{stats_html}</div>
  <p style="font-size:12px;color:var(--muted);margin-bottom:16px">{dim_legend}</p>
  {heatmap_html}
  {owner_map_html}
  {domains_html}
  <footer>Auto-generated by <code>scripts/generate_site.py</code> · Crayon-HU/avm-metadata</footer>
</body>
</html>
"""

    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    import tempfile
    out_dir = os.path.dirname(os.path.abspath(output))
    tmp_fd, tmp_path = tempfile.mkstemp(dir=out_dir, suffix=".html.tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(html)
        os.replace(tmp_path, output)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    print(f"  ✓  Generated: {output}")
    print(f"     {total} modules  |  {len(by_domain)} domains  |  avg score {avg_overall:.0f}%")

    if open_browser:
        webbrowser.open(f"file://{os.path.abspath(output)}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> dict:
    args: dict = {
        "domains":      None,
        "types":        None,
        "output":       DEFAULT_OUT,
        "open_browser": False,
    }
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        elif tok in ("--domains", "--domain") and i + 1 < len(argv):
            i += 1
            args["domains"] = [d.strip() for d in argv[i].split(",") if d.strip() and d.strip() != "all"]
        elif tok in ("--types", "--type") and i + 1 < len(argv):
            i += 1
            args["types"] = [t.strip() for t in argv[i].split(",") if t.strip() and t.strip() != "all"]
        elif tok in ("--output", "-o") and i + 1 < len(argv):
            i += 1
            args["output"] = argv[i]
        elif tok == "--open":
            args["open_browser"] = True
        i += 1
    return args


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    a = _parse_args(argv)
    generate_site(
        filter_domains = a["domains"] or None,
        filter_types   = a["types"]   or None,
        output         = a["output"],
        open_browser   = a["open_browser"],
    )


if __name__ == "__main__":
    main()
