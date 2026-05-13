#!/usr/bin/env python3
"""build_resource_index.py — Build a per-resource-type stub inventory.

Reads all analysis_terraform_metadata blocks from data/modules/ YAMLs and
creates stub YAML files for each Terraform symbol type encountered:

  data/resources/    azurerm_virtual_network.yaml
  data/datasources/  azurerm_subnet.yaml      (separate folder — avoids name collision)
  data/functions/    assert_cidrv4.yaml
  data/ephemerals/   ...
  data/actions/      ...

Each stub is the future home for provider changelog findings and provider issues.
Stubs are created once and NEVER overwritten — run Phase 2/3 scripts to populate
provider_updates.findings and provider_issues.items.

Usage:
    python3 scripts/build_resource_index.py [options]
    ./avm.sh index [options]    # operator alias

Options:
    --domains LIST   Comma-separated domain slugs (or 'all').
    --types LIST     Comma-separated module types: res, ptn, utl (or 'all').
    --modules LIST   Comma-separated module names (short form or full name).
    --dry-run        Print what would be created/skipped without writing.
    --force          Overwrite existing stubs (regenerates the stub header;
                     safe to run — provider_updates/provider_issues content
                     would be reset to empty, so use with care).
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
MODULES_DIR = os.path.join(REPO_ROOT, "data", "modules")
DATA_DIR    = os.path.join(REPO_ROOT, "data")

# ---------------------------------------------------------------------------
# Symbol type constants
# ---------------------------------------------------------------------------

# Symbol type → output directory under data/ (directories already exist)
_SYMBOL_DIR: dict[str, str] = {
    "resource":   "resources",
    "datasource": "datasources",
    "function":   "functions",
    "ephemeral":  "ephemerals",
    "action":     "actions",
}

# Symbol type → YAML key in analysis_terraform_metadata
_SYMBOL_YAML_KEY: dict[str, str] = {
    "resource":   "resources_managed",
    "datasource": "datasources_managed",
    "function":   "functions_used",
    "ephemeral":  "ephemeral_managed",
    "action":     "actions_managed",
}

# Known provider → Terraform Registry namespace (hashicorp/name or org/name)
_PROVIDER_NAMESPACES: dict[str, str] = {
    "azurerm":   "hashicorp/azurerm",
    "azuread":   "hashicorp/azuread",
    "azapi":     "azure/azapi",
    "null":      "hashicorp/null",
    "random":    "hashicorp/random",
    "time":      "hashicorp/time",
    "tls":       "hashicorp/tls",
    "modtm":     "azure/modtm",
    "assert":    "bwoznicki/assert",
    "terraform": "",  # built-in provider — no registry page
}

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------
_NO_COLOR = not sys.stdout.isatty()


def _ansi(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"


def _ok(s: str)   -> str: return _ansi("32", s)
def _warn(s: str) -> str: return _ansi("33", s)
def _dim(s: str)  -> str: return _ansi("2",  s)


SEP = "─" * 70

# ---------------------------------------------------------------------------
# YAML block parsers (stdlib, no dependencies)
# ---------------------------------------------------------------------------


def _read_raw(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _extract_catalog_fields(content: str) -> dict[str, str]:
    """Extract name, domain, type, status from the CATALOG block (2-space indent only)."""
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
        m = re.match(r'^  (name|domain|type|status|display_name):\s+"?([^"#\n]+)"?', line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"')
    return fields


def _extract_tf_metadata_block(content: str) -> str:
    """Return the raw text of the analysis_terraform_metadata block, or ''."""
    start_pat = re.compile(r"^# BEGIN ANALYSIS:terraform-metadata\s*$", re.MULTILINE)
    end_pat   = re.compile(r"^# END ANALYSIS:terraform-metadata\s*$",   re.MULTILINE)
    m_start   = start_pat.search(content)
    if not m_start:
        return ""
    m_end = end_pat.search(content, m_start.end())
    if not m_end:
        return ""
    return content[m_start.end():m_end.start()]


def _parse_symbol_map(block: str, key: str) -> dict[str, list[str]]:
    """Parse a symbol map like:
        resources_managed:
          azurerm:
            - azurerm_virtual_network
            - azurerm_subnet
    Returns {provider: [resource_type, ...]} or {} if key not present.
    """
    result: dict[str, list[str]] = {}
    lines  = block.splitlines()
    in_key = False
    cur_provider: str | None = None
    key_indent: int | None = None

    for line in lines:
        stripped = line.lstrip()
        indent   = len(line) - len(stripped)
        if not stripped:
            continue

        # Detect the top-level key (e.g. "  resources_managed:")
        if stripped.rstrip(":") == key and stripped.endswith(":"):
            in_key     = True
            key_indent = indent
            cur_provider = None
            continue

        if not in_key:
            continue

        # A line at the same indent as the key terminates the block
        if key_indent is not None and indent <= key_indent and not stripped.startswith("-"):
            in_key = False
            cur_provider = None
            continue

        # Provider line: "  azurerm:" (one level deeper than key)
        if stripped.endswith(":") and not stripped.startswith("-"):
            cur_provider = stripped[:-1].strip()
            result.setdefault(cur_provider, [])
            continue

        # List item: "    - azurerm_virtual_network"
        if stripped.startswith("- ") and cur_provider is not None:
            rtype = stripped[2:].strip().strip('"')
            if rtype:
                result[cur_provider].append(rtype)

    return result

# ---------------------------------------------------------------------------
# Stub generation
# ---------------------------------------------------------------------------


def _registry_url(symbol_type: str, provider: str, resource_type: str) -> str:
    """Construct the Terraform Registry docs URL for a given symbol."""
    namespace = _PROVIDER_NAMESPACES.get(provider, f"hashicorp/{provider}")
    if not namespace:
        return ""  # built-in provider (e.g. terraform)

    base = f"https://registry.terraform.io/providers/{namespace}/latest/docs"

    # Strip provider prefix to get the URL path suffix
    prefix = f"{provider}_"
    if resource_type.startswith(prefix):
        suffix = resource_type[len(prefix):]
    elif "::" in resource_type:
        # Function: "assert::cidrv4" → use function name only
        suffix = resource_type.split("::")[-1]
    else:
        suffix = resource_type

    if symbol_type == "resource":
        return f"{base}/resources/{suffix}"
    elif symbol_type == "datasource":
        return f"{base}/data-sources/{suffix}"
    elif symbol_type == "function":
        return f"{base}/functions/{suffix}"
    elif symbol_type == "ephemeral":
        return f"{base}/ephemeral-resources/{suffix}"
    else:
        # Actions — no standard registry docs page
        return ""


def _safe_filename(resource_type: str) -> str:
    """Convert a resource type string to a safe filename (no ::, no slashes)."""
    return re.sub(r"[:/\\]+", "_", resource_type).strip("_")


def _stub_content(symbol_type: str, provider: str, resource_type: str) -> str:
    """Generate stub YAML content for a resource type."""
    registry_url = _registry_url(symbol_type, provider, resource_type)
    lines = [
        f"resource:",
        f"  type: {resource_type}",
        f"  provider: {provider}",
        f"  symbol_type: {symbol_type}",
    ]
    if registry_url:
        lines.append(f'  registry_url: "{registry_url}"')
    lines += [
        f"",
        f"provider_updates:",
        f"  last_checked: null",
        f"  findings: []",
        f"  # finding shape:",
        f"  #   - version: \"4.15.0\"",
        f"  #     criticality: high   # critical | high | medium | low",
        f"  #     type: bug_fix       # bug_fix | security | enhancement | breaking_change | new_feature | deprecated",
        f"  #     summary: \"...\"",
        f"  #     url: \"...\"",
        f"",
        f"provider_issues:",
        f"  last_checked: null",
        f"  items: []",
        f"  # item shape:",
        f"  #   - number: 1234",
        f"  #     title: \"...\"",
        f"  #     labels: [bug]",
        f"  #     url: \"...\"",
        f"  #     created_at: \"2026-01-01\"",
        f"",
        f"enrichment:",
        f"  notes: []",
    ]
    return "\n".join(lines) + "\n"


def _write_stub(symbol_type: str, provider: str, resource_type: str, dry_run: bool, force: bool = False) -> tuple[str, bool]:
    """Write a stub file. Returns (path, was_created_or_overwritten).

    By default, existing stubs are skipped (no overwrite). Pass force=True to
    regenerate stubs even if they already exist (safe — only recreates the stub
    header, not provider_updates or provider_issues content).
    """
    folder = os.path.join(DATA_DIR, _SYMBOL_DIR[symbol_type])
    os.makedirs(folder, exist_ok=True)
    filename = _safe_filename(resource_type) + ".yaml"
    filepath = os.path.join(folder, filename)

    if os.path.exists(filepath) and not force:
        return filepath, False  # already exists — skip unless --force

    if not dry_run:
        content = _stub_content(symbol_type, provider, resource_type)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return filepath, True

# ---------------------------------------------------------------------------
# Inventory builder
# ---------------------------------------------------------------------------


def build_inventory(
    filter_domains: list[str] | None = None,
    filter_types:   list[str] | None = None,
    filter_modules: list[str] | None = None,
) -> set[tuple[str, str, str]]:
    """Scan all module YAMLs and return a set of (symbol_type, provider, resource_type) tuples."""
    found: set[tuple[str, str, str]] = set()

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
            name    = catalog.get("name", fname[:-5])
            short   = (name
                       .removeprefix("terraform-azurerm-")
                       .removeprefix("terraform-azure-")
                       .removeprefix("terraform-azapi-"))

            if filter_domains and domain not in filter_domains:
                continue
            if filter_modules and short not in filter_modules and name not in filter_modules:
                continue

            block = _extract_tf_metadata_block(content)
            if not block:
                continue

            for sym_type, yaml_key in _SYMBOL_YAML_KEY.items():
                symbol_map = _parse_symbol_map(block, yaml_key)
                for provider, resource_types in symbol_map.items():
                    for rtype in resource_types:
                        found.add((sym_type, provider, rtype))

    return found

# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


def cmd_index(
    filter_domains: list[str] | None = None,
    filter_types:   list[str] | None = None,
    filter_modules: list[str] | None = None,
    dry_run:        bool = False,
    force:          bool = False,
) -> None:
    flags = []
    if dry_run: flags.append("dry-run")
    if force:   flags.append("force")
    flag_str = f"[{', '.join(flags)}] " if flags else ""
    print(f"\nAVM index  {flag_str}— building resource stub inventory")
    print(SEP)

    inventory = build_inventory(filter_domains, filter_types, filter_modules)

    if not inventory:
        print(_warn("  No analysis_terraform_metadata blocks found. Run './avm.sh check' first."))
        sys.exit(0)

    created  = 0
    skipped  = 0
    by_sym: dict[str, int] = {}

    for sym_type, provider, rtype in sorted(inventory):
        filepath, was_written = _write_stub(sym_type, provider, rtype, dry_run, force)
        if was_written:
            created += 1
            by_sym[sym_type] = by_sym.get(sym_type, 0) + 1
            if dry_run:
                action = "would create" if not os.path.exists(filepath) else "would overwrite"
                label  = _dim(f"[dry-run] {action}")
            else:
                label = _ok("✓")
            rel = os.path.relpath(filepath, REPO_ROOT)
            print(f"  {label}  {rel}")
        else:
            skipped += 1

    print()
    sym_summary = "  ".join(f"{k}={v}" for k, v in sorted(by_sym.items()))

    action_word = "Wrote" if force else "Created"
    if dry_run:
        print(f"  {_dim('[dry-run]')} Would write {created} stub(s)  |  "
              f"skip {skipped} existing  |  ({sym_summary})")
    else:
        print(f"  {_ok('Done.')}  {action_word} {created}  |  "
              f"Skipped {skipped} existing  |  ({sym_summary})")
    print(f"  Total known symbols: {len(inventory)}")
    print()

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str]) -> dict:
    args: dict = {
        "domains": None,
        "types":   None,
        "modules": None,
        "dry_run": False,
        "force":   False,
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
        elif tok in ("--modules", "--module") and i + 1 < len(argv):
            i += 1
            args["modules"] = [m.strip() for m in argv[i].split(",") if m.strip()]
        elif tok == "--dry-run":
            args["dry_run"] = True
        elif tok == "--force":
            args["force"] = True
        i += 1
    return args


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    a = _parse_args(argv)
    cmd_index(
        filter_domains = a["domains"] or None,
        filter_types   = a["types"]   or None,
        filter_modules = a["modules"] or None,
        dry_run        = a["dry_run"],
        force          = a["force"],
    )


if __name__ == "__main__":
    main()
