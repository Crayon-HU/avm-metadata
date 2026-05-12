#!/usr/bin/env python3
"""analyze_module.py — Multi-dimensional analysis of AVM module repositories.

All tool-owned analysis results are stored in per-dimension marker blocks:
    # BEGIN ANALYSIS:{dimension}
    analysis_{dimension_slug}:
      ...
    # END ANALYSIS:{dimension}

Six built-in dimensions:
    terraform-metadata       Terraform version + provider constraints + resources/modules.
                             (replaces the old scrape_modules.py / # BEGIN SCRAPED)
    avm-interface-compliance Required AVM interface variables (lock, role_assignments, …)
    security-hardening       Hardcoded values, validation blocks, sensitive outputs.
    test-coverage            examples/, tests/, *.go / *.tftest.hcl file presence.
    doc-quality              README length, required section headers.
    dependency-health        Version constraint style (derived from terraform-metadata).

Usage:
    python3 scripts/analyze_module.py [options]
    ./avm.sh check [options]          # operator alias
    ./avm.sh scrape [options]         # backward-compat alias for --dimension terraform-metadata

Options:
    --module    NAME    Analyze a single module by name.
    --dimension DIM     Run only this dimension (repeat for multiple). Default: all.
    --dry-run           Show planned changes without writing files.
    --force             Ignore --max-age; always re-analyze.
    --max-age   DAYS    Skip dimensions checked within N days (default: 7).

Environment:
    GITHUB_TOKEN        Optional. Increases GitHub API rate limit from 60 to 5000 req/hr.
"""

import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
MODULES_DIR = os.path.join(REPO_ROOT, "data", "modules")

CATALOG_BEGIN = "# BEGIN CATALOG"
CATALOG_END   = "# END CATALOG"

ANALYSIS_BEGIN_PREFIX = "# BEGIN ANALYSIS:"
ANALYSIS_END_PREFIX   = "# END ANALYSIS:"

# Anchored regexes — match the marker line exactly (dimension-scoped)
def _begin_re(dim: str) -> re.Pattern:
    return re.compile(r"^" + re.escape(f"# BEGIN ANALYSIS:{dim}") + r"\s*$", re.MULTILINE)

def _end_re(dim: str) -> re.Pattern:
    return re.compile(r"^" + re.escape(f"# END ANALYSIS:{dim}") + r"\s*$", re.MULTILINE)

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"
GITHUB_ORG = "Azure"

DEFAULT_MAX_AGE_DAYS = 7

# AVM interface variables required per module type
AVM_INTERFACE_VARS_RES = [
    "lock", "role_assignments", "private_endpoints",
    "diagnostic_settings", "managed_identities", "tags", "enable_telemetry",
]
AVM_INTERFACE_VARS_PTN_UTL = ["tags", "enable_telemetry"]

# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

class RateLimitError(RuntimeError):
    """Raised when the GitHub API rate limit is exceeded."""


def _github_headers() -> dict:
    headers = {
        "Accept":     "application/vnd.github.v3+json",
        "User-Agent": "avm-metadata-analyzer/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_url(url: str, use_api_headers: bool = False, retries: int = 2) -> bytes | None:
    """Fetch a URL, returning bytes or None on 404. Retries on transient errors."""
    headers = _github_headers() if use_api_headers else {"User-Agent": "avm-metadata-analyzer/1.0"}
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
    return None


def list_root_contents(repo_name: str) -> list[dict]:
    """Fetch the repo root directory listing from the GitHub Contents API."""
    url = f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/contents"
    raw = _fetch_url(url, use_api_headers=True)
    if raw is None:
        return []
    try:
        entries = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    return entries if isinstance(entries, list) else []


def fetch_raw_file(repo_name: str, filepath: str, branch: str = "main") -> str | None:
    """Fetch a raw file from GitHub. Returns text or None on 404."""
    url = f"{GITHUB_RAW}/{GITHUB_ORG}/{repo_name}/{branch}/{filepath}"
    raw = _fetch_url(url, use_api_headers=False)
    return raw.decode("utf-8", errors="replace") if raw is not None else None


def list_directory(repo_name: str, path: str) -> list[dict] | None:
    """List a subdirectory in the repo. Returns None if the path doesn't exist."""
    url = f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/contents/{path}"
    raw = _fetch_url(url, use_api_headers=True)
    if raw is None:
        return None
    try:
        entries = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return entries if isinstance(entries, list) else None


# ---------------------------------------------------------------------------
# HCL parsing (no external library — brace-aware)
# ---------------------------------------------------------------------------

def _strip_hcl_comments(text: str) -> str:
    """Remove single-line HCL # comments (simplified — ignores # inside strings)."""
    lines = []
    for line in text.split("\n"):
        idx = line.find("#")
        lines.append(line[:idx] if idx >= 0 else line)
    return "\n".join(lines)


def _extract_brace_block(text: str, start: int) -> tuple[str, int]:
    """Find the first '{' at or after start and return (content_inside, end_pos)."""
    open_pos = text.find("{", start)
    if open_pos == -1:
        return "", -1
    depth, i = 0, open_pos
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_pos + 1 : i], i + 1
        i += 1
    return "", -1


def parse_terraform_constraints(content: str) -> dict:
    """Parse required_version and required_providers from terraform.tf / versions.tf."""
    result: dict = {}
    clean = _strip_hcl_comments(content)

    m = re.search(r'required_version\s*=\s*"([^"]*)"', clean)
    if m:
        result["required_version"] = m.group(1)

    rp_idx = clean.find("required_providers")
    if rp_idx >= 0:
        block, _ = _extract_brace_block(clean, rp_idx)
        if block:
            providers: dict = {}
            pos = 0
            while pos < len(block):
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
    """Extract Terraform resource types from HCL, grouped by provider prefix."""
    clean = _strip_hcl_comments(content)
    resources: dict[str, set] = {}
    for m in re.finditer(r'^resource\s+"([^"]+)"\s+"[^"]+"', clean, re.MULTILINE):
        resource_type = m.group(1)
        prefix = resource_type.split("_")[0]
        resources.setdefault(prefix, set()).add(resource_type)
    return {k: sorted(v) for k, v in sorted(resources.items())}


def parse_module_calls(content: str) -> list[dict]:
    """Extract module call blocks from HCL content."""
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


def parse_variable_names(content: str) -> list[tuple[str, int]]:
    """Return [(variable_name, line_number)] for all variable blocks in HCL."""
    variables = []
    for m in re.finditer(r'^variable\s+"([^"]+)"', content, re.MULTILINE):
        line_num = content[:m.start()].count("\n") + 1
        variables.append((m.group(1), line_num))
    return variables


def find_variable_file(var_name: str, tf_contents: dict[str, str]) -> str | None:
    """Return 'filename.tf:line' if var_name is declared, else None."""
    for fname, content in tf_contents.items():
        for name, line_num in parse_variable_names(content):
            if name == var_name:
                return f"{fname}:{line_num}"
    return None


# ---------------------------------------------------------------------------
# Per-module context — shared fetch cache
# ---------------------------------------------------------------------------

class ModuleContext:
    """Fetched data for one module, shared across all dimensions in a single run."""

    def __init__(self, repo_name: str, mod_type: str):
        self.repo_name = repo_name
        self.mod_type  = mod_type
        self._root_contents: list[dict] | None = None
        self._tf_contents:   dict[str, str] | None = None
        self._readme:        str | None = None
        self._readme_fetched = False
        self._examples_listing: list[dict] | None = None
        self._examples_fetched  = False
        self._tests_listing: list[dict] | None = None
        self._tests_fetched  = False

    def root_contents(self) -> list[dict]:
        if self._root_contents is None:
            self._root_contents = list_root_contents(self.repo_name)
        return self._root_contents

    def tf_contents(self) -> dict[str, str]:
        """Fetch and cache all root-level .tf file contents."""
        if self._tf_contents is None:
            self._tf_contents = {}
            tf_files = [
                e["name"] for e in self.root_contents()
                if isinstance(e, dict) and e.get("type") == "file"
                and e.get("name", "").endswith(".tf")
            ]
            for fname in tf_files:
                text = fetch_raw_file(self.repo_name, fname)
                if text:
                    self._tf_contents[fname] = text
        return self._tf_contents

    def combined_tf(self) -> str:
        return "\n".join(self.tf_contents().values())

    def readme(self) -> str | None:
        if not self._readme_fetched:
            self._readme_fetched = True
            self._readme = fetch_raw_file(self.repo_name, "README.md")
        return self._readme

    def examples_listing(self) -> list[dict] | None:
        if not self._examples_fetched:
            self._examples_fetched = True
            self._examples_listing = list_directory(self.repo_name, "examples")
        return self._examples_listing

    def tests_listing(self) -> list[dict] | None:
        if not self._tests_fetched:
            self._tests_fetched = True
            self._tests_listing = list_directory(self.repo_name, "tests")
        return self._tests_listing


# ---------------------------------------------------------------------------
# Block I/O — reading and writing ANALYSIS blocks
# ---------------------------------------------------------------------------

def extract_block(content: str, dim: str) -> tuple[int, int] | None:
    """Find the span of # BEGIN ANALYSIS:{dim} ... # END ANALYSIS:{dim} in content.

    Returns (begin_idx, end_idx_exclusive) where content[begin_idx:end_idx] is the
    full block including markers, or None if the block is absent.
    """
    bm = _begin_re(dim).search(content)
    if not bm:
        return None
    em = _end_re(dim).search(content, bm.end())
    if not em:
        return None
    return bm.start(), em.end()


def extract_checked_at(content: str, dim: str) -> datetime | None:
    """Extract the checked_at timestamp from a specific dimension's block."""
    span = extract_block(content, dim)
    if span is None:
        return None
    block_text = content[span[0]:span[1]]
    m = re.search(r'^\s+checked_at:\s+"([^"]+)"', block_text, re.MULTILINE)
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    except ValueError:
        return None


def is_stale(content: str, dim: str, max_age_days: int) -> bool:
    """Return True if the dimension block is absent or its checked_at is older than max_age_days."""
    checked_at = extract_checked_at(content, dim)
    if checked_at is None:
        return True
    age = datetime.now(timezone.utc) - checked_at
    if age.days < 0:
        # Future timestamp — treat as stale (e.g. clock skew)
        return True
    return age.days >= max_age_days


def _insertion_point(content: str) -> int:
    """Return the position to insert a new analysis block.

    Strategy: insert before the top-level `enrichment:` line if present,
    otherwise insert after `# END CATALOG`.
    """
    # Find enrichment: at the start of a line (not indented)
    enrich_m = re.search(r"^enrichment:", content, re.MULTILINE)
    if enrich_m:
        return enrich_m.start()
    # Fall back: after END CATALOG
    catalog_end = content.find(CATALOG_END)
    if catalog_end != -1:
        return catalog_end + len(CATALOG_END)
    return len(content)


def apply_block_updates(content: str, updates: dict[str, str]) -> str:
    """Apply all dimension block updates to content in one pass.

    updates: {dim: new_block_text_including_markers}

    For each dimension:
    - If block exists: replace it in place.
    - If block is absent: insert before enrichment: (or after END CATALOG).

    All replacements are applied to the same working string so no update
    clobbers another.
    """
    for dim, new_block in updates.items():
        span = extract_block(content, dim)
        if span is not None:
            before = content[: span[0]]
            after  = content[span[1]:]
            # Preserve a single newline after the block if one existed
            if after.startswith("\n"):
                content = before + new_block + after
            else:
                content = before + new_block + "\n" + after
        else:
            pos = _insertion_point(content)
            content = content[:pos] + new_block + "\n" + content[pos:]
    return content


def _write_atomic(filepath: str, content: str) -> None:
    """Write content atomically using a temp file in the same directory."""
    dir_path = os.path.dirname(filepath)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        # Copy permissions from original file
        try:
            orig_mode = os.stat(filepath).st_mode
            os.chmod(tmp_path, orig_mode)
        except OSError:
            pass
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# YAML serialization helpers (no PyYAML dependency)
# ---------------------------------------------------------------------------

def _q(v: str) -> str:
    """JSON-encoded double-quoted YAML scalar."""
    return json.dumps(v)


def _build_check_yaml(check_name: str, result: dict, indent: int = 4) -> str:
    """Serialize a single check result as inline YAML, e.g.:
        lock: { status: pass, evidence: "variables.tf:47" }
    """
    pad = " " * indent
    parts = [f"status: {result['status']}"]
    if "evidence" in result:
        parts.append(f"evidence: {_q(result['evidence'])}")
    if "finding" in result:
        parts.append(f"finding: {_q(result['finding'])}")
    inline = ", ".join(parts)
    return f"{pad}{check_name}: {{ {inline} }}"


def _build_analysis_block(dim: str, yaml_key: str, payload: dict) -> str:
    """Build the full # BEGIN ANALYSIS:{dim} ... # END ANALYSIS:{dim} block text."""
    lines = [
        f"# BEGIN ANALYSIS:{dim}",
        f"{yaml_key}:",
        f"  checked_at: {_q(payload['checked_at'])}",
        f"  status: {payload['status']}",
    ]

    if "errors" in payload:
        if payload["errors"]:
            lines.append("  errors:")
            for e in payload["errors"]:
                lines.append(f"    - {_q(e)}")
        else:
            lines.append("  errors: []")

    if "terraform_constraints" in payload:
        constraints = payload["terraform_constraints"]
        if constraints:
            lines.append("  terraform_constraints:")
            if "required_version" in constraints:
                lines.append(f"    required_version: {_q(constraints['required_version'])}")
            req_prov = constraints.get("required_providers", {})
            if req_prov:
                lines.append("    required_providers:")
                for prov, pdata in sorted(req_prov.items()):
                    lines.append(f"      {prov}:")
                    if "source" in pdata:
                        lines.append(f"        source: {_q(pdata['source'])}")
                    if "version_constraint" in pdata:
                        lines.append(f"        version_constraint: {_q(pdata['version_constraint'])}")

    if "resources_managed" in payload:
        rm = payload["resources_managed"]
        if rm:
            lines.append("  resources_managed:")
            for prefix, res_list in sorted(rm.items()):
                lines.append(f"    {prefix}:")
                for r in res_list:
                    lines.append(f"      - {_q(r)}")

    if "modules_called" in payload:
        mc = payload["modules_called"]
        if mc:
            lines.append("  modules_called:")
            for mod in mc:
                lines.append(f"    - local_name: {_q(mod['local_name'])}")
                lines.append(f"      source: {_q(mod['source'])}")
                if "version" in mod:
                    lines.append(f"      version: {_q(mod['version'])}")

    if "checks" in payload:
        checks = payload["checks"]
        if checks:
            lines.append("  checks:")
            for check_name, result in checks.items():
                lines.append(_build_check_yaml(check_name, result))

    if "llm_assessment" in payload:
        lines.append(f"  llm_assessment: {_q(payload['llm_assessment'])}")

    lines.append(f"# END ANALYSIS:{dim}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dimension: terraform-metadata
# ---------------------------------------------------------------------------

def check_terraform_metadata(ctx: ModuleContext) -> dict:
    """Fetch .tf files and extract version constraints + resources/module calls."""
    errors: list[str] = []
    tf_files = ctx.tf_contents()

    if not tf_files:
        errors.append("no .tf files fetched from repo root")

    combined = ctx.combined_tf()
    constraints = parse_terraform_constraints(combined) if combined else {}
    resources_managed: dict = {}
    modules_called:    list = []

    if ctx.mod_type in ("res", "utl"):
        resources_managed = parse_resources(combined) if combined else {}
    elif ctx.mod_type == "ptn":
        modules_called = parse_module_calls(combined) if combined else []

    if errors and not tf_files:
        status = "fail"
    elif errors or (
        ctx.mod_type in ("res", "utl") and not resources_managed and not constraints
    ) or (
        ctx.mod_type == "ptn" and not modules_called and not constraints
    ):
        status = "partial"
    else:
        status = "pass"

    payload: dict = {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status":     status,
        "errors":     errors,
    }
    if constraints:
        payload["terraform_constraints"] = constraints
    if resources_managed:
        payload["resources_managed"] = resources_managed
    if modules_called:
        payload["modules_called"] = modules_called

    return payload


# ---------------------------------------------------------------------------
# Dimension: avm-interface-compliance
# ---------------------------------------------------------------------------

# Required interface variables per module type
_AVM_INTERFACE_REQUIRED: dict[str, list[str]] = {
    "res": AVM_INTERFACE_VARS_RES,
    "ptn": AVM_INTERFACE_VARS_PTN_UTL,
    "utl": AVM_INTERFACE_VARS_PTN_UTL,
}


def check_avm_interface_compliance(ctx: ModuleContext) -> dict:
    """Check for required AVM interface variable declarations in .tf files."""
    required_vars = _AVM_INTERFACE_REQUIRED.get(ctx.mod_type, AVM_INTERFACE_VARS_PTN_UTL)
    tf_files = ctx.tf_contents()
    checks: dict = {}

    for var_name in required_vars:
        location = find_variable_file(var_name, tf_files)
        if location:
            checks[var_name] = {"status": "pass", "evidence": location}
        else:
            checks[var_name] = {
                "status":  "missing",
                "finding": f'No variable "{var_name}" found in root .tf files',
            }

    if not tf_files:
        overall = "fail"
    elif all(c["status"] == "pass" for c in checks.values()):
        overall = "pass"
    elif any(c["status"] == "pass" for c in checks.values()):
        overall = "partial"
    else:
        overall = "fail"

    return {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status":     overall,
        "checks":     checks,
    }


# ---------------------------------------------------------------------------
# Dimension: security-hardening
# ---------------------------------------------------------------------------

# Common Azure region names that should not be hardcoded
_HARDCODED_LOCATIONS = [
    "eastus", "eastus2", "westus", "westus2", "westus3",
    "northeurope", "westeurope", "uksouth", "ukwest",
    "australiaeast", "southeastasia", "eastasia",
    "centralus", "northcentralus", "southcentralus",
]
_LOCATION_PATTERN = re.compile(
    r'"(' + "|".join(re.escape(loc) for loc in _HARDCODED_LOCATIONS) + r')"',
    re.IGNORECASE,
)

# Sensitive output name substrings
_SENSITIVE_KEYWORDS = ["key", "secret", "password", "token", "credential", "cert"]


def _find_hardcoded_locations(tf_contents: dict[str, str]) -> dict:
    """Check for hardcoded Azure location strings outside of comments."""
    for fname, content in tf_contents.items():
        clean = _strip_hcl_comments(content)
        m = _LOCATION_PATTERN.search(clean)
        if m:
            line_num = content[:content.find(m.group(0))].count("\n") + 1 if m.group(0) in content else 0
            return {
                "status":  "fail",
                "finding": f'Hardcoded location "{m.group(1)}" in {fname}:{line_num}',
            }
    return {"status": "pass", "evidence": "No hardcoded locations found"}


def _find_validation_blocks(tf_contents: dict[str, str]) -> dict:
    """Check that variables have validation {} blocks (heuristic: at least one must exist)."""
    for fname, content in tf_contents.items():
        if re.search(r'\bvalidation\s*\{', content):
            return {"status": "pass", "evidence": f"validation block found in {fname}"}
    return {
        "status":  "partial",
        "finding": "No validation {} blocks found in any .tf file",
    }


def _find_sensitive_outputs(tf_contents: dict[str, str]) -> dict:
    """Check that outputs with sensitive names declare sensitive = true."""
    for fname, content in tf_contents.items():
        clean = _strip_hcl_comments(content)
        for m in re.finditer(r'^output\s+"([^"]+)"\s*\{', clean, re.MULTILINE):
            out_name = m.group(1).lower()
            if any(kw in out_name for kw in _SENSITIVE_KEYWORDS):
                block_content, _ = _extract_brace_block(clean, m.start())
                if not re.search(r'\bsensitive\s*=\s*true\b', block_content):
                    return {
                        "status":  "fail",
                        "finding": f'Output "{m.group(1)}" in {fname} may be sensitive but lacks sensitive = true',
                    }
    return {"status": "pass", "evidence": "All sensitive-named outputs declare sensitive = true (or none found)"}


def check_security_hardening(ctx: ModuleContext) -> dict:
    """Scan .tf files for common security anti-patterns."""
    tf_files = ctx.tf_contents()

    if not tf_files:
        return {
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "fail",
            "checks": {
                "hardcoded_locations": {"status": "unchecked", "finding": "No .tf files available"},
                "validation_blocks":   {"status": "unchecked", "finding": "No .tf files available"},
                "sensitive_outputs":   {"status": "unchecked", "finding": "No .tf files available"},
            },
        }

    checks = {
        "hardcoded_locations": _find_hardcoded_locations(tf_files),
        "validation_blocks":   _find_validation_blocks(tf_files),
        "sensitive_outputs":   _find_sensitive_outputs(tf_files),
    }

    statuses = [c["status"] for c in checks.values()]
    if all(s == "pass" for s in statuses):
        overall = "pass"
    elif any(s == "fail" for s in statuses):
        overall = "fail"
    else:
        overall = "partial"

    return {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status":     overall,
        "checks":     checks,
    }


# ---------------------------------------------------------------------------
# Dimension: test-coverage
# ---------------------------------------------------------------------------

def check_test_coverage(ctx: ModuleContext) -> dict:
    """Check for examples/, tests/, and test file types via GitHub Contents API."""
    checks: dict = {}

    # Check examples/ directory
    examples = ctx.examples_listing()
    if examples is not None and len(examples) > 0:
        checks["examples_dir"] = {
            "status":   "pass",
            "evidence": f"examples/ contains {len(examples)} item(s)",
        }
    else:
        checks["examples_dir"] = {
            "status":  "missing",
            "finding": "examples/ directory not found or empty",
        }

    # Check tests/ directory
    tests = ctx.tests_listing()
    if tests is not None:
        # Look for .go or .tftest.hcl files in tests/
        test_files = [
            e["name"] for e in tests
            if isinstance(e, dict) and e.get("type") == "file"
            and (e.get("name", "").endswith(".go") or e.get("name", "").endswith(".tftest.hcl"))
        ]
        if test_files:
            checks["test_files"] = {
                "status":   "pass",
                "evidence": f"Found {len(test_files)} test file(s) in tests/ ({test_files[0]}…)",
            }
        else:
            checks["test_files"] = {
                "status":  "partial",
                "finding": "tests/ exists but contains no .go or .tftest.hcl files",
            }
    else:
        checks["test_files"] = {
            "status":  "missing",
            "finding": "tests/ directory not found",
        }

    statuses = [c["status"] for c in checks.values()]
    if all(s == "pass" for s in statuses):
        overall = "pass"
    elif any(s == "missing" for s in statuses):
        overall = "partial"
    else:
        overall = "partial"

    return {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status":     overall,
        "checks":     checks,
    }


# ---------------------------------------------------------------------------
# Dimension: doc-quality
# ---------------------------------------------------------------------------

_REQUIRED_README_SECTIONS = ["## Usage", "## Examples", "## Requirements"]
_MIN_README_CHARS = 500


def check_doc_quality(ctx: ModuleContext) -> dict:
    """Check README.md length and required section headers."""
    readme = ctx.readme()
    checks: dict = {}

    if readme is None:
        return {
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "fail",
            "checks": {
                "readme_exists":   {"status": "missing", "finding": "README.md not found"},
                "readme_length":   {"status": "unchecked", "finding": "README.md not found"},
                "required_sections": {"status": "unchecked", "finding": "README.md not found"},
            },
        }

    checks["readme_exists"] = {"status": "pass", "evidence": "README.md found"}

    char_count = len(readme)
    if char_count >= _MIN_README_CHARS:
        checks["readme_length"] = {
            "status":   "pass",
            "evidence": f"{char_count} characters",
        }
    else:
        checks["readme_length"] = {
            "status":  "partial",
            "finding": f"README.md only {char_count} characters (minimum {_MIN_README_CHARS})",
        }

    missing_sections = [s for s in _REQUIRED_README_SECTIONS if s not in readme]
    if not missing_sections:
        checks["required_sections"] = {
            "status":   "pass",
            "evidence": f"All required sections present: {', '.join(_REQUIRED_README_SECTIONS)}",
        }
    else:
        checks["required_sections"] = {
            "status":  "partial",
            "finding": f"Missing sections: {', '.join(missing_sections)}",
        }

    statuses = [c["status"] for c in checks.values()]
    if all(s == "pass" for s in statuses):
        overall = "pass"
    elif any(s in ("fail", "missing") for s in statuses):
        overall = "fail"
    else:
        overall = "partial"

    return {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status":     overall,
        "checks":     checks,
    }


# ---------------------------------------------------------------------------
# Dimension: dependency-health
# ---------------------------------------------------------------------------

def check_dependency_health(ctx: ModuleContext, metadata_payload: dict | None = None) -> dict:
    """Check version constraint style using terraform-metadata (no extra API calls).

    metadata_payload: if terraform-metadata was just re-run, pass its payload directly.
    Otherwise, the caller is responsible for ensuring the YAML file has an up-to-date block.
    """
    checks: dict = {}

    if metadata_payload is None:
        # No in-memory data — indicate that we couldn't run properly
        return {
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status":     "partial",
            "checks": {
                "terraform_version_upper_bound": {
                    "status":  "unchecked",
                    "finding": "terraform-metadata not available; run that dimension first",
                },
                "provider_constraint_style": {
                    "status":  "unchecked",
                    "finding": "terraform-metadata not available; run that dimension first",
                },
            },
        }

    if metadata_payload.get("status") in ("fail",):
        return {
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status":     "partial",
            "checks": {
                "terraform_version_upper_bound": {
                    "status":  "unchecked",
                    "finding": "terraform-metadata failed; cannot assess dependency health",
                },
                "provider_constraint_style": {
                    "status":  "unchecked",
                    "finding": "terraform-metadata failed; cannot assess dependency health",
                },
            },
        }

    constraints = metadata_payload.get("terraform_constraints", {})

    # Check: Terraform required_version has an upper bound
    req_ver = constraints.get("required_version", "")
    if req_ver:
        # Upper bound = constraint contains "< " or "~>" (pessimistic operator)
        if "< " in req_ver or "<=" in req_ver or ("~>" in req_ver and not req_ver.startswith(">=")):
            checks["terraform_version_upper_bound"] = {
                "status":   "pass",
                "evidence": f'required_version = "{req_ver}"',
            }
        else:
            checks["terraform_version_upper_bound"] = {
                "status":  "partial",
                "finding": f'required_version = "{req_ver}" has no upper bound',
            }
    else:
        checks["terraform_version_upper_bound"] = {
            "status":  "missing",
            "finding": "required_version not specified in terraform block",
        }

    # Check: all providers use ~> or pinned = constraints (not open-ended >=)
    req_prov = constraints.get("required_providers", {})
    open_ended = []
    for prov_name, pdata in req_prov.items():
        ver_constraint = pdata.get("version_constraint", "")
        if ver_constraint and ver_constraint.lstrip().startswith(">=") and "<" not in ver_constraint:
            open_ended.append(f"{prov_name}: {_q(ver_constraint)}")

    if not req_prov:
        checks["provider_constraint_style"] = {
            "status":  "missing",
            "finding": "No required_providers block found",
        }
    elif open_ended:
        checks["provider_constraint_style"] = {
            "status":  "fail",
            "finding": f"Open-ended >= constraint(s) detected: {'; '.join(open_ended)}",
        }
    else:
        checks["provider_constraint_style"] = {
            "status":   "pass",
            "evidence": f"All {len(req_prov)} provider(s) use upper-bounded constraints",
        }

    statuses = [c["status"] for c in checks.values()]
    if all(s == "pass" for s in statuses):
        overall = "pass"
    elif any(s == "fail" for s in statuses):
        overall = "fail"
    else:
        overall = "partial"

    return {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status":     overall,
        "checks":     checks,
    }


# ---------------------------------------------------------------------------
# Dimension registry
# ---------------------------------------------------------------------------

# Maps dimension slug → (yaml_key, check_function)
# Functions receive (ctx: ModuleContext) except dependency-health which also takes
# an optional in-memory metadata_payload.
DIMENSIONS: dict[str, tuple[str, object]] = {
    "terraform-metadata":       ("analysis_terraform_metadata",       check_terraform_metadata),
    "avm-interface-compliance": ("analysis_avm_interface_compliance", check_avm_interface_compliance),
    "security-hardening":       ("analysis_security_hardening",       check_security_hardening),
    "test-coverage":            ("analysis_test_coverage",            check_test_coverage),
    "doc-quality":              ("analysis_doc_quality",              check_doc_quality),
    "dependency-health":        ("analysis_dependency_health",        check_dependency_health),
}


def _yaml_key(dim: str) -> str:
    return DIMENSIONS[dim][0]


# ---------------------------------------------------------------------------
# Per-module orchestration
# ---------------------------------------------------------------------------

def analyze_module(filepath: str, mod_type: str, dims: list[str], opts: dict) -> str:
    """Run the requested dimensions on one module file.

    Returns a summary string: 'ok', 'partial', 'failed', 'unchanged', or 'would-update(…)'.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract repo_url from catalog block for GitHub fetching
    repo_url_m = re.search(r'repo_url:\s+"([^"]+)"', content)
    if not repo_url_m:
        print(f"    WARN: no repo_url in {filepath}", file=sys.stderr)
        return "failed"

    repo_url  = repo_url_m.group(1)
    repo_name = repo_url.rstrip("/").split("/")[-1]

    ctx = ModuleContext(repo_name=repo_name, mod_type=mod_type)

    # Determine which dimensions are actually stale and need running
    dims_to_run: list[str] = []
    for dim in dims:
        if opts["force"] or is_stale(content, dim, opts["max_age"]):
            dims_to_run.append(dim)

    # dependency-health auto-triggers terraform-metadata if metadata is going to be
    # refreshed in this run (to keep them consistent)
    if "dependency-health" in dims_to_run and "terraform-metadata" not in dims_to_run:
        # Also add terraform-metadata if the existing block is absent/stale, so
        # dependency-health can use fresh in-memory data
        if is_stale(content, "terraform-metadata", opts["max_age"]):
            dims_to_run.insert(0, "terraform-metadata")

    if not dims_to_run:
        return "unchanged"

    # Run check functions, building payloads
    payloads: dict[str, dict] = {}
    statuses: list[str] = []

    metadata_payload: dict | None = None  # passed to dependency-health if freshly computed

    for dim in dims_to_run:
        yaml_key, check_fn = DIMENSIONS[dim]
        try:
            if dim == "dependency-health":
                payload = check_dependency_health(ctx, metadata_payload=metadata_payload)
            else:
                payload = check_fn(ctx)  # type: ignore[call-arg]
            if dim == "terraform-metadata":
                metadata_payload = payload
        except RateLimitError:
            raise
        except Exception as e:
            payload = {
                "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "status":     "fail",
                "checks": {
                    "error": {"status": "fail", "finding": f"Unexpected error: {e}"}
                },
            }

        payloads[dim] = payload
        statuses.append(payload["status"])

    # Serialise each dimension payload into a block
    updates: dict[str, str] = {}
    for dim, payload in payloads.items():
        yaml_key, _ = DIMENSIONS[dim]
        block_text = _build_analysis_block(dim, yaml_key, payload)
        updates[dim] = block_text

    new_content = apply_block_updates(content, updates)

    if new_content == content:
        return "unchanged"

    if opts["dry_run"]:
        combined_status = (
            "pass" if all(s == "pass" for s in statuses)
            else "fail" if "fail" in statuses
            else "partial"
        )
        return f"would-update({combined_status})"

    _write_atomic(filepath, new_content)

    if "fail" in statuses:
        return "failed"
    if "partial" in statuses:
        return "partial"
    return "ok"


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> dict:
    args: dict = {
        "dry_run":    "--dry-run" in sys.argv,
        "force":      "--force" in sys.argv,
        "module":     None,
        "dimensions": [],
        "max_age":    DEFAULT_MAX_AGE_DAYS,
    }
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--module" and i + 1 < len(sys.argv):
            args["module"] = sys.argv[i + 1]
            i += 2
        elif arg == "--dimension" and i + 1 < len(sys.argv):
            dim = sys.argv[i + 1]
            if dim not in DIMENSIONS:
                print(
                    f"ERROR: unknown dimension '{dim}'. Valid dimensions: {', '.join(DIMENSIONS)}",
                    file=sys.stderr,
                )
                sys.exit(1)
            args["dimensions"].append(dim)
            i += 2
        elif arg == "--max-age" and i + 1 < len(sys.argv):
            try:
                args["max_age"] = int(sys.argv[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    if not args["dimensions"]:
        args["dimensions"] = list(DIMENSIONS.keys())

    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    opts = _parse_args()

    if opts["dry_run"]:
        print("  (dry-run mode — no files will be modified)")

    if not os.environ.get("GITHUB_TOKEN"):
        print("  HINT: Set GITHUB_TOKEN for higher GitHub API rate limits (5000/hr vs 60/hr).")

    dims = opts["dimensions"]
    print(f"  Dimensions: {', '.join(dims)}")

    module_files: list[tuple[str, str]] = []
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

    total = len(module_files)
    ok = partial = failed = unchanged = 0

    print(f"  Analyzing {total} module(s)…")

    for idx, (filepath, mod_type) in enumerate(module_files, start=1):
        mod_name = os.path.basename(filepath)[:-5]
        prefix   = f"  [{idx:>3}/{total}] {mod_type}/{mod_name}"

        try:
            result = analyze_module(filepath, mod_type, dims, opts)
        except RateLimitError as e:
            print(f"\n  ABORT: {e}", file=sys.stderr)
            print(f"  Analyzed {ok + partial + failed + unchanged}/{total} modules before rate limit.")
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
        print(
            f"Dry run — would update: {ok + partial + failed}, "
            f"unchanged: {unchanged}"
        )
    else:
        print(
            f"Done — ok: {ok}, partial: {partial}, failed: {failed}, "
            f"unchanged: {unchanged}"
        )


if __name__ == "__main__":
    main()
