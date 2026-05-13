#!/usr/bin/env python3
"""tag_use_cases.py — Infer use-case tags for AVM modules and write analysis_use_cases blocks.

Reads module YAMLs from data/modules/ and the lookup table from data/use_case_tags.yaml.
Classifies each module using a three-tier signal model:

  Tier 1 — catalog.domain            → base functional tags
  Tier 2 — provider_namespace/resource_type → resource-specific tags (res modules)
  Tier 3 — resources_managed list    → extra tags (filtered; helpers ignored)

Writes a # BEGIN ANALYSIS:use-cases ... # END ANALYSIS:use-cases block into each
module YAML. Does NOT touch enrichment.use_cases (operator-owned).

With --promote: also seeds enrichment.use_cases when it is currently empty ([])
after writing the analysis block.

Usage:
    python3 scripts/tag_use_cases.py [options]
    ./avm.sh tag [options]    # operator alias

Options:
    --modules NAME[,…]    Short module name(s), e.g. avm-res-network-virtualnetwork
    --domains DOMAIN[,…]  Filter by domain (comma-separated)
    --types TYPE[,…]      Filter by type: res, ptn, utl (comma-separated)
    --force               Re-tag even if analysis_use_cases block is already fresh
    --dry-run             Print proposed tags without writing any files
    --promote             Also seed enrichment.use_cases when currently empty
    --tags-file PATH      Path to use_case_tags.yaml (default: data/use_case_tags.yaml)
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT    = os.path.dirname(SCRIPT_DIR)
MODULES_DIR  = os.path.join(REPO_ROOT, "data", "modules")
DEFAULT_TAGS = os.path.join(REPO_ROOT, "data", "use_case_tags.yaml")

ANALYSIS_DIM           = "use-cases"
ANALYSIS_BEGIN         = f"# BEGIN ANALYSIS:{ANALYSIS_DIM}"
ANALYSIS_END           = f"# END ANALYSIS:{ANALYSIS_DIM}"
CATALOG_END            = "# END CATALOG"

# ---------------------------------------------------------------------------
# YAML helpers (stdlib-only readers already used in generate_site.py)
# ---------------------------------------------------------------------------

def _read_raw(path: str) -> str:
    """Read a file, returning empty string on error."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _write_atomic(filepath: str, content: str) -> None:
    """Write content atomically using a temp file in the same directory."""
    dir_path = os.path.dirname(filepath)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
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
# Catalog field extraction
# ---------------------------------------------------------------------------

def _extract_catalog_field(content: str, field: str) -> str:
    """Extract a single flat field from the catalog block."""
    in_catalog = False
    for line in content.splitlines():
        if line.strip() == "# BEGIN CATALOG":
            in_catalog = True
            continue
        if line.strip() == "# END CATALOG":
            break
        if not in_catalog:
            continue
        m = re.match(rf'^  {re.escape(field)}:\s+"?([^"#\n]+)"?', line)
        if m:
            return m.group(1).strip().strip('"')
    return ""


def _extract_resources_managed(content: str) -> list[str]:
    """Extract all resource type names from analysis_terraform_metadata.resources_managed."""
    in_block   = False
    in_section = False
    resources: list[str] = []
    for line in content.splitlines():
        if line.startswith(f"# BEGIN ANALYSIS:terraform-metadata"):
            in_block = True
            continue
        if line.startswith("# END ANALYSIS:terraform-metadata"):
            break
        if not in_block:
            continue
        if re.match(r"^\s{2}resources_managed:", line):
            in_section = True
            continue
        if in_section:
            if re.match(r"^\s{2}\w", line) and not re.match(r"^\s{4}", line):
                # Back to a top-level block key — section ended
                break
            m = re.match(r'^\s{6}-\s+"?([a-z][a-z0-9_]+)"?', line)
            if m:
                resources.append(m.group(1))
    return resources


def _analysis_block_exists(content: str) -> bool:
    return ANALYSIS_BEGIN in content


def _is_enrichment_use_cases_empty(content: str) -> bool:
    """Return True if enrichment.use_cases is currently the empty list []."""
    m = re.search(r"^  use_cases:\s*\[\]", content, re.MULTILINE)
    return m is not None


# ---------------------------------------------------------------------------
# Block I/O (mirrors analyze_module.py pattern)
# ---------------------------------------------------------------------------

def _find_block_span(content: str) -> tuple[int, int] | None:
    begin_re = re.compile(r"^" + re.escape(ANALYSIS_BEGIN) + r"\s*$", re.MULTILINE)
    end_re   = re.compile(r"^" + re.escape(ANALYSIS_END)   + r"\s*$", re.MULTILINE)
    bm = begin_re.search(content)
    if not bm:
        return None
    em = end_re.search(content, bm.end())
    if not em:
        return None
    return bm.start(), em.end()


def _insertion_point(content: str) -> int:
    """Return position to insert a new analysis block.

    Inserts before enrichment: if present, otherwise after # END CATALOG.
    """
    enrich_m = re.search(r"^enrichment:", content, re.MULTILINE)
    if enrich_m:
        return enrich_m.start()
    idx = content.find(CATALOG_END)
    if idx != -1:
        return idx + len(CATALOG_END)
    return len(content)


def _apply_block(content: str, new_block: str) -> str:
    """Replace or insert the analysis_use_cases block."""
    span = _find_block_span(content)
    if span is not None:
        before = content[: span[0]]
        after  = content[span[1]:]
        if after.startswith("\n"):
            return before + new_block + after
        return before + new_block + "\n" + after
    pos = _insertion_point(content)
    return content[:pos] + new_block + "\n" + content[pos:]


def _promote_use_cases(content: str, tags: list[str]) -> str:
    """Seed enrichment.use_cases when it is currently empty."""
    tags_str = "[" + ", ".join(f'"{t}"' for t in tags) + "]"
    return re.sub(
        r"^  use_cases:\s*\[\]",
        f"  use_cases: {tags_str}",
        content,
        count=1,
        flags=re.MULTILINE,
    )


# ---------------------------------------------------------------------------
# Lookup table loader
# ---------------------------------------------------------------------------

def load_tags(path: str) -> dict[str, Any]:
    """Load the use_case_tags.yaml lookup table."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid use_case_tags.yaml format: expected a mapping at top level")
    return {
        "domains":        data.get("domains", {}),
        "resource_types": data.get("resource_types", {}),
        "resources":      data.get("resources", {}),
        "ignore":         set(data.get("ignore", [])),
    }


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify(module: dict[str, str], resources: list[str], lookup: dict[str, Any]) -> list[str]:
    """Return a sorted, deduplicated list of inferred use-case tags.

    Uses a three-tier signal model:
      1. catalog.domain         → base tags
      2. provider_namespace/resource_type → resource-specific tags (res only)
      3. filtered resources_managed → extra tags
    """
    tags: set[str] = set()

    # Tier 1 — domain
    domain = module.get("domain", "")
    for tag in lookup["domains"].get(domain, []):
        tags.add(tag)

    # Tier 2 — provider_namespace/resource_type (res modules only)
    if module.get("type") == "res":
        ns  = module.get("provider_namespace", "").strip().strip('"')
        rt  = module.get("resource_type", "").strip().strip('"')
        if ns and rt:
            key = f"{ns}/{rt}"
            for tag in lookup["resource_types"].get(key, []):
                tags.add(tag)

    # Tier 3 — filtered resources_managed
    ignore = lookup["ignore"]
    for resource in resources:
        if resource in ignore:
            continue
        for tag in lookup["resources"].get(resource, []):
            tags.add(tag)

    return sorted(tags)


# ---------------------------------------------------------------------------
# Block formatter
# ---------------------------------------------------------------------------

def _format_block(tags: list[str], evidence: dict[str, str]) -> str:
    """Render the full # BEGIN ANALYSIS:use-cases ... # END ANALYSIS:use-cases block."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status = "pass" if tags else "unchecked"
    tags_yaml = "[" + ", ".join(f'"{t}"' for t in tags) + "]"

    ev_lines = "\n".join(
        f"    {k}: {v}"
        for k, v in evidence.items()
        if v
    )

    lines = [
        ANALYSIS_BEGIN,
        "analysis_use_cases:",
        f'  checked_at: "{now}"',
        f"  status: {status}",
        f"  inferred_tags: {tags_yaml}",
        "  evidence:",
    ]
    if ev_lines:
        lines.append(ev_lines)
    else:
        lines.append("    (none)")
    lines.append(ANALYSIS_END)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Module discovery
# ---------------------------------------------------------------------------

def _list_module_files(
    filter_modules: list[str] | None,
    filter_domains: list[str] | None,
    filter_types:   list[str] | None,
) -> list[tuple[str, str]]:
    """Return list of (filepath, short_name) for matching modules."""
    results: list[tuple[str, str]] = []
    for mod_type in ("res", "ptn", "utl"):
        if filter_types and mod_type not in filter_types:
            continue
        type_dir = os.path.join(MODULES_DIR, mod_type)
        if not os.path.isdir(type_dir):
            continue
        for fname in sorted(os.listdir(type_dir)):
            if not fname.endswith(".yaml"):
                continue
            short = fname[:-5]
            if filter_modules and short not in filter_modules:
                continue
            filepath = os.path.join(type_dir, fname)
            if filter_domains:
                content = _read_raw(filepath)
                domain  = _extract_catalog_field(content, "domain")
                if domain not in filter_domains:
                    continue
            results.append((filepath, short))
    return results


# ---------------------------------------------------------------------------
# Main tagger
# ---------------------------------------------------------------------------

def tag_modules(
    filter_modules: list[str] | None = None,
    filter_domains: list[str] | None = None,
    filter_types:   list[str] | None = None,
    force:          bool = False,
    dry_run:        bool = False,
    promote:        bool = False,
    tags_file:      str  = DEFAULT_TAGS,
) -> None:
    """Tag all matching modules with inferred use-case tags."""
    if not os.path.isfile(tags_file):
        print(f"[ERROR] Tags file not found: {tags_file}", file=sys.stderr)
        sys.exit(1)

    lookup = load_tags(tags_file)
    files  = _list_module_files(filter_modules, filter_domains, filter_types)

    if not files:
        print("[WARNING] No module files matched the given filters.", file=sys.stderr)
        return

    tagged      = 0
    skipped     = 0
    promoted    = 0
    no_metadata = 0

    for filepath, short_name in files:
        content  = _read_raw(filepath)
        if not content:
            continue

        # Skip if block already exists and not --force
        if not force and _analysis_block_exists(content):
            skipped += 1
            continue

        # Extract catalog fields
        domain   = _extract_catalog_field(content, "domain")
        mod_type = _extract_catalog_field(content, "type") or _infer_type_from_path(filepath)
        prov_ns  = _extract_catalog_field(content, "provider_namespace")
        res_type = _extract_catalog_field(content, "resource_type")

        module_info = {
            "name":               short_name,
            "domain":             domain,
            "type":               mod_type,
            "provider_namespace": prov_ns,
            "resource_type":      res_type,
        }

        # Check for terraform-metadata block (tier 3 requires it)
        resources      = _extract_resources_managed(content)
        has_metadata   = "# BEGIN ANALYSIS:terraform-metadata" in content
        if not has_metadata:
            no_metadata += 1

        # Classify
        tags = classify(module_info, resources, lookup)

        evidence = {}
        if domain:
            evidence["catalog_domain"] = domain
        if prov_ns and res_type and mod_type == "res":
            evidence["catalog_resource_type"] = f"{prov_ns}/{res_type}"
        if resources and has_metadata:
            # Show up to 5 non-ignored resources as evidence
            shown = [r for r in resources if r not in lookup["ignore"]][:5]
            if shown:
                evidence["resources_managed"] = "[" + ", ".join(shown) + "]"

        block = _format_block(tags, evidence)

        if dry_run:
            tag_str = ", ".join(tags) if tags else "(none)"
            prefix  = "  [DRY-RUN]" if dry_run else "  "
            print(f"{prefix} {short_name}")
            print(f"           tags: {tag_str}")
            if promote and tags and _is_enrichment_use_cases_empty(content):
                print(f"           promote: would seed enrichment.use_cases")
            tagged += 1
            continue

        # Apply block update
        new_content = _apply_block(content, block)

        # Optionally seed enrichment.use_cases when empty
        if promote and tags and _is_enrichment_use_cases_empty(new_content):
            new_content = _promote_use_cases(new_content, tags)
            promoted   += 1

        _write_atomic(filepath, new_content)
        tagged += 1
        tag_str = ", ".join(tags[:5]) + ("…" if len(tags) > 5 else "")
        print(f"  ✓  {short_name}  →  [{tag_str}]")

    mode_note = " (dry-run)" if dry_run else ""
    print(
        f"\n  Tagged{mode_note}: {tagged}  |  Skipped (already tagged): {skipped}"
        + (f"  |  Promoted to enrichment: {promoted}" if promote else "")
        + (f"  |  No metadata (tier-3 skipped): {no_metadata}" if no_metadata > 0 else "")
    )


def _infer_type_from_path(filepath: str) -> str:
    """Infer module type from the directory name: res, ptn, utl."""
    parent = os.path.basename(os.path.dirname(filepath))
    if parent in ("res", "ptn", "utl"):
        return parent
    return ""


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> dict:
    args: dict = {
        "modules":      None,
        "domains":      None,
        "types":        None,
        "force":        False,
        "dry_run":      False,
        "promote":      False,
        "tags_file":    DEFAULT_TAGS,
    }
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        elif tok in ("--modules", "--module") and i + 1 < len(argv):
            i += 1
            args["modules"] = [m.strip() for m in argv[i].split(",") if m.strip()]
        elif tok in ("--domains", "--domain") and i + 1 < len(argv):
            i += 1
            args["domains"] = [d.strip() for d in argv[i].split(",") if d.strip() and d.strip() != "all"]
        elif tok in ("--types", "--type") and i + 1 < len(argv):
            i += 1
            args["types"] = [t.strip() for t in argv[i].split(",") if t.strip() and t.strip() != "all"]
        elif tok == "--force":
            args["force"] = True
        elif tok == "--dry-run":
            args["dry_run"] = True
        elif tok == "--promote":
            args["promote"] = True
        elif tok in ("--tags-file", "--tags") and i + 1 < len(argv):
            i += 1
            args["tags_file"] = argv[i]
        i += 1
    return args


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    a = _parse_args(argv)
    tag_modules(
        filter_modules = a["modules"],
        filter_domains = a["domains"],
        filter_types   = a["types"],
        force          = a["force"],
        dry_run        = a["dry_run"],
        promote        = a["promote"],
        tags_file      = a["tags_file"],
    )


if __name__ == "__main__":
    main()
