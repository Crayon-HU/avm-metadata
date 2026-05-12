#!/usr/bin/env python3
"""scrape_modules.py — Scrape each AVM module repo and populate the 'scraped' block
in data/modules/{type}/{name}.yaml.

For res/utl modules: populates scraped.terraform_constraints + scraped.resources_managed
For ptn modules:     populates scraped.terraform_constraints + scraped.modules_called

The scraped block sits between # BEGIN SCRAPED and # END SCRAPED markers, separate from
the catalog section (managed by sync_catalog.py) and the enrichment section (hand-maintained).
Neither sync nor scrape will touch each other's sections.

Usage:
    python3 scripts/scrape_modules.py [options]
    ./avm.sh scrape [options]

Options:
    --dry-run          Show planned changes without writing files
    --force            Re-scrape even if scraped_at is newer than --max-age
    --module NAME      Scrape a single module by name (e.g. avm-res-network-virtualnetwork)
    --max-age DAYS     Skip modules scraped within this many days (default: 7)

Environment:
    GITHUB_TOKEN       Optional. Increases GitHub API rate limit from 60 to 5000 req/hr.
                       Set via: export GITHUB_TOKEN=ghp_...
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants — must match sync_catalog.py
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
MODULES_DIR = os.path.join(REPO_ROOT, "data", "modules")

BEGIN_MARKER         = "# BEGIN CATALOG"
END_MARKER           = "# END CATALOG"
SCRAPED_BEGIN_MARKER = "# BEGIN SCRAPED"
SCRAPED_END_MARKER   = "# END SCRAPED"

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"
GITHUB_ORG = "Azure"

DEFAULT_MAX_AGE_DAYS = 7

# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def _github_headers() -> dict:
    """Build GitHub API request headers; include auth token if GITHUB_TOKEN is set."""
    headers = {
        "Accept":     "application/vnd.github.v3+json",
        "User-Agent": "avm-metadata-scraper/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_url(url: str, use_api_headers: bool = False, retries: int = 2) -> bytes | None:
    """Fetch a URL, returning bytes or None on 404. Retries on transient errors."""
    headers = _github_headers() if use_api_headers else {"User-Agent": "avm-metadata-scraper/1.0"}
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 403:
                raise RateLimitError(
                    "GitHub API rate limited (HTTP 403). "
                    "Set GITHUB_TOKEN to increase limit to 5000 req/hr."
                ) from e
            if e.code in (429, 502, 503) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, OSError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise
    return None  # Unreachable


class RateLimitError(RuntimeError):
    """Raised when GitHub API rate limit is exceeded."""


def list_tf_files(repo_name: str) -> list[str]:
    """Use GitHub Contents API to list all .tf files at the repo root.

    Returns a list of filenames (e.g. ['main.tf', 'terraform.tf', 'variables.tf']).
    Falls back to a known-common-files list if the API is unavailable (no token, rate-limited).
    """
    url = f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/contents"
    raw = _fetch_url(url, use_api_headers=True)
    if raw is None:
        return []
    try:
        entries = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    if not isinstance(entries, list):
        # API returned an error object (e.g. rate-limit message as JSON)
        return []
    return [
        e["name"]
        for e in entries
        if isinstance(e, dict) and e.get("type") == "file" and e.get("name", "").endswith(".tf")
    ]


def fetch_raw_file(repo_name: str, filepath: str, branch: str = "main") -> str | None:
    """Fetch a raw file from GitHub via raw.githubusercontent.com. Returns None on 404."""
    url = f"{GITHUB_RAW}/{GITHUB_ORG}/{repo_name}/{branch}/{filepath}"
    raw = _fetch_url(url, use_api_headers=False)
    if raw is None:
        return None
    return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# HCL parsing — brace-aware, no external library
# ---------------------------------------------------------------------------

def _strip_hcl_comments(text: str) -> str:
    """Remove single-line HCL comments (# ...) from text.
    Simplified: does not handle # inside quoted strings (uncommon in .tf structure).
    """
    lines = []
    for line in text.split("\n"):
        idx = line.find("#")
        if idx >= 0:
            lines.append(line[:idx])
        else:
            lines.append(line)
    return "\n".join(lines)


def _extract_brace_block(text: str, start: int) -> tuple[str, int]:
    """Find the first '{' at or after start and return (content, end_pos).

    content is the text between the braces (exclusive).
    end_pos is the index immediately after the closing '}'.
    Returns ("", -1) if no matching brace pair is found.
    """
    open_pos = text.find("{", start)
    if open_pos == -1:
        return "", -1
    depth = 0
    i = open_pos
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_pos + 1 : i], i + 1
        i += 1
    return "", -1  # Unmatched brace


def parse_terraform_constraints(content: str) -> dict:
    """Parse terraform.tf / versions.tf content for required_version and required_providers.

    Returns a dict:
        {
            "required_version": "...",           # may be absent
            "required_providers": {
                "azurerm": {"source": "...", "version_constraint": "..."},
                ...
            }
        }
    """
    result: dict = {}
    clean = _strip_hcl_comments(content)

    # required_version — simple string search
    m = re.search(r'required_version\s*=\s*"([^"]*)"', clean)
    if m:
        result["required_version"] = m.group(1)

    # required_providers block
    rp_idx = clean.find("required_providers")
    if rp_idx >= 0:
        block, _ = _extract_brace_block(clean, rp_idx)
        if block:
            providers: dict = {}
            pos = 0
            while pos < len(block):
                # Find next: name = {
                pm = re.search(r'(\w+)\s*=\s*\{', block[pos:])
                if not pm:
                    break
                prov_name = pm.group(1)
                abs_pos = pos + pm.start()
                prov_content, end_pos = _extract_brace_block(block, abs_pos)
                if prov_content and end_pos > 0:
                    src_m = re.search(r'source\s*=\s*"([^"]*)"', prov_content)
                    ver_m = re.search(r'version\s*=\s*"([^"]*)"', prov_content)
                    entry: dict = {}
                    if src_m:
                        entry["source"] = src_m.group(1)
                    if ver_m:
                        entry["version_constraint"] = ver_m.group(1)
                    if entry:
                        providers[prov_name] = entry
                    pos = end_pos
                else:
                    pos += pm.end()
            if providers:
                result["required_providers"] = providers

    return result


def parse_resources(content: str) -> dict[str, list[str]]:
    """Extract Terraform resource types from HCL, grouped by provider prefix.

    Returns: {"azurerm": ["azurerm_virtual_network", ...], "azapi": [...]}
    """
    clean = _strip_hcl_comments(content)
    resources: dict[str, set] = {}
    for m in re.finditer(r'^resource\s+"([^"]+)"\s+"[^"]+"', clean, re.MULTILINE):
        resource_type = m.group(1)
        provider_prefix = resource_type.split("_")[0]
        resources.setdefault(provider_prefix, set()).add(resource_type)
    return {k: sorted(v) for k, v in sorted(resources.items())}


def parse_module_calls(content: str) -> list[dict]:
    """Extract module call blocks from HCL content.

    Returns a list of dicts: [{"local_name": "...", "source": "...", "version": "..."}, ...]
    version is included only when present in the module block.
    """
    clean = _strip_hcl_comments(content)
    modules: list[dict] = []
    pos = 0
    while pos < len(clean):
        mm = re.search(r'^module\s+"([^"]+)"\s*\{', clean[pos:], re.MULTILINE)
        if not mm:
            break
        local_name = mm.group(1)
        abs_pos = pos + mm.start()
        block_content, end_pos = _extract_brace_block(clean, abs_pos)
        if block_content and end_pos > 0:
            src_m = re.search(r'source\s*=\s*"([^"]*)"', block_content)
            ver_m = re.search(r'version\s*=\s*"([^"]*)"', block_content)
            if src_m:
                entry: dict = {"local_name": local_name, "source": src_m.group(1)}
                if ver_m:
                    entry["version"] = ver_m.group(1)
                modules.append(entry)
            pos = end_pos
        else:
            pos += mm.end()
    return modules


# ---------------------------------------------------------------------------
# Per-module scraping
# ---------------------------------------------------------------------------

def _repo_name_from_url(repo_url: str) -> str:
    """Extract the GitHub repo name from a full URL.
    E.g. https://github.com/Azure/terraform-azurerm-avm-res-network-virtualnetwork
         → terraform-azurerm-avm-res-network-virtualnetwork
    """
    return repo_url.rstrip("/").split("/")[-1]


def scrape_module(filepath: str, mod_type: str, dry_run: bool) -> str:
    """Scrape a single module file. Returns 'ok', 'partial', 'failed', 'skipped', or 'unchanged'."""
    # Read repo_url and module name from catalog section
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    catalog_text = _extract_catalog_text(raw)
    if not catalog_text:
        print(f"    WARN: no catalog section in {filepath}", file=sys.stderr)
        return "failed"

    repo_url_m = re.search(r'repo_url:\s+"([^"]+)"', catalog_text)
    if not repo_url_m:
        print(f"    WARN: no repo_url in {filepath}", file=sys.stderr)
        return "failed"

    repo_url  = repo_url_m.group(1)
    repo_name = _repo_name_from_url(repo_url)

    # List all .tf files in the repo root
    errors: list[str] = []
    try:
        tf_files = list_tf_files(repo_name)
    except RateLimitError as e:
        print(f"    RATE LIMIT: {e}", file=sys.stderr)
        raise
    except Exception as e:
        errors.append(f"list_tf_files: {e}")
        # Fall back to known common filenames
        tf_files = ["terraform.tf", "versions.tf", "main.tf", "providers.tf"]

    # Fetch and concatenate all .tf file contents
    combined = ""
    fetched_count = 0
    for tf_file in tf_files:
        content = fetch_raw_file(repo_name, tf_file)
        if content:
            combined += f"\n# --- {tf_file} ---\n" + content
            fetched_count += 1

    if fetched_count == 0:
        errors.append("no .tf files fetched")

    # Parse constraints — common to all module types
    constraints = parse_terraform_constraints(combined) if combined else {}

    # Parse resources or module calls depending on module type
    resources_managed: dict = {}
    modules_called: list = []

    if mod_type in ("res", "utl"):
        resources_managed = parse_resources(combined) if combined else {}
    elif mod_type == "ptn":
        modules_called = parse_module_calls(combined) if combined else []

    # Determine scrape status
    if errors and fetched_count == 0:
        status = "failed"
    elif errors or (
        (mod_type in ("res", "utl") and not resources_managed and not constraints)
        or (mod_type == "ptn" and not modules_called and not constraints)
    ):
        status = "partial"
    else:
        status = "ok"

    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scraped_yaml = _build_scraped_yaml(at, status, errors, constraints, resources_managed, modules_called)
    new_block = SCRAPED_BEGIN_MARKER + "\n" + scraped_yaml + "\n" + SCRAPED_END_MARKER

    # Compare with existing scraped block
    existing_block = _extract_scraped_block(raw)
    if existing_block == new_block:
        return "unchanged"

    if dry_run:
        return f"would-update({status})"

    _write_scraped_block(filepath, raw, new_block)
    return status


def _extract_catalog_text(file_content: str) -> str | None:
    """Return content between BEGIN/END CATALOG markers."""
    begin = file_content.find(BEGIN_MARKER)
    end   = file_content.find(END_MARKER)
    if begin == -1 or end == -1:
        return None
    return file_content[begin : end + len(END_MARKER)]


def _extract_scraped_block(file_content: str) -> str | None:
    """Return the full scraped block including markers, or None."""
    begin = file_content.find(SCRAPED_BEGIN_MARKER)
    end   = file_content.find(SCRAPED_END_MARKER)
    if begin == -1 or end == -1:
        return None
    return file_content[begin : end + len(SCRAPED_END_MARKER)]


def _write_scraped_block(filepath: str, original_content: str, new_block: str) -> None:
    """Replace the scraped block in a module file. Inserts after END CATALOG if absent."""
    begin = original_content.find(SCRAPED_BEGIN_MARKER)
    end   = original_content.find(SCRAPED_END_MARKER)

    if begin != -1 and end != -1:
        # Replace existing scraped block
        new_content = (
            original_content[:begin]
            + new_block
            + original_content[end + len(SCRAPED_END_MARKER):]
        )
    else:
        # No scraped block yet — insert after END CATALOG
        catalog_end = original_content.find(END_MARKER)
        if catalog_end == -1:
            raise ValueError(f"Cannot locate {END_MARKER} in file")
        insert_pos = catalog_end + len(END_MARKER)
        new_content = (
            original_content[:insert_pos]
            + "\n" + new_block + "\n"
            + original_content[insert_pos:].lstrip("\n")
        )

    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)
    os.replace(tmp, filepath)


# ---------------------------------------------------------------------------
# Scraped YAML building (no PyYAML dependency)
# ---------------------------------------------------------------------------

def _s(v: str) -> str:
    """JSON-encoded YAML double-quoted scalar (same as in sync_catalog.py)."""
    return json.dumps(v)


def _build_scraped_yaml(
    at: str,
    status: str,
    errors: list[str],
    constraints: dict,
    resources_managed: dict,
    modules_called: list,
) -> str:
    """Build the scraped: YAML block content (not including the # BEGIN / # END markers)."""
    lines = [
        "scraped:",
        f"  at: {_s(at)}",
        f"  status: {status}",
    ]

    if errors:
        lines.append("  errors:")
        for e in errors:
            lines.append(f"    - {_s(e)}")
    else:
        lines.append("  errors: []")

    if constraints:
        lines.append("  terraform_constraints:")
        req_ver = constraints.get("required_version")
        if req_ver:
            lines.append(f"    required_version: {_s(req_ver)}")
        req_prov = constraints.get("required_providers", {})
        if req_prov:
            lines.append("    required_providers:")
            for prov_name, prov_data in sorted(req_prov.items()):
                lines.append(f"      {prov_name}:")
                if "source" in prov_data:
                    lines.append(f"        source: {_s(prov_data['source'])}")
                if "version_constraint" in prov_data:
                    lines.append(f"        version_constraint: {_s(prov_data['version_constraint'])}")

    if resources_managed:
        lines.append("  resources_managed:")
        for provider_prefix, res_list in sorted(resources_managed.items()):
            lines.append(f"    {provider_prefix}:")
            for r in res_list:
                lines.append(f"      - {_s(r)}")

    if modules_called:
        lines.append("  modules_called:")
        for mod in modules_called:
            lines.append(f"    - local_name: {_s(mod['local_name'])}")
            lines.append(f"      source: {_s(mod['source'])}")
            if "version" in mod:
                lines.append(f"      version: {_s(mod['version'])}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Staleness check
# ---------------------------------------------------------------------------

def _get_scraped_at(file_content: str) -> datetime | None:
    """Extract and parse the scraped.at timestamp from a file, or return None."""
    m = re.search(r'^\s+at:\s+"([^"]+)"', file_content, re.MULTILINE)
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_stale(file_content: str, max_age_days: int) -> bool:
    """Return True if the file has no scraped block or its scraped_at is older than max_age_days."""
    scraped_at = _get_scraped_at(file_content)
    if scraped_at is None:
        return True
    age = datetime.now(timezone.utc) - scraped_at
    return age.days >= max_age_days


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args() -> dict:
    args = {
        "dry_run":     "--dry-run" in sys.argv,
        "force":       "--force" in sys.argv,
        "module":      None,
        "max_age":     DEFAULT_MAX_AGE_DAYS,
    }
    for i, arg in enumerate(sys.argv):
        if arg == "--module" and i + 1 < len(sys.argv):
            args["module"] = sys.argv[i + 1]
        if arg == "--max-age" and i + 1 < len(sys.argv):
            try:
                args["max_age"] = int(sys.argv[i + 1])
            except ValueError:
                pass
    return args


def main() -> None:
    opts = _parse_args()

    if opts["dry_run"]:
        print("  (dry-run mode — no files will be modified)")

    if not os.environ.get("GITHUB_TOKEN"):
        print("  HINT: Set GITHUB_TOKEN for higher GitHub API rate limits (5000/hr vs 60/hr).")

    # Collect all module files
    module_files: list[tuple[str, str]] = []  # (filepath, mod_type)
    for mod_type in ("res", "ptn", "utl"):
        type_dir = os.path.join(MODULES_DIR, mod_type)
        if not os.path.isdir(type_dir):
            continue
        for fname in sorted(os.listdir(type_dir)):
            if not fname.endswith(".yaml"):
                continue
            mod_name = fname[:-5]
            if opts["module"] and mod_name != opts["module"]:
                continue
            module_files.append((os.path.join(type_dir, fname), mod_type))

    if opts["module"] and not module_files:
        print(f"ERROR: module '{opts['module']}' not found in data/modules/", file=sys.stderr)
        sys.exit(1)

    total     = len(module_files)
    ok        = partial = failed = unchanged = skipped = 0

    print(f"  Scraping {total} module(s)…")

    for idx, (filepath, mod_type) in enumerate(module_files, start=1):
        mod_name = os.path.basename(filepath)[:-5]
        prefix   = f"  [{idx:>3}/{total}] {mod_type}/{mod_name}"

        # Staleness check (skip fresh files unless --force)
        if not opts["force"]:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if not _is_stale(content, opts["max_age"]):
                skipped += 1
                continue

        try:
            result = scrape_module(filepath, mod_type, opts["dry_run"])
        except RateLimitError as e:
            print(f"\n  ABORT: {e}", file=sys.stderr)
            print(f"  Scraped {ok + partial + failed + unchanged + skipped}/{total} modules before rate limit.")
            sys.exit(2)
        except Exception as e:
            print(f"{prefix}  ✗ ERROR: {e}", file=sys.stderr)
            failed += 1
            continue

        if result == "unchanged":
            unchanged += 1
        elif result == "ok":
            ok += 1
            print(f"{prefix}  ✓ ok")
        elif result == "partial":
            partial += 1
            print(f"{prefix}  ⚠ partial")
        elif result == "failed":
            failed += 1
            print(f"{prefix}  ✗ failed")
        elif result.startswith("would-update"):
            ok += 1
            print(f"{prefix}  → {result}")

    print("────────────────────────────────────────────────────────")
    if opts["dry_run"]:
        print(f"Dry run — would update: {ok + partial + failed}, unchanged: {unchanged}, skipped (fresh): {skipped}")
    else:
        print(f"Done — ok: {ok}, partial: {partial}, failed: {failed}, unchanged: {unchanged}, skipped (fresh): {skipped}")


if __name__ == "__main__":
    main()
