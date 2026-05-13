#!/usr/bin/env python3
"""fetch_provider_changes.py — Fetch Terraform provider changelog and write findings to resource stubs.

Phase 2 of Provider Change Intelligence.

For each provider, fetches GitHub Releases, parses each release body to extract
resource type mentions and their criticality, then writes findings into the
provider_updates.findings block of each matching stub in:

    data/resources/     azurerm_virtual_network.yaml
    data/datasources/   azurerm_subnet.yaml
    data/functions/     ...
    data/ephemerals/    ...

Criticality is determined by the release body section heading:
    Breaking Changes / Security → critical
    Bug Fixes / Fixes           → high
    Enhancements                → medium
    New Resources / New Data Sources / Deprecations → low/medium

Usage:
    python3 scripts/fetch_provider_changes.py [options]
    ./avm.sh providers [options]    # operator alias

Options:
    --provider LIST     Comma-separated provider names (default: azurerm,azapi)
    --since VERSION     Only include releases >= this version (e.g., 4.0.0)
    --max-releases N    Maximum releases to fetch per provider (default: 100)
    --dry-run           Print summary without modifying files
    --force             Re-fetch even if last_checked is within 24 h

Environment:
    GITHUB_TOKEN        GitHub personal access token (recommended; provides
                        5 000 req/hr vs 60 req/hr unauthenticated)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

import yaml  # PyYAML — available in this repo's Python environment

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(SCRIPT_DIR)
DATA_DIR   = os.path.join(REPO_ROOT, "data")

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

# Maps provider short name → GitHub repo coordinates
_PROVIDERS: dict[str, dict[str, str]] = {
    "azurerm": {
        "owner": "hashicorp",
        "repo":  "terraform-provider-azurerm",
    },
    "azapi": {
        "owner": "Azure",
        "repo":  "terraform-provider-azapi",
    },
    "azuread": {
        "owner": "hashicorp",
        "repo":  "terraform-provider-azuread",
    },
}

# Stub directories to scan (relative to DATA_DIR)
_STUB_DIRS: list[str] = ["resources", "datasources", "functions", "ephemerals"]

# ---------------------------------------------------------------------------
# Section → (criticality, finding_type) mapping
# Entries are matched as substrings (case-insensitive) against the heading.
# First match wins — more specific entries should appear first.
# ---------------------------------------------------------------------------
_SECTION_MAP: list[tuple[str, str, str]] = [
    # (heading_keyword,    criticality,  finding_type)
    ("breaking change",    "critical",   "breaking_change"),
    ("breaking-change",    "critical",   "breaking_change"),
    ("security",           "critical",   "security"),
    ("cve",                "critical",   "security"),
    ("vulnerability",      "critical",   "security"),
    ("bug fix",            "high",       "bug_fix"),
    ("bug-fix",            "high",       "bug_fix"),
    ("bugfix",             "high",       "bug_fix"),
    ("fix",                "high",       "bug_fix"),
    ("regression",         "high",       "bug_fix"),
    ("crash",              "high",       "bug_fix"),
    ("panic",              "high",       "bug_fix"),
    ("deprecat",           "medium",     "deprecated"),
    ("behaviour change",   "medium",     "enhancement"),
    ("behavior change",    "medium",     "enhancement"),
    ("enhancement",        "medium",     "enhancement"),
    ("improvement",        "medium",     "enhancement"),
    ("feature",            "medium",     "enhancement"),
    ("upgrade guide",      "medium",     "enhancement"),
    ("new resource",       "low",        "new_feature"),
    ("new data source",    "low",        "new_feature"),
    ("new datasource",     "low",        "new_feature"),
    ("documentation",      "low",        "documentation"),
    ("note",               "low",        "documentation"),
]

# Regex to find resource type names in backticks: `azurerm_virtual_network`
# Captures the full name; requires at least one underscore.
_RESOURCE_TYPE_RE = re.compile(
    r'`([a-z][a-z0-9]*_[a-z][a-z0-9_]*)`'
)

# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string to a sortable integer tuple.

    Strips 'v' prefix and pre-release / build-metadata suffixes.
    Examples: 'v4.15.0' → (4, 15, 0); '4.0.0-beta.1' → (4, 0, 0).
    """
    v = v.lstrip("v").split("-")[0].split("+")[0]
    parts: list[int] = []
    for segment in v.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            break  # stop at non-numeric segment
    return tuple(parts)


def _version_gte(a: str, b: str) -> bool:
    """Return True if version string a >= version string b."""
    return _parse_version(a) >= _parse_version(b)


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def _github_get(url: str, token: str | None) -> Any:
    """Make an authenticated GET request to the GitHub API and return parsed JSON.

    Raises RuntimeError for HTTP errors (404, 403/rate-limit, etc.).
    """
    headers = {
        "Accept":     "application/vnd.github.v3+json",
        "User-Agent": "avm-metadata-fetch-provider-changes/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 403 and "rate limit" in body.lower():
            raise RuntimeError(
                "GitHub API rate limit exceeded. "
                "Set the GITHUB_TOKEN environment variable for higher limits (5 000 req/hr)."
            )
        if e.code == 404:
            raise RuntimeError(f"GitHub API 404 Not Found: {url}")
        raise RuntimeError(f"GitHub API error {e.code} ({e.reason}): {body[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching {url}: {e.reason}")


def _fetch_releases(
    owner:        str,
    repo:         str,
    since:        str | None,
    token:        str | None,
    max_releases: int,
) -> list[dict]:
    """Fetch published (non-draft, non-prerelease) releases from GitHub, newest first.

    Stops early when a release version falls below *since* (if provided).
    Returns at most *max_releases* entries.
    """
    releases: list[dict] = []
    page = 1
    per_page = 100  # GitHub's maximum

    while len(releases) < max_releases:
        url = (
            f"https://api.github.com/repos/{owner}/{repo}/releases"
            f"?per_page={per_page}&page={page}"
        )
        batch: list[dict] = _github_get(url, token)

        if not batch:
            break

        for release in batch:
            if release.get("draft") or release.get("prerelease"):
                continue  # skip drafts and pre-releases

            tag = release.get("tag_name", "")
            if since and not _version_gte(tag, since):
                return releases  # past the requested lower bound — stop

            releases.append(release)
            if len(releases) >= max_releases:
                return releases

        if len(batch) < per_page:
            break  # last page reached
        page += 1

    return releases


# ---------------------------------------------------------------------------
# Release body parsing
# ---------------------------------------------------------------------------


def _section_from_heading(heading: str) -> tuple[str, str]:
    """Map a section heading string to (criticality, finding_type).

    Case-insensitive substring match; first match in _SECTION_MAP wins.
    Returns ('low', 'documentation') as default fallback.
    """
    h = heading.lower()
    for keyword, criticality, ftype in _SECTION_MAP:
        if keyword in h:
            return criticality, ftype
    return "low", "documentation"


def _extract_findings_from_release(
    body:    str,
    version: str,
    url:     str,
) -> dict[str, list[dict]]:
    """Parse a release body (markdown) and return findings grouped by resource type.

    Handles both heading formats used by Terraform providers:
    - Modern:  ## Section Heading
    - Legacy:  **SECTION HEADING:**
    - Sub:     ### Sub-heading

    Returns a dict of resource_type → list of finding dicts.
    """
    findings: dict[str, list[dict]] = {}
    current_criticality = "low"
    current_type = "documentation"

    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Detect modern markdown headings: ## or ###
        heading_match = re.match(r'^#{1,3}\s+(.+?)(?:\s*#+)?$', stripped)
        if heading_match:
            current_criticality, current_type = _section_from_heading(
                heading_match.group(1).strip()
            )
            continue

        # Detect legacy bold headings: **HEADING:** or **HEADING**
        bold_match = re.match(r'^\*\*([^*]+?)\*\*\s*:?\s*$', stripped)
        if bold_match:
            current_criticality, current_type = _section_from_heading(
                bold_match.group(1).strip()
            )
            continue

        # Find resource type mentions (require backtick quoting)
        matches = _RESOURCE_TYPE_RE.findall(stripped)
        if not matches:
            continue

        # Build a clean summary: strip bullet chars, remove GitHub issue links
        summary = re.sub(r'\s*\[#\d+\]\(https?://[^\)]*\)', '', stripped)
        summary = summary.lstrip("*-–•· ").strip()
        if len(summary) > 200:
            summary = summary[:197] + "..."

        for resource_type in matches:
            if resource_type not in findings:
                findings[resource_type] = []
            findings[resource_type].append({
                "version":     version,
                "criticality": current_criticality,
                "type":        current_type,
                "summary":     summary,
                "url":         url,
            })

    return findings


# ---------------------------------------------------------------------------
# Stub loading and writing
# ---------------------------------------------------------------------------


def _load_stubs(providers: list[str]) -> dict[str, tuple[str, dict]]:
    """Load all resource stubs for the given providers.

    Scans _STUB_DIRS and reads each .yaml. Skips invalid files with a warning.

    Returns a dict of resource_type → (file_path, parsed_yaml_dict).
    """
    stubs: dict[str, tuple[str, dict]] = {}

    for subdir in _STUB_DIRS:
        stub_dir = os.path.join(DATA_DIR, subdir)
        if not os.path.isdir(stub_dir):
            continue
        for fname in sorted(os.listdir(stub_dir)):
            if not fname.endswith(".yaml"):
                continue
            fpath = os.path.join(stub_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict) or "resource" not in data:
                    continue
                provider = data["resource"].get("provider", "")
                if provider not in providers:
                    continue
                resource_type = data["resource"].get("type", "")
                if resource_type:
                    stubs[resource_type] = (fpath, data)
            except Exception as exc:  # noqa: BLE001
                print(
                    f"  [warn] Skipping invalid stub {os.path.relpath(fpath, REPO_ROOT)}: {exc}",
                    file=sys.stderr,
                )

    return stubs


def _is_recently_checked(stub_data: dict, max_age_hours: int = 24) -> bool:
    """Return True if provider_updates.last_checked is within max_age_hours."""
    try:
        last_checked = stub_data.get("provider_updates", {}).get("last_checked")
        if last_checked is None:
            return False
        ts = datetime.fromisoformat(str(last_checked).rstrip("Z")).replace(
            tzinfo=timezone.utc
        )
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        return age_hours < max_age_hours
    except Exception:  # noqa: BLE001
        return False


def _format_provider_updates_block(findings: list[dict], now: str) -> str:
    """Render the provider_updates: YAML block as a plain string.

    Findings are written as actual YAML entries. When findings is empty,
    the shape comment is preserved for documentation.
    """
    lines: list[str] = [
        "provider_updates:",
        f'  last_checked: "{now}"',
    ]

    if findings:
        lines.append("  findings:")
        for f in findings:
            # Escape double-quotes in string values by replacing with single-quotes
            summary_safe = f["summary"].replace('"', "'")
            url_safe     = f["url"].replace('"', "'")
            lines += [
                f'  - version: "{f["version"]}"',
                f'    criticality: {f["criticality"]}',
                f'    type: {f["type"]}',
                f'    summary: "{summary_safe}"',
                f'    url: "{url_safe}"',
            ]
    else:
        lines += [
            "  findings: []",
            "  # finding shape:",
            "  #   - version: \"4.15.0\"",
            "  #     criticality: high   # critical | high | medium | low",
            "  #     type: bug_fix       # bug_fix | security | enhancement | breaking_change | new_feature | deprecated",
            "  #     summary: \"...\"",
            "  #     url: \"...\"",
        ]

    return "\n".join(lines)


def _replace_yaml_section(content: str, key: str, new_block: str) -> str:
    """Replace a top-level YAML key block with new_block in a YAML text string.

    Uses a line-by-line state machine: the section starts at the line matching
    `key:` and ends at the next line that begins with a top-level YAML key
    (letter/underscore at column 0 followed by `:`).

    This preserves all content outside the target section — including comments
    and hand-maintained values in other sections (e.g., enrichment.notes).

    new_block should NOT end with a newline; a blank separator line is added
    automatically between the new block and the following section.
    """
    lines = content.split("\n")
    start_idx: int | None = None
    end_idx: int = len(lines)

    # Locate start of the target section
    for i, line in enumerate(lines):
        if line.rstrip() == f"{key}:" or line.startswith(f"{key}: "):
            start_idx = i
            break

    if start_idx is None:
        return content  # key not found — return unchanged

    # Locate end: first subsequent line that is a top-level YAML key
    for i in range(start_idx + 1, len(lines)):
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', lines[i]):
            end_idx = i
            break

    prefix            = lines[:start_idx]
    suffix            = lines[end_idx:]
    new_block_lines   = new_block.split("\n")

    # Insert a single blank separator line between new block and next section
    return "\n".join(prefix + new_block_lines + [""] + suffix)


def _update_stub(fpath: str, findings: list[dict], now: str, dry_run: bool) -> bool:
    """Write findings into a stub file's provider_updates: section.

    Returns True if the file was (or would be) modified.
    """
    with open(fpath, "r", encoding="utf-8") as fh:
        original = fh.read()

    new_block   = _format_provider_updates_block(findings, now)
    new_content = _replace_yaml_section(original, "provider_updates", new_block)

    if new_content == original:
        return False

    if not dry_run:
        # Atomic write: write to temp then rename to avoid partial file on error
        import tempfile
        tmp_dir = os.path.dirname(fpath)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".yaml",
            dir=tmp_dir, delete=False,
        ) as tmp:
            tmp.write(new_content)
            tmp_path = tmp.name
        os.replace(tmp_path, fpath)  # atomic on POSIX

    return True


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


def cmd_providers(
    providers:    list[str],
    since:        str | None,
    dry_run:      bool,
    force:        bool,
    max_releases: int,
    token:        str | None,
) -> None:
    """Fetch provider releases and write findings into resource stubs."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Validate requested providers
    unknown = [p for p in providers if p not in _PROVIDERS]
    if unknown:
        print(f"[error] Unknown provider(s): {', '.join(unknown)}. "
              f"Available: {', '.join(_PROVIDERS)}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading stubs for: {', '.join(providers)}")
    stubs = _load_stubs(providers)
    print(f"  {len(stubs)} stub(s) loaded")

    total_stubs_updated = 0
    total_findings      = 0

    for provider_name in providers:
        pinfo = _PROVIDERS[provider_name]
        owner, repo = pinfo["owner"], pinfo["repo"]

        label = f"{provider_name} ({owner}/{repo})"
        suffix = f"  --since {since}" if since else "  (last {max_releases} releases)"
        print(f"\nFetching releases: {label}{suffix}")

        try:
            releases = _fetch_releases(owner, repo, since, token, max_releases)
        except RuntimeError as exc:
            print(f"  [error] {exc}", file=sys.stderr)
            continue

        print(f"  Fetched {len(releases)} release(s)")
        if not releases:
            continue

        # Aggregate all findings by resource type across all releases
        all_findings: dict[str, list[dict]] = {}
        for release in releases:
            body    = release.get("body") or ""
            version = release.get("tag_name", "").lstrip("v")
            url     = release.get("html_url", "")
            for rtype, items in _extract_findings_from_release(body, version, url).items():
                all_findings.setdefault(rtype, []).extend(items)

        types_with_findings = sum(1 for v in all_findings.values() if v)
        print(f"  {types_with_findings} resource type(s) mentioned in release notes")

        # Write findings into matching stubs
        provider_updated = 0
        provider_findings = 0

        for resource_type, (fpath, stub_data) in stubs.items():
            if stub_data["resource"].get("provider") != provider_name:
                continue
            if not force and _is_recently_checked(stub_data, max_age_hours=24):
                continue

            findings_for_type = all_findings.get(resource_type, [])
            rel_path = os.path.relpath(fpath, REPO_ROOT)

            if dry_run:
                n = len(findings_for_type)
                if n:
                    print(f"  [dry-run] {n} finding(s) → {rel_path}")
                    provider_updated  += 1
                    provider_findings += n
                continue

            modified = _update_stub(fpath, findings_for_type, now, dry_run=False)
            if modified:
                provider_updated  += 1
                provider_findings += len(findings_for_type)

        if dry_run:
            print(f"  [dry-run] Would update {provider_updated} stub(s), "
                  f"{provider_findings} finding(s)")
        else:
            print(f"  Updated {provider_updated} stub(s) with "
                  f"{provider_findings} finding(s)")

        total_stubs_updated += provider_updated
        total_findings      += provider_findings

    action = "[dry-run] Would write" if dry_run else "Done. Wrote"
    print(f"\n{action} {total_findings} finding(s) across {total_stubs_updated} stub(s).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch Terraform provider changelog and write findings to resource stubs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--provider", default="azurerm,azapi",
        help="Comma-separated provider names (default: azurerm,azapi)",
    )
    p.add_argument(
        "--since", default=None,
        metavar="VERSION",
        help="Only include releases >= this version (e.g., 4.0.0)",
    )
    p.add_argument(
        "--max-releases", type=int, default=100,
        metavar="N",
        help="Maximum releases to fetch per provider (default: 100)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be written without modifying files",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Re-fetch even if last_checked is within 24 h",
    )
    return p.parse_args()


def main() -> None:
    args  = _parse_args()
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        print(
            "[warn] GITHUB_TOKEN not set — using unauthenticated API (60 req/hr limit).\n"
            "       Set GITHUB_TOKEN for 5 000 req/hr.",
            file=sys.stderr,
        )

    providers = [p.strip() for p in args.provider.split(",") if p.strip()]
    cmd_providers(
        providers    = providers,
        since        = args.since,
        dry_run      = args.dry_run,
        force        = args.force,
        max_releases = args.max_releases,
        token        = token,
    )


if __name__ == "__main__":
    main()
