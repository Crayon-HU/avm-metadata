#!/usr/bin/env python3
"""report.py — Read-only reporting for the AVM metadata catalog.

Reads all data/modules/ YAMLs and produces human-readable reports.
No files are modified by this script.

Usage:
    python3 scripts/report.py [subcommand] [options]
    ./avm.sh report [subcommand] [options]    # operator alias

Subcommands:
    --scores              Weighted compliance scorecard ranked by overall score.
    --issues              Cross-module open issue rollup, grouped by severity.
    --json                Export full catalog to a single JSON file.
    --provider-findings   Triage table of provider update findings by module.

Common options:
    --domain  DOMAIN[,…]   Filter by domain (comma-separated; or 'all').
    --type    TYPE[,…]     Filter by type: res, ptn, utl (comma-separated; or 'all').
    --output  FILE         Write output to FILE instead of stdout.

--scores specific:
    --min-score  N         Only show modules with score < N (0–100).

--issues specific:
    --severity  LEVEL[,…]  Filter by severity: critical, high, medium, low.
    --open-only            Only show issues with status: open (default: True).

--provider-findings specific:
    --severity LEVEL[,…]   Filter by severity (default: critical,high).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
MODULES_DIR = os.path.join(REPO_ROOT, "data", "modules")

# ---------------------------------------------------------------------------
# Severity weights — kept in sync with analyze_module.DIMENSION_SEVERITY.
# Defined here as well so report.py has no runtime import dependency on
# analyze_module.py (which requires a cloned repo context to be useful).
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

# Status → numeric value for scoring (0.0 – 1.0).
STATUS_VALUE: dict[str, float] = {
    "pass":       1.0,
    "partial":    0.5,
    "unchecked":  0.5,  # treat unchecked as neutral, not failure
    "fail":       0.0,
    "missing":    0.0,
    "failed":     0.0,
    "skip":       0.5,
}

# Maps the YAML analysis_* key prefix to the dimension slug.
_KEY_TO_DIM: dict[str, str] = {
    "analysis_terraform_metadata":       "terraform-metadata",
    "analysis_avm_interface_compliance": "avm-interface-compliance",
    "analysis_security_hardening":       "security-hardening",
    "analysis_test_coverage":            "test-coverage",
    "analysis_doc_quality":              "doc-quality",
    "analysis_dependency_health":        "dependency-health",
    "analysis_provider_currency":        "provider-currency",
}

_SEVERITY_ORDER = ["critical", "high", "medium", "low"]

# ---------------------------------------------------------------------------
# Terminal colour helpers
# ---------------------------------------------------------------------------

def _c_ok(s: str)   -> str: return f"\033[32m{s}\033[0m"
def _c_warn(s: str) -> str: return f"\033[33m{s}\033[0m"
def _c_err(s: str)  -> str: return f"\033[31m{s}\033[0m"
def _c_dim(s: str)  -> str: return f"\033[2m{s}\033[0m"
def _c_bold(s: str) -> str: return f"\033[1m{s}\033[0m"

def _status_icon(status: str) -> str:
    if status == "pass":   return _c_ok("✓")
    if status == "partial": return _c_warn("⚠")
    return _c_err("✗")

# ---------------------------------------------------------------------------
# Minimal YAML reader
# ---------------------------------------------------------------------------

def _read_yaml_raw(filepath: str) -> str:
    """Return raw file content, or '' on error."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _extract_catalog_fields(content: str) -> dict[str, str]:
    """Extract key: value pairs from the CATALOG block (name, domain, type, status).

    Only matches top-level catalog fields (2-space indented), not nested keys
    such as owner.name which sit deeper inside the catalog block.
    """
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
        # Match only top-level catalog fields: exactly 2 spaces of indentation
        m = re.match(r'^  (name|domain|type|status|display_name):\s+"?([^"#\n]+)"?', line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"')
    return fields


def _extract_analysis_blocks(content: str) -> dict[str, dict]:
    """Extract analysis_* blocks as {yaml_key: {field: value}} dicts.

    Only reads 'status' and 'checked_at' at the top level of each block.
    Individual check statuses are read from the 'checks:' sub-map if present.
    """
    results: dict[str, dict] = {}
    current_key: str | None = None
    in_block = False
    block_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("# BEGIN ANALYSIS:"):
            in_block = True
            block_lines = []
            current_key = None
            continue
        if line.startswith("# END ANALYSIS:"):
            if current_key and block_lines:
                results[current_key] = _parse_analysis_block_lines(block_lines)
            in_block = False
            block_lines = []
            current_key = None
            continue
        if in_block:
            block_lines.append(line)
            # The first non-empty, non-comment line that matches analysis_*: is the key
            if current_key is None:
                m = re.match(r'^(analysis_\w+):', line)
                if m:
                    current_key = m.group(1)

    return results


def _parse_analysis_block_lines(lines: list[str]) -> dict:
    """Parse top-level status, checked_at, and checks sub-map from block lines."""
    result: dict = {}
    in_checks = False
    checks: dict[str, str] = {}

    for line in lines:
        # Top-level checked_at
        m = re.match(r'^\s{2}checked_at:\s+"([^"]+)"', line)
        if m and not in_checks:
            result["checked_at"] = m.group(1)
            continue
        # Top-level status
        m = re.match(r'^\s{2}status:\s+(\S+)', line)
        if m and not in_checks:
            result["status"] = m.group(1)
            continue
        # Start of checks: block (indented 2 spaces)
        if re.match(r'^\s{2}checks:', line):
            in_checks = True
            continue
        # Inside checks: individual check status
        if in_checks:
            # Check name line: "    check_name: { status: X, ... }"
            m = re.match(r'^\s{4}(\w+):\s*\{.*?status:\s+(\w+)', line)
            if m:
                checks[m.group(1)] = m.group(2)
            # Indented further — not a new check
            elif re.match(r'^\s{2}\S', line):
                in_checks = False

    if checks:
        result["checks"] = checks
    return result


def _extract_enrichment_issues(content: str) -> list[dict]:
    """Extract enrichment.known_issues entries from a module YAML."""
    issues: list[dict] = []
    in_enrichment = False
    in_issues = False
    current_issue: dict | None = None

    for line in content.splitlines():
        if re.match(r'^enrichment:', line):
            in_enrichment = True
            continue
        if in_enrichment and re.match(r'^(\S)', line) and not re.match(r'^enrichment:', line):
            in_enrichment = False
            in_issues = False
            continue
        if not in_enrichment:
            continue

        # Detect known_issues: list start
        if re.match(r'^\s+known_issues:', line):
            in_issues = True
            current_issue = None
            continue

        # Another top-level enrichment key ends the issues block
        if in_issues and re.match(r'^\s{2}\S', line) and not re.match(r'^\s{2}-', line):
            in_issues = False
            if current_issue is not None:
                issues.append(current_issue)
                current_issue = None
            continue

        if not in_issues:
            continue

        # New issue entry
        m = re.match(r'^\s{2}-\s+title:\s+"?([^"#\n]+)"?', line)
        if m:
            if current_issue is not None:
                issues.append(current_issue)
            current_issue = {"title": m.group(1).strip().strip('"')}
            continue

        if current_issue is None:
            continue

        # Issue fields
        for key in ("status", "severity", "workaround", "url"):
            m = re.match(rf'^\s+{key}:\s+"?([^"#\n]+)"?', line)
            if m:
                current_issue[key] = m.group(1).strip().strip('"')

    if current_issue is not None:
        issues.append(current_issue)

    return issues

# ---------------------------------------------------------------------------
# Module loader
# ---------------------------------------------------------------------------

def load_modules(
    filter_domains: list[str] | None = None,
    filter_types:   list[str] | None = None,
) -> list[dict]:
    """Load all module YAMLs from data/modules/, returning a list of parsed dicts.

    Each dict has keys: name, domain, type, status, display_name,
    analysis (dict keyed by dim slug), issues (list), raw (file content).
    """
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
            content  = _read_yaml_raw(filepath)
            if not content:
                continue

            catalog = _extract_catalog_fields(content)
            domain  = catalog.get("domain", "")
            if filter_domains and domain not in filter_domains:
                continue

            # Map analysis_* yaml keys to dimension slugs
            raw_analysis = _extract_analysis_blocks(content)
            analysis: dict[str, dict] = {}
            for yaml_key, data in raw_analysis.items():
                dim = _KEY_TO_DIM.get(yaml_key)
                if dim:
                    analysis[dim] = data

            modules.append({
                "name":         catalog.get("name", fname[:-5]),
                "domain":       domain,
                "type":         mod_type,
                "status":       catalog.get("status", ""),
                "display_name": catalog.get("display_name", ""),
                "analysis":     analysis,
                "issues":       _extract_enrichment_issues(content),
                "raw":          content,
                "filepath":     filepath,
            })

    return modules

# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def compute_score(analysis: dict[str, dict]) -> tuple[float, dict[str, str]]:
    """Compute a weighted compliance score (0.0–100.0) from analysis blocks.

    Returns (score, {dim: status}) where score is the weighted percentage.
    Dimensions with no data are excluded from the denominator.
    """
    total_weight  = 0.0
    weighted_sum  = 0.0
    dim_statuses: dict[str, str] = {}

    for dim, meta in DIMENSION_SEVERITY.items():
        data = analysis.get(dim)
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
    """Return the age in days of the oldest checked_at across all dimensions, or None."""
    now = datetime.now(timezone.utc)
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
# Subcommand: --scores
# ---------------------------------------------------------------------------

_DIM_ABBREV = {
    "terraform-metadata":       "tm",
    "avm-interface-compliance": "ai",
    "security-hardening":       "sh",
    "test-coverage":            "tc",
    "doc-quality":              "dq",
    "dependency-health":        "dh",
    "provider-currency":        "pc",
}
_STATUS_BADGE_PLAIN = {
    "pass":    "✓",
    "partial": "⚠",
    "fail":    "✗",
    "—":       "–",
}
_STATUS_BADGE_COLOR = {
    "pass":    _c_ok,
    "partial": _c_warn,
    "fail":    _c_err,
    "—":       _c_dim,
}


def _dim_badge(status: str) -> str:
    """Return a 1-char badge with ANSI colour. Safe for column-separated output."""
    plain = _STATUS_BADGE_PLAIN.get(status, "?")
    color = _STATUS_BADGE_COLOR.get(status, lambda s: s)
    return color(plain)


def cmd_scores(
    modules:   list[dict],
    min_score: float = 0.0,
    output:    str | None = None,
) -> None:
    """Print weighted compliance scorecard sorted by score descending."""
    rows: list[tuple[float, dict]] = []
    for mod in modules:
        score, dim_statuses = compute_score(mod["analysis"])
        if score < min_score:
            rows.append((score, {"mod": mod, "dim_statuses": dim_statuses}))
        elif min_score == 0.0:
            rows.append((score, {"mod": mod, "dim_statuses": dim_statuses}))

    rows.sort(key=lambda r: r[0], reverse=True)

    # Determine column widths
    max_name = max((len(r[1]["mod"]["name"]) for r in rows), default=30)
    name_w   = min(max_name, 55)

    # Header
    dims = list(DIMENSION_SEVERITY.keys())
    abbrev_header = "  ".join(f"{_DIM_ABBREV[d]:>2}" for d in dims)
    header = (
        f"  {'Score':>6}  {'Stale':>5}  {abbrev_header}  {'Module':<{name_w}}  Domain"
    )
    sep = "─" * len(header)

    lines: list[str] = [
        "",
        _c_bold("AVM Compliance Scorecard"),
        f"  Columns: {', '.join(f'{v}={k}' for k, v in _DIM_ABBREV.items())}",
        f"  Severity weights: " + ", ".join(
            f"{k}={v['weight']}({v['level']})" for k, v in DIMENSION_SEVERITY.items()
        ),
        sep,
        header,
        sep,
    ]

    for score, row in rows:
        mod        = row["mod"]
        dim_s      = row["dim_statuses"]
        stale      = _staleness_days(mod["analysis"])
        stale_str  = f"{stale}d" if stale is not None else "   —"
        stale_disp = _c_warn(stale_str) if stale is not None and stale > 14 else stale_str

        badges = "  ".join(
            _dim_badge(dim_s.get(d, "—"))
            for d in dims
        )
        score_str = _c_err(f"{score:5.1f}%") if score < 60 else (
            _c_warn(f"{score:5.1f}%") if score < 85 else _c_ok(f"{score:5.1f}%")
        )
        name_disp  = mod["name"][:name_w]
        lines.append(
            f"  {score_str}  {stale_disp:>5}  {badges}  {name_disp:<{name_w}}  {mod['domain']}"
        )

    lines += [sep, f"  {len(rows)} modules"]

    text = "\n".join(lines) + "\n"
    _write_output(text, output)


# ---------------------------------------------------------------------------
# Subcommand: --issues
# ---------------------------------------------------------------------------

_SEV_ORDER_MAP = {s: i for i, s in enumerate(_SEVERITY_ORDER)}


def cmd_issues(
    modules:          list[dict],
    filter_severity:  list[str] | None = None,
    output:           str | None = None,
) -> None:
    """Print cross-module open issue rollup sorted by severity then module name."""
    rows: list[dict] = []
    for mod in modules:
        for issue in mod["issues"]:
            if issue.get("status", "open") != "open":
                continue
            sev = issue.get("severity", "low").lower()
            if filter_severity and sev not in filter_severity:
                continue
            rows.append({
                "severity":  sev,
                "module":    mod["name"],
                "domain":    mod["domain"],
                "title":     issue.get("title", ""),
                "workaround": issue.get("workaround", ""),
                "url":        issue.get("url", ""),
            })

    # Sort: severity order → module name
    rows.sort(key=lambda r: (_SEV_ORDER_MAP.get(r["severity"], 99), r["module"]))

    max_title  = max((len(r["title"]) for r in rows), default=40)
    title_w    = min(max_title, 60)
    max_module = max((len(r["module"]) for r in rows), default=35)
    module_w   = min(max_module, 50)

    header = (
        f"  {'Sev':<8}  {'Module':<{module_w}}  {'Title':<{title_w}}"
    )
    sep = "─" * len(header)

    _sev_color = {
        "critical": _c_err,
        "high":     _c_warn,
        "medium":   lambda s: s,
        "low":      _c_dim,
    }

    lines: list[str] = [
        "",
        _c_bold("AVM Open Issue Rollup"),
        f"  {len(rows)} open issue(s) across {len(modules)} module(s)",
        sep, header, sep,
    ]

    current_sev = ""
    for row in rows:
        sev = row["severity"]
        if sev != current_sev:
            current_sev = sev
            lines.append(f"  {_c_bold(sev.upper())}")
        color  = _sev_color.get(sev, lambda s: s)
        title  = row["title"][:title_w]
        module = row["module"][:module_w]
        suffix = f"  → {row['workaround']}" if row.get("workaround") else ""
        lines.append(f"  {color(f'{sev:<8}')}  {module:<{module_w}}  {title}{suffix}")

    lines += [sep, f"  Total: {len(rows)} open issue(s)"]

    text = "\n".join(lines) + "\n"
    _write_output(text, output)


# ---------------------------------------------------------------------------
# Subcommand: --provider-findings
# ---------------------------------------------------------------------------

_CRIT_ORDER = ["critical", "high", "medium", "low"]


def _extract_provider_currency_data(content: str) -> dict | None:
    """Extract analysis_provider_currency fields needed for triage report.

    Returns a dict with status, worst_criticality, finding_counts, issue_counts,
    or None if the block is absent.
    """
    in_block = False
    block_lines: list[str] = []
    for line in content.splitlines():
        if line.strip() == "# BEGIN ANALYSIS:provider-currency":
            in_block = True
            block_lines = []
            continue
        if line.strip() == "# END ANALYSIS:provider-currency":
            break
        if in_block:
            block_lines.append(line)

    if not block_lines:
        return None

    result: dict = {}
    in_finding_counts = False
    finding_counts: dict[str, int] = {}

    for line in block_lines:
        m = re.match(r'^\s{2}status:\s+(\S+)', line)
        if m:
            result["status"] = m.group(1)
            continue
        m = re.match(r'^\s{2}worst_criticality:\s+(\S+)', line)
        if m:
            result["worst_criticality"] = m.group(1)
            continue
        if re.match(r'^\s{2}finding_counts:', line):
            in_finding_counts = True
            continue
        if in_finding_counts:
            m = re.match(r'^\s{4}(critical|high|medium|low):\s+(\d+)', line)
            if m:
                finding_counts[m.group(1)] = int(m.group(2))
                continue
            # End of finding_counts block
            if re.match(r'^\s{2}\S', line):
                in_finding_counts = False
        m = re.match(r'^\s{4}total:\s+(\d+)', line)
        if m and "issue_counts" not in result:
            result["issue_counts_total"] = int(m.group(1))
            continue

    if finding_counts:
        result["finding_counts"] = finding_counts
    return result or None


def cmd_provider_findings(
    modules:         list[dict],
    filter_severity: list[str] | None = None,
    output:          str | None = None,
) -> None:
    """Print provider currency triage table sorted by worst criticality."""
    default_severity = {"critical", "high"}
    sev_filter = set(filter_severity) if filter_severity else default_severity

    _sev_order = {s: i for i, s in enumerate(_CRIT_ORDER)}

    rows: list[dict] = []
    for mod in modules:
        pf = _extract_provider_currency_data(mod["raw"])
        if pf is None:
            continue
        worst = pf.get("worst_criticality", "none")
        if worst in ("none", "unknown") and "pass" in (pf.get("status", "")):
            continue
        if worst not in sev_filter:
            continue
        fc = pf.get("finding_counts", {})
        rows.append({
            "module":   mod["name"],
            "domain":   mod["domain"],
            "worst":    worst,
            "critical": fc.get("critical", 0),
            "high":     fc.get("high", 0),
            "medium":   fc.get("medium", 0),
            "low":      fc.get("low", 0),
            "issues":   pf.get("issue_counts_total", 0),
            "status":   pf.get("status", ""),
        })

    rows.sort(key=lambda r: (_sev_order.get(r["worst"], 99), r["module"]))

    max_name = max((len(r["module"]) for r in rows), default=35)
    name_w   = min(max_name, 55)

    _sev_color = {
        "critical": _c_err,
        "high":     _c_warn,
        "medium":   lambda s: s,
        "low":      _c_dim,
        "none":     _c_dim,
    }

    header = (
        f"  {'Worst':<10}  {'Crit':>4}  {'High':>4}  {'Med':>4}  {'Low':>4}  {'Issues':>6}"
        f"  {'Module':<{name_w}}  Domain"
    )
    sep = "─" * len(header)

    lines: list[str] = [
        "",
        _c_bold("AVM Provider Currency Findings"),
        f"  Severity filter: {', '.join(sorted(sev_filter, key=lambda s: _sev_order.get(s, 99)))}",
        f"  {len(rows)} module(s) with findings",
        sep, header, sep,
    ]

    current_worst = ""
    for row in rows:
        worst = row["worst"]
        if worst != current_worst:
            current_worst = worst
            lines.append(f"  {_c_bold(worst.upper())}")
        color = _sev_color.get(worst, lambda s: s)
        name  = row["module"][:name_w]
        lines.append(
            f"  {color(f'{worst:<10}')}  {row['critical']:>4}  {row['high']:>4}"
            f"  {row['medium']:>4}  {row['low']:>4}  {row['issues']:>6}"
            f"  {name:<{name_w}}  {row['domain']}"
        )

    lines += [sep, f"  Total: {len(rows)} module(s) with {'/'.join(sorted(sev_filter))} findings"]

    text = "\n".join(lines) + "\n"
    _write_output(text, output)


# ---------------------------------------------------------------------------
# Subcommand: --json
# ---------------------------------------------------------------------------

def cmd_json(modules: list[dict], output: str | None = None) -> None:
    """Export all modules to a single JSON file."""
    out_path = output or os.path.join(REPO_ROOT, "data", "catalog.json")

    def _parse_module(mod: dict) -> dict:
        """Strip raw content and build a clean JSON-serialisable dict."""
        score, dim_statuses = compute_score(mod["analysis"])
        stale = _staleness_days(mod["analysis"])
        return {
            "name":         mod["name"],
            "domain":       mod["domain"],
            "type":         mod["type"],
            "status":       mod["status"],
            "display_name": mod["display_name"],
            "score":        score,
            "stale_days":   stale,
            "analysis":     {
                dim: {
                    "status":     data.get("status"),
                    "checked_at": data.get("checked_at"),
                }
                for dim, data in mod["analysis"].items()
            },
            "open_issues": len([i for i in mod["issues"] if i.get("status", "open") == "open"]),
        }

    catalog: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total":        len(modules),
        "modules":      [_parse_module(m) for m in modules],
    }

    text = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    if output == "-":
        _write_output(text, None)
    else:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"  Wrote {len(modules)} modules to {os.path.relpath(out_path, REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Output helper
# ---------------------------------------------------------------------------

def _write_output(text: str, output: str | None) -> None:
    if output and output != "-":
        with open(output, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"  Output written to {output}")
    else:
        sys.stdout.write(text)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> dict:
    args: dict = {
        "subcommand":      None,
        "domains":         [],
        "types":           [],
        "output":          None,
        "min_score":       0.0,
        "filter_severity": [],
    }

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("--scores", "--issues", "--json", "--provider-findings"):
            args["subcommand"] = arg.lstrip("-")
            i += 1
        elif arg in ("--domain", "--domains") and i + 1 < len(sys.argv):
            val = sys.argv[i + 1]
            args["domains"] = [] if val.lower() == "all" else [v.strip() for v in val.split(",") if v.strip()]
            i += 2
        elif arg in ("--type", "--types") and i + 1 < len(sys.argv):
            val = sys.argv[i + 1]
            args["types"] = [] if val.lower() == "all" else [v.strip() for v in val.split(",") if v.strip()]
            i += 2
        elif arg == "--output" and i + 1 < len(sys.argv):
            args["output"] = sys.argv[i + 1]
            i += 2
        elif arg == "--min-score" and i + 1 < len(sys.argv):
            try:
                args["min_score"] = float(sys.argv[i + 1])
            except ValueError:
                pass
            i += 2
        elif arg == "--severity" and i + 1 < len(sys.argv):
            val = sys.argv[i + 1]
            args["filter_severity"] = [v.strip().lower() for v in val.split(",") if v.strip()]
            i += 2
        else:
            i += 1

    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    if args["subcommand"] is None:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    filter_domains = args["domains"] or None
    filter_types   = args["types"] or None

    modules = load_modules(filter_domains=filter_domains, filter_types=filter_types)
    if not modules:
        print("No modules found — check --domain/--type filters.", file=sys.stderr)
        sys.exit(1)

    sub = args["subcommand"]

    if sub == "scores":
        cmd_scores(modules, min_score=args["min_score"], output=args["output"])
    elif sub == "issues":
        cmd_issues(
            modules,
            filter_severity=args["filter_severity"] or None,
            output=args["output"],
        )
    elif sub == "json":
        cmd_json(modules, output=args["output"])
    elif sub == "provider-findings":
        cmd_provider_findings(
            modules,
            filter_severity=args["filter_severity"] or None,
            output=args["output"],
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
