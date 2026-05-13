#!/usr/bin/env python3
"""harvest_module_issues.py — Harvest open GitHub issues from AVM module repos.

For each module in data/modules/, fetches open issues from the upstream GitHub
repository (catalog.repo_url) and writes a module_issues: block into the
module YAML file.

This is row #2 in the AVM issues architecture:

  1. enrichment.known_issues   hand-typed by operator        avm report --issues
  2. module_issues              this script                   avm harvest
  3. provider_issues            fetch_provider_changes.py     avm providers --mode issues
  4. provider_updates           fetch_provider_changes.py     avm providers

Usage:
    python3 scripts/harvest_module_issues.py [options]
    ./avm.sh harvest [options]

Options:
    --domains DOMAIN[,…]     Filter by domain slug (e.g. networking,compute)
    --types TYPE[,…]         Filter by module type: res, ptn, utl
    --modules NAME[,…]       Filter by short module name (e.g. avm-res-network-virtualnetwork)
    --labels LABEL[,…]       Issue label filter; keep issues with ANY of these labels
                             (default: bug,enhancement,breaking-change,help wanted,good first issue)
    --max-issues N           Maximum issues to store per module (default: 50)
    --since Nd               Skip modules harvested within N days (default: 1)
    --force                  Re-harvest even if last_harvested is fresh
    --dry-run                Print summary without modifying files

Environment:
    GITHUB_TOKEN             GitHub personal access token (recommended; 5 000 req/hr
                             vs 60 req/hr unauthenticated)
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(SCRIPT_DIR)
MODULES_DIR = os.path.join(REPO_ROOT, "data", "modules")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_LABELS: list[str] = [
    "bug",
    "enhancement",
    "breaking-change",
    "help wanted",
    "good first issue",
]
_DEFAULT_MAX_ISSUES   = 50
_DEFAULT_SINCE_DAYS   = 1       # skip modules harvested within this many days


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _github_get(url: str, token: str | None) -> Any:
    """Make an authenticated GET request to the GitHub API and return parsed JSON.

    Raises RuntimeError for HTTP errors (404, 403/rate-limit, etc.).
    """
    headers = {
        "Accept":     "application/vnd.github.v3+json",
        "User-Agent": "avm-metadata-harvest-module-issues/1.0",
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
                "Set the GITHUB_TOKEN environment variable for higher limits "
                "(5 000 req/hr)."
            )
        if e.code == 404:
            raise RuntimeError(f"GitHub API 404 Not Found: {url}")
        raise RuntimeError(f"GitHub API error {e.code} ({e.reason}): {body[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching {url}: {e.reason}")


def _fetch_issues(
    owner:      str,
    repo:       str,
    token:      str | None,
    max_issues: int,
) -> list[dict]:
    """Bulk-fetch all open (non-PR) issues from a GitHub repository, newest first.

    Returns at most max_issues entries. Does NOT filter by label server-side —
    caller filters client-side to support OR logic across labels.
    """
    issues:  list[dict] = []
    page     = 1
    per_page = 100  # GitHub's maximum

    while len(issues) < max_issues:
        url = (
            f"https://api.github.com/repos/{owner}/{repo}/issues"
            f"?state=open&per_page={per_page}&page={page}"
        )
        batch: list[dict] = _github_get(url, token)

        if not batch:
            break

        for item in batch:
            # GitHub issues endpoint returns PRs too — skip them
            if "pull_request" in item:
                continue
            issues.append(item)
            if len(issues) >= max_issues:
                return issues

        if len(batch) < per_page:
            break  # reached last page
        page += 1

    return issues


# ---------------------------------------------------------------------------
# YAML section helpers
# ---------------------------------------------------------------------------

def _upsert_yaml_section(content: str, key: str, new_block: str) -> str:
    """Replace an existing top-level YAML key block, or insert before enrichment:.

    Uses a line-by-line state machine:
    - If `key:` already exists, replaces it in-place.
    - If not found, inserts before the `enrichment:` section.
    - If neither exists, appends at the end.

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

    if start_idx is not None:
        # Key found — locate end (next top-level key at column 0)
        for i in range(start_idx + 1, len(lines)):
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', lines[i]):
                end_idx = i
                break

        prefix          = lines[:start_idx]
        suffix          = lines[end_idx:]
        new_block_lines = new_block.split("\n")
        return "\n".join(prefix + new_block_lines + [""] + suffix)

    # Key not found — insert before enrichment:
    for i, line in enumerate(lines):
        if line.rstrip() == "enrichment:" or line.startswith("enrichment: "):
            prefix          = lines[:i]
            suffix          = lines[i:]
            new_block_lines = new_block.split("\n")
            return "\n".join(prefix + new_block_lines + [""] + suffix)

    # No enrichment: either — append at end (strip trailing blank lines first)
    trimmed = content.rstrip("\n")
    return trimmed + "\n\n" + new_block + "\n"


# ---------------------------------------------------------------------------
# Freshness check
# ---------------------------------------------------------------------------

def _is_freshly_harvested(content: str, max_age_hours: float) -> bool:
    """Return True if module_issues.last_harvested is within max_age_hours."""
    in_block = False
    for line in content.splitlines():
        if line.rstrip() == "module_issues:":
            in_block = True
            continue
        if in_block:
            # Top-level key signals end of block
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', line):
                break
            m = re.match(r'^\s+last_harvested:\s+"?([^"\s]+)"?', line)
            if m:
                raw = m.group(1).rstrip("Z")
                try:
                    ts = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
                    age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                    return age_hours < max_age_hours
                except ValueError:
                    return False
    return False


# ---------------------------------------------------------------------------
# Module discovery
# ---------------------------------------------------------------------------

def _extract_catalog_fields(content: str) -> dict[str, str]:
    """Extract name, domain, type, status, repo_url from the CATALOG block."""
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
        m = re.match(
            r'^  (name|domain|type|status|repo_url):\s+"?([^"#\n]+)"?', line
        )
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"')
    return fields


def _discover_modules(
    filter_domains: set[str],
    filter_types:   set[str],
    filter_names:   set[str],
) -> list[dict]:
    """Discover module YAML files, returning a list of module metadata dicts."""
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
            name = fname[:-5]
            if filter_names and name not in filter_names:
                continue
            filepath = os.path.join(type_dir, fname)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except OSError as exc:
                print(f"  [warn] Cannot read {filepath}: {exc}", file=sys.stderr)
                continue

            catalog = _extract_catalog_fields(content)
            domain  = catalog.get("domain", "")
            if filter_domains and domain not in filter_domains:
                continue

            repo_url = catalog.get("repo_url", "")
            modules.append({
                "name":     name,
                "domain":   domain,
                "type":     mod_type,
                "repo_url": repo_url,
                "filepath": filepath,
                "content":  content,
            })
    return modules


# ---------------------------------------------------------------------------
# GitHub org/repo extraction
# ---------------------------------------------------------------------------

def _parse_github_coords(repo_url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL like https://github.com/Azure/repo-name.

    Returns None if the URL is not a valid GitHub URL.
    """
    m = re.match(
        r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', repo_url.strip()
    )
    if not m:
        return None
    return m.group(1), m.group(2)


# ---------------------------------------------------------------------------
# Label filtering
# ---------------------------------------------------------------------------

def _matches_labels(issue: dict, target_labels: set[str]) -> bool:
    """Return True if the issue has at least one label from target_labels.

    If target_labels is empty, all issues are accepted.
    """
    if not target_labels:
        return True
    issue_labels = {lb["name"].lower() for lb in issue.get("labels", [])}
    return bool(issue_labels & {lb.lower() for lb in target_labels})


# ---------------------------------------------------------------------------
# YAML block formatter
# ---------------------------------------------------------------------------

def _format_module_issues_block(issues: list[dict], now: str) -> str:
    """Render the module_issues: YAML block as a plain string.

    Issues list should already be pre-filtered and limited to max_issues.
    When issues is empty, a schema comment is preserved for documentation.
    """
    lines: list[str] = [
        "module_issues:",
        f'  last_harvested: "{now}"',
        f"  open_count: {len(issues)}",
    ]

    if issues:
        lines.append("  issues:")
        for item in issues:
            title_safe  = item.get("title", "").replace('"', "'")
            url_safe    = item.get("html_url", item.get("url", "")).replace('"', "'")
            label_names = [lb["name"] for lb in item.get("labels", [])]
            labels_yaml = json.dumps(label_names)
            created     = (item.get("created_at") or "")[:10]
            comments    = item.get("comments", 0)
            lines += [
                f'  - number: {item["number"]}',
                f'    title: "{title_safe}"',
                f"    labels: {labels_yaml}",
                f'    url: "{url_safe}"',
                f'    created_at: "{created}"',
                f"    comments: {comments}",
            ]
    else:
        lines += [
            "  issues: []",
            "  # issue shape:",
            "  #   - number: 312",
            '  #     title: "..."',
            "  #     labels: [bug, help wanted]",
            '  #     url: "..."',
            '  #     created_at: "2026-03-21"',
            "  #     comments: 4",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File update
# ---------------------------------------------------------------------------

def _update_module_file(
    fpath:   str,
    issues:  list[dict],
    now:     str,
    dry_run: bool,
) -> bool:
    """Write or update the module_issues: section in fpath.

    Returns True if the file was (or would be) modified.
    """
    with open(fpath, "r", encoding="utf-8") as fh:
        original = fh.read()

    new_block   = _format_module_issues_block(issues, now)
    new_content = _upsert_yaml_section(original, "module_issues", new_block)

    if new_content == original:
        return False

    if not dry_run:
        with open(fpath, "w", encoding="utf-8") as fh:
            fh.write(new_content)

    return True


# ---------------------------------------------------------------------------
# Main harvest loop
# ---------------------------------------------------------------------------

def harvest(
    filter_domains: set[str],
    filter_types:   set[str],
    filter_names:   set[str],
    target_labels:  set[str],
    max_issues:     int,
    max_age_hours:  float,
    force:          bool,
    dry_run:        bool,
    token:          str | None,
) -> None:
    """Discover modules and harvest GitHub issues into module_issues: blocks."""
    modules = _discover_modules(filter_domains, filter_types, filter_names)
    if not modules:
        print("No modules matched the given filters.", file=sys.stderr)
        return

    total   = len(modules)
    updated = 0
    skipped = 0
    failed  = 0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"  Harvesting {total} module(s)…")

    for i, mod in enumerate(modules, 1):
        name    = mod["name"]
        content = mod["content"]
        fpath   = mod["filepath"]

        prefix = f"  [{i:>3}/{total}] {mod['type']}/{name}"

        # Freshness check
        if not force and _is_freshly_harvested(content, max_age_hours):
            print(f"{prefix}  (fresh — skipped)")
            skipped += 1
            continue

        # Parse GitHub coordinates
        coords = _parse_github_coords(mod["repo_url"])
        if not coords:
            print(
                f"{prefix}  [warn] cannot parse repo_url: {mod['repo_url']!r}",
                file=sys.stderr,
            )
            failed += 1
            continue

        owner, repo = coords

        try:
            raw_issues = _fetch_issues(owner, repo, token, max_issues * 4)
        except RuntimeError as exc:
            print(f"{prefix}  [error] {exc}", file=sys.stderr)
            failed += 1
            continue

        # Client-side label filter
        filtered = [iss for iss in raw_issues if _matches_labels(iss, target_labels)]
        filtered = filtered[:max_issues]

        changed = _update_module_file(fpath, filtered, now, dry_run)

        if dry_run:
            action = "would-update"
        elif changed:
            action = "updated"
        else:
            action = "unchanged"

        print(f"{prefix}  {action}({len(filtered)} issues)")
        if changed:
            updated += 1

    print("─" * 60)
    if dry_run:
        print(
            f"Dry run — would update: {updated}, skipped (fresh): {skipped}, "
            f"failed: {failed}"
        )
    else:
        print(
            f"Done — updated: {updated}, skipped (fresh): {skipped}, "
            f"failed: {failed}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="harvest_module_issues",
        description="Harvest open GitHub issues from AVM module repos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--domains",
        metavar="DOMAIN[,…]",
        help="Filter by domain slug (comma-separated)",
    )
    parser.add_argument(
        "--types",
        metavar="TYPE[,…]",
        help="Filter by module type: res, ptn, utl (comma-separated)",
    )
    parser.add_argument(
        "--modules",
        metavar="NAME[,…]",
        help="Filter by short module name (comma-separated)",
    )
    parser.add_argument(
        "--labels",
        metavar="LABEL[,…]",
        default=",".join(_DEFAULT_LABELS),
        help=(
            "Issue label filter — keep issues with ANY of these labels "
            f"(default: {','.join(_DEFAULT_LABELS)})"
        ),
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=_DEFAULT_MAX_ISSUES,
        metavar="N",
        help=f"Maximum issues to store per module (default: {_DEFAULT_MAX_ISSUES})",
    )
    parser.add_argument(
        "--since",
        default=f"{_DEFAULT_SINCE_DAYS}d",
        metavar="Nd",
        help=(
            "Skip modules harvested within N days "
            f"(default: {_DEFAULT_SINCE_DAYS}d)"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-harvest even if last_harvested is within the --since window",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without modifying files",
    )
    return parser.parse_args()


def _parse_days(value: str) -> float:
    """Parse a 'Nd' string into a float number of hours.

    Accepts: '1d', '7d', '30d', or a plain integer (treated as days).
    """
    value = value.strip().lower()
    if value.endswith("d"):
        days_str = value[:-1]
    else:
        days_str = value
    try:
        return float(days_str) * 24.0
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid --since value {value!r}; expected format: Nd (e.g. 1d, 7d)"
        ) from exc


def main() -> None:
    args = _parse_args()

    if args.dry_run:
        print("(dry-run mode — no files will be modified)")

    filter_domains = (
        {d.strip() for d in args.domains.split(",") if d.strip()}
        if args.domains
        else set()
    )
    filter_types = (
        {t.strip() for t in args.types.split(",") if t.strip()}
        if args.types
        else set()
    )
    filter_names = (
        {n.strip() for n in args.modules.split(",") if n.strip()}
        if args.modules
        else set()
    )
    target_labels = {lb.strip() for lb in args.labels.split(",") if lb.strip()}
    max_age_hours = _parse_days(args.since)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print(
            "  [warn] GITHUB_TOKEN not set — unauthenticated requests "
            "(60 req/hr limit).",
            file=sys.stderr,
        )

    harvest(
        filter_domains = filter_domains,
        filter_types   = filter_types,
        filter_names   = filter_names,
        target_labels  = target_labels,
        max_issues     = args.max_issues,
        max_age_hours  = max_age_hours,
        force          = args.force,
        dry_run        = args.dry_run,
        token          = token,
    )


if __name__ == "__main__":
    main()
