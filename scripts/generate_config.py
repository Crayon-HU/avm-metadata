#!/usr/bin/env python3
"""generate_config.py — Generate .config/modules.yaml from data/modules/ catalog files.

Reads the # BEGIN CATALOG / # END CATALOG block from every data/modules/{res,ptn,utl}/*.yaml
file, extracts the key fields, and writes .config/modules.yaml in the format expected by
scripts/clone_repos.sh and scripts/clone_repos.ps1.

Replaces scripts/generate_modules.sh and scripts/generate_modules.ps1.

Usage:
    python3 scripts/generate_config.py                                  # interactive menus
    python3 scripts/generate_config.py --domains all --types all
    python3 scripts/generate_config.py --domains networking,compute --types res,ptn
    python3 scripts/generate_config.py --domains all --include-deprecated
    python3 scripts/generate_config.py --dry-run
    ./avm.sh setup --domains all
"""

import os
import re
import sys
import tempfile
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
MODULES_DIR = os.path.join(REPO_ROOT, "data", "modules")
OUTPUT_FILE = os.path.join(REPO_ROOT, ".config", "modules.yaml")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALL_TYPES    = ("res", "ptn", "utl")
CATALOG_BEGIN = "# BEGIN CATALOG"
CATALOG_END   = "# END CATALOG"

# Modules whose catalog.status (lowercased) are excluded by default.
# Only "Available" modules are included unless the relevant flag is passed.
EXCLUDED_STATUSES_DEFAULT = {"deprecated", "proposed"}


# ---------------------------------------------------------------------------
# Catalog parsing
# ---------------------------------------------------------------------------

def _strip_quotes(value: str) -> str:
    """Remove surrounding double-quotes from a YAML scalar value if present."""
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


# Fields extracted by simple regex — all live in the flat top level of catalog:
_FIELD_RE = re.compile(
    r"^\s+"                          # indented (inside catalog: block)
    r"(name|type|domain|display_name|description|repo_url|status)"
    r":\s+(.+)$"
)

# Nested fields (owners.primary.name etc.) share the key "name", so we
# stop extracting after we've seen the top-level name field once.
def _parse_catalog_block(block: str) -> dict:
    """
    Extract catalog fields from the text between BEGIN/END CATALOG markers.

    Returns a dict with keys: name, type, domain, display_name, description,
    repo_url, status. Missing fields default to empty string.
    """
    fields: dict[str, str] = {
        "name": "", "type": "", "domain": "", "display_name": "",
        "description": "", "repo_url": "", "status": "",
    }
    seen_name = False  # top-level name is the first occurrence

    for line in block.splitlines():
        m = _FIELD_RE.match(line)
        if not m:
            continue
        key, raw_val = m.group(1), _strip_quotes(m.group(2))
        if key == "name":
            if not seen_name:
                fields["name"] = raw_val
                seen_name = True
            # subsequent name: lines are owner names — skip
        else:
            if not fields[key]:  # first occurrence wins
                fields[key] = raw_val

    return fields


def read_module_catalog(filepath: str) -> dict | None:
    """
    Read a data/modules/*.yaml file and return its catalog fields, or None if
    the file has no valid catalog block.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        print(f"  WARN  cannot read {filepath}: {exc}", file=sys.stderr)
        return None

    begin_idx = content.find(CATALOG_BEGIN)
    end_idx   = content.find(CATALOG_END)
    if begin_idx == -1 or end_idx == -1 or end_idx <= begin_idx:
        return None

    block = content[begin_idx + len(CATALOG_BEGIN): end_idx]
    fields = _parse_catalog_block(block)

    if not fields["name"] or not fields["repo_url"]:
        return None  # not enough data to be useful

    # Derive the full GitHub repo name from the URL (last path component)
    # e.g. "https://github.com/Azure/terraform-azurerm-avm-res-network-virtualnetwork"
    #   → "terraform-azurerm-avm-res-network-virtualnetwork"
    fields["clone_name"] = fields["repo_url"].rstrip("/").rsplit("/", 1)[-1]

    return fields


def discover_modules(types: tuple[str, ...]) -> list[dict]:
    """
    Walk data/modules/{types}/ and return parsed catalog dicts, sorted by
    domain then name.
    """
    modules: list[dict] = []
    for module_type in types:
        type_dir = os.path.join(MODULES_DIR, module_type)
        if not os.path.isdir(type_dir):
            continue
        for fname in sorted(os.listdir(type_dir)):
            if not fname.endswith(".yaml"):
                continue
            fields = read_module_catalog(os.path.join(type_dir, fname))
            if fields:
                modules.append(fields)

    modules.sort(key=lambda m: (m.get("domain", ""), m.get("name", "")))
    return modules


# ---------------------------------------------------------------------------
# Interactive menus
# ---------------------------------------------------------------------------

def _print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def _interactive_domain_menu(available_domains: list[str]) -> list[str]:
    """Prompt user to select domains from a numbered list. Returns selected slugs."""
    print()
    _print_separator("═")
    print("AVM Config Generator — Domain Selection")
    _print_separator("═")
    print()
    for i, slug in enumerate(available_domains, 1):
        print(f"  {i:2})  {slug}")
    print()
    print("Enter numbers separated by spaces, or type 'all'.")
    print()

    while True:
        raw = input("Domain selection: ").strip()
        if not raw:
            print("  No selection — please enter numbers or 'all'.")
            continue
        if raw.lower() == "all":
            return list(available_domains)

        selected: list[str] = []
        valid = True
        for token in raw.split():
            if not token.isdigit():
                print(f"  Invalid input '{token}' — enter numbers only, or 'all'.")
                valid = False
                break
            n = int(token)
            if n < 1 or n > len(available_domains):
                print(f"  Number {n} is out of range (1–{len(available_domains)}).")
                valid = False
                break
            slug = available_domains[n - 1]
            if slug not in selected:
                selected.append(slug)
        if valid and selected:
            return selected


def _interactive_type_menu() -> list[str]:
    """Prompt user to select module types. Returns selected type strings."""
    labels = {
        "res": "Resource  (avm-res-*) — single Azure resource",
        "ptn": "Pattern   (avm-ptn-*) — multi-resource composition",
        "utl": "Utility   (avm-utl-*) — data/schema helpers, no Azure resources",
    }
    print()
    print("Module Types")
    _print_separator()
    for i, t in enumerate(ALL_TYPES, 1):
        print(f"  {i})  {t}  — {labels[t]}")
    print()
    print("Enter numbers separated by spaces, or press Enter / type 'all'.")
    print()

    raw = input("Type selection [all]: ").strip()
    if not raw or raw.lower() == "all":
        return list(ALL_TYPES)

    selected: list[str] = []
    for token in raw.split():
        if not token.isdigit():
            print(f"  WARN  Invalid token '{token}' — skipping", file=sys.stderr)
            continue
        n = int(token)
        if 1 <= n <= len(ALL_TYPES):
            t = ALL_TYPES[n - 1]
            if t not in selected:
                selected.append(t)
        else:
            print(f"  WARN  Number {n} out of range — skipping", file=sys.stderr)

    return selected if selected else list(ALL_TYPES)


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def build_modules_yaml(
    modules: list[dict],
    selected_domains: list[str],
    selected_types: list[str],
    include_deprecated: bool,
    timestamp: str,
    include_proposed: bool = False,
) -> str:
    """
    Build the content of .config/modules.yaml from the filtered module list.
    """
    lines: list[str] = [
        "# AUTO-GENERATED — do not edit manually.",
        "# Source: data/modules/{res,ptn,utl}/*.yaml catalog sections.",
        f"# Re-run: python3 scripts/generate_config.py  (or ./avm.sh setup)",
        f"# Generated: {timestamp}",
        f"# Domains:   {', '.join(selected_domains)}",
        f"# Types:     {', '.join(selected_types)}",
        "#",
        "",
        "modules:",
    ]

    current_domain = None
    count = 0

    for m in modules:
        domain = m.get("domain", "")
        mod_type = m.get("type", "")

        # Apply domain filter
        if selected_domains and domain not in selected_domains:
            continue
        # Apply type filter
        if selected_types and mod_type not in selected_types:
            continue
        # Apply status filter — build the excluded set from defaults minus opt-ins
        excluded = set(EXCLUDED_STATUSES_DEFAULT)
        if include_deprecated:
            excluded.discard("deprecated")
        if include_proposed:
            excluded.discard("proposed")
        if m.get("status", "").lower() in excluded:
            continue

        # Domain section comment
        if domain != current_domain:
            if current_domain is not None:
                lines.append("")
            lines.append(f"  # --- {domain} ---")
            current_domain = domain

        git_url = m["repo_url"].rstrip("/")
        if not git_url.endswith(".git"):
            git_url += ".git"
        description = m.get("display_name") or m.get("description") or m["name"]

        lines.append(f"  - name: {m['clone_name']}")
        lines.append(f"    domain: {domain}")
        lines.append(f"    type: {mod_type}")
        lines.append(f"    url: {git_url}")
        lines.append(f"    branch: main")
        lines.append(f"    description: {description}")
        count += 1

    lines.append("")  # trailing newline
    return "\n".join(lines), count


# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> dict:
    """Minimal hand-rolled arg parser — stdlib only."""
    args = {
        "domains": "",
        "types": "",
        "include_deprecated": False,
        "include_proposed": False,
        "dry_run": False,
    }
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help", "help"):
            _print_usage()
            sys.exit(0)
        elif arg.startswith("--domains="):
            args["domains"] = arg.split("=", 1)[1]
        elif arg == "--domains":
            i += 1
            if i >= len(argv):
                _die("--domains requires a value")
            args["domains"] = argv[i]
        elif arg.startswith("--types="):
            args["types"] = arg.split("=", 1)[1]
        elif arg == "--types":
            i += 1
            if i >= len(argv):
                _die("--types requires a value")
            args["types"] = argv[i]
        elif arg == "--include-deprecated":
            args["include_deprecated"] = True
        elif arg == "--include-proposed":
            args["include_proposed"] = True
        elif arg == "--dry-run":
            args["dry_run"] = True
        else:
            _die(f"Unknown argument: {arg}")
        i += 1
    return args


def _print_usage() -> None:
    print("""
Usage: python3 scripts/generate_config.py [options]

Options:
  --domains <list|all>      Comma-separated domain slugs, or 'all'
  --types <list|all>        Comma-separated types (res,ptn,utl), or 'all'
  --include-deprecated      Also include modules with status=Deprecated
  --include-proposed        Also include modules with status=Proposed
  --dry-run                 Print what would be written; don't write the file
  -h, --help                Show this help

Examples:
  python3 scripts/generate_config.py --domains all
  python3 scripts/generate_config.py --domains networking,compute --types res,ptn
  python3 scripts/generate_config.py --domains all --include-deprecated
  python3 scripts/generate_config.py --domains all --include-proposed
""")


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args(sys.argv[1:])
    dry_run = args["dry_run"]
    include_deprecated = args["include_deprecated"]
    include_proposed   = args["include_proposed"]

    # --- discover all available domains from data/modules ---
    all_modules = discover_modules(ALL_TYPES)
    if not all_modules:
        _die(f"No module catalog files found under {MODULES_DIR}")

    all_domains: list[str] = sorted({m["domain"] for m in all_modules if m.get("domain")})

    # --- resolve domain selection ---
    if args["domains"]:
        raw_domains = args["domains"].strip().lower()
        if raw_domains == "all":
            selected_domains = all_domains
        else:
            selected_domains = []
            for slug in raw_domains.split(","):
                slug = slug.strip()
                if slug not in all_domains:
                    _die(f"Unknown domain '{slug}'. Available: {', '.join(all_domains)}")
                selected_domains.append(slug)
    else:
        selected_domains = _interactive_domain_menu(all_domains)

    if not selected_domains:
        print("No domains selected. Nothing to do.")
        sys.exit(0)

    # --- resolve type selection ---
    if args["types"]:
        raw_types = args["types"].strip().lower()
        if raw_types == "all":
            selected_types = list(ALL_TYPES)
        else:
            selected_types = []
            for t in raw_types.split(","):
                t = t.strip()
                if t not in ALL_TYPES:
                    _die(f"Unknown type '{t}'. Valid: {', '.join(ALL_TYPES)}")
                selected_types.append(t)
    else:
        selected_types = _interactive_type_menu()

    if not selected_types:
        print("No types selected. Nothing to do.")
        sys.exit(0)

    print()
    print(f"Selected domains: {', '.join(selected_domains)}")
    print(f"Selected types:   {', '.join(selected_types)}")
    if include_deprecated:
        print("Including:        deprecated modules")
    if include_proposed:
        print("Including:        proposed modules")
    print()

    # --- build output ---
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content, count = build_modules_yaml(
        all_modules, selected_domains, selected_types, include_deprecated, timestamp,
        include_proposed=include_proposed,
    )

    if count == 0:
        print("No modules matched the selected filters. Nothing written.")
        sys.exit(0)

    # --- dry run ---
    if dry_run:
        print("─" * 60)
        print(f"DRY RUN — would write {count} modules to {OUTPUT_FILE}")
        print("─" * 60)
        print(content)
        return

    # --- atomic write ---
    config_dir = os.path.dirname(OUTPUT_FILE)
    os.makedirs(config_dir, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=config_dir, suffix=".yaml.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp_path, OUTPUT_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise

    print("─" * 60)
    print(f"Done — {count} modules written to {OUTPUT_FILE}")
    print()
    print("Next step:")
    print("  ./avm.sh clone")
    print("  ./avm.sh clone --domain networking")


if __name__ == "__main__":
    main()
