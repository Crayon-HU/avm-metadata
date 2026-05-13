"""Data loaders for the AVM Intelligence Portal.

The repository intentionally avoids PyYAML, so these parsers read only the
small subset of YAML shapes produced by the repo automation.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .scoring import KEY_TO_DIM

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parent
MODULES_DIR = REPO_ROOT / "data" / "modules"
DATA_DIR = REPO_ROOT / "data"


def read_raw(path: str | Path) -> str:
    """Read a text file, replacing invalid bytes."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _strip_value(value: str) -> str:
    """Normalize a simple YAML scalar."""
    raw = value.strip()
    if " #" in raw:
        raw = raw.split(" #", 1)[0].rstrip()
    return raw.strip().strip('"').strip("'")


def _extract_catalog_fields(content: str) -> dict[str, str]:
    """Extract the catalog scalar fields used by the site."""
    fields: dict[str, str] = {}
    in_catalog = False
    keys = (
        "name",
        "domain",
        "type",
        "status",
        "display_name",
        "repo_url",
        "registry_url",
        "description",
        "first_published",
        "provider",
        "provider_namespace",
        "resource_type",
        "last_synced",
    )
    pattern = re.compile(rf'^  ({"|".join(keys)}):\s*(.*)$')
    for line in content.splitlines():
        if line.strip() == "# BEGIN CATALOG":
            in_catalog = True
            continue
        if line.strip() == "# END CATALOG":
            break
        if not in_catalog:
            continue
        match = pattern.match(line)
        if match:
            fields[match.group(1)] = _strip_value(match.group(2))
    return fields


def _extract_analysis_blocks(content: str) -> dict[str, dict[str, str]]:
    """Return {yaml_key: {status, checked_at}} for each analysis block."""
    results: dict[str, dict[str, str]] = {}
    current_key: str | None = None
    in_block = False
    data: dict[str, str] = {}
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
            match = re.match(r"^(analysis_\w+):", line)
            if match:
                current_key = match.group(1)
            continue
        match = re.match(r'^\s{2}checked_at:\s+"([^"]+)"', line)
        if match:
            data["checked_at"] = match.group(1)
            continue
        match = re.match(r"^\s{2}status:\s+(\S+)", line)
        if match:
            data["status"] = match.group(1)

        match = re.match(r"^\s{2}worst_criticality:\s+(\S+)", line)
        if match:
            data["worst_criticality"] = match.group(1)

    return results


def _extract_mapping_list(content: str, root_key: str) -> dict[str, list[str]]:
    """Extract a provider -> symbol list mapping from an analysis block."""
    result: dict[str, list[str]] = {}
    in_root = False
    current_provider = ""
    for line in content.splitlines():
        if re.match(rf"^\s{{2}}{re.escape(root_key)}:\s*$", line):
            in_root = True
            current_provider = ""
            continue
        if in_root and re.match(r"^\s{2}\w", line):
            break
        if not in_root:
            continue
        provider_match = re.match(r"^\s{4}([A-Za-z0-9_-]+):\s*$", line)
        if provider_match:
            current_provider = provider_match.group(1)
            result.setdefault(current_provider, [])
            continue
        item_match = re.match(r'^\s{6}-\s+"?([^"\n]+)"?\s*$', line)
        if item_match and current_provider:
            result.setdefault(current_provider, []).append(item_match.group(1).strip())
    return result


def _extract_version_pinned(content: str) -> str:
    match = re.search(r'^\s+version_pinned:\s*"([^"]*)"', content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_last_synced(content: str) -> str:
    match = re.search(r'^  last_synced:\s*"([^"]+)"', content, re.MULTILINE)
    return match.group(1)[:10] if match else ""


def _extract_owners(content: str) -> dict[str, dict[str, str]]:
    """Parse catalog owners block."""
    owners: dict[str, dict[str, str]] = {
        "primary": {"handle": "", "name": ""},
        "secondary": {"handle": "", "name": ""},
    }
    in_catalog = False
    in_owners = False
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
                in_owners = False
                continue
            key_match = re.match(r"^\s{4}(primary|secondary):", line)
            if key_match:
                current_key = key_match.group(1)
                continue
            value_match = re.match(r'^\s{6}(handle|name):\s*"?([^"#\n]*)"?', line)
            if value_match and current_key in owners:
                owners[current_key][value_match.group(1)] = _strip_value(
                    value_match.group(2)
                )
    return owners


def load_modules(
    filter_domains: list[str] | None = None,
    filter_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Load module catalog and analysis metadata from data/modules."""
    modules: list[dict[str, Any]] = []
    for mod_type in ("res", "ptn", "utl"):
        if filter_types and mod_type not in filter_types:
            continue
        type_dir = MODULES_DIR / mod_type
        if not type_dir.is_dir():
            continue
        for filepath in sorted(type_dir.glob("*.yaml")):
            content = read_raw(filepath)
            if not content:
                continue
            catalog = _extract_catalog_fields(content)
            domain = catalog.get("domain", "")
            if filter_domains and domain not in filter_domains:
                continue
            raw_analysis = _extract_analysis_blocks(content)
            analysis = {
                KEY_TO_DIM[key]: value
                for key, value in raw_analysis.items()
                if key in KEY_TO_DIM
            }
            modules.append(
                {
                    "name": catalog.get("name", filepath.stem),
                    "domain": domain,
                    "type": catalog.get("type", mod_type),
                    "status": catalog.get("status", ""),
                    "display_name": catalog.get("display_name", ""),
                    "description": catalog.get("description", ""),
                    "repo_url": catalog.get("repo_url", ""),
                    "registry_url": catalog.get("registry_url", ""),
                    "first_published": catalog.get("first_published", ""),
                    "provider": catalog.get("provider", ""),
                    "provider_namespace": catalog.get("provider_namespace", ""),
                    "resource_type": catalog.get("resource_type", ""),
                    "last_synced": _extract_last_synced(content),
                    "version_pinned": _extract_version_pinned(content),
                    "analysis": analysis,
                    "owners": _extract_owners(content),
                    "resources_managed": _extract_mapping_list(
                        content, "resources_managed"
                    ),
                    "datasources_managed": _extract_mapping_list(
                        content, "datasources_managed"
                    ),
                    "_path": str(filepath),
                    "_content": content,
                }
            )
    return modules


def _parse_simple_list_items(lines: list[str], start_index: int) -> list[dict[str, Any]]:
    """Parse a YAML list of dictionaries indented below a known key."""
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    base_indent = None
    for line in lines[start_index:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if base_indent is None:
            match = re.match(r"^(\s*)-\s+", line)
            if not match:
                break
            base_indent = len(match.group(1))
        indent = len(line) - len(line.lstrip(" "))
        if indent < base_indent:
            break
        item_match = re.match(r"^\s*-\s+([A-Za-z0-9_-]+):\s*(.*)$", line)
        if item_match:
            if current:
                items.append(current)
            current = {item_match.group(1): _strip_value(item_match.group(2))}
            continue
        field_match = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*)$", line)
        if field_match and current is not None:
            value = _strip_value(field_match.group(2))
            if value.startswith("[") and value.endswith("]"):
                value = [
                    part.strip().strip('"').strip("'")
                    for part in value[1:-1].split(",")
                    if part.strip()
                ]
            current[field_match.group(1)] = value
            continue
        if current is not None and re.match(r"^\w", line):
            break
    if current:
        items.append(current)
    return items


def _parse_list_under_key(content: str, key: str) -> list[dict[str, Any]]:
    """Parse the first simple list below a key like findings/items/issues."""
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"^\s+{re.escape(key)}:\s*$", line):
            return _parse_simple_list_items(lines, index + 1)
        if re.match(rf"^\s+{re.escape(key)}:\s*\[\]\s*$", line):
            return []
    return []


def _extract_resource_fields(content: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in content.splitlines():
        match = re.match(
            r"^\s{2}(type|provider|symbol_type|registry_url):\s*(.*)$", line
        )
        if match:
            fields[match.group(1)] = _strip_value(match.group(2))
    return fields


def _extract_last_checked(content: str, section: str) -> str:
    in_section = False
    for line in content.splitlines():
        if line.strip() == f"{section}:":
            in_section = True
            continue
        if in_section and re.match(r"^\w", line):
            break
        if in_section:
            match = re.match(r'^\s{2}last_checked:\s*"([^"]+)"', line)
            if match:
                return match.group(1)
    return ""


def load_resources() -> list[dict[str, Any]]:
    """Load resource and datasource provider intelligence stubs."""
    resources: list[dict[str, Any]] = []
    for symbol_dir, symbol_type in (
        (DATA_DIR / "resources", "resource"),
        (DATA_DIR / "datasources", "datasource"),
    ):
        if not symbol_dir.is_dir():
            continue
        for filepath in sorted(symbol_dir.glob("*.yaml")):
            content = read_raw(filepath)
            fields = _extract_resource_fields(content)
            resources.append(
                {
                    "type": fields.get("type", filepath.stem),
                    "provider": fields.get("provider", filepath.stem.split("_", 1)[0]),
                    "symbol_type": fields.get("symbol_type", symbol_type),
                    "registry_url": fields.get("registry_url", ""),
                    "findings": _parse_list_under_key(content, "findings"),
                    "issues": _parse_list_under_key(content, "items"),
                    "updates_last_checked": _extract_last_checked(
                        content, "provider_updates"
                    ),
                    "issues_last_checked": _extract_last_checked(
                        content, "provider_issues"
                    ),
                    "_path": str(filepath),
                }
            )
    return resources


def load_module_issues(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract harvested module issues and enrichment known issues."""
    issues: list[dict[str, Any]] = []
    for module in modules:
        content = module.get("_content", "")
        for item in _parse_list_under_key(content, "issues"):
            issues.append(
                {
                    "source": "module_issues",
                    "module": module["name"],
                    "domain": module.get("domain", ""),
                    "type": module.get("type", ""),
                    "severity": "medium",
                    "status": "open",
                    **item,
                }
            )
        for item in _parse_list_under_key(content, "known_issues"):
            status = item.get("status", "open")
            if status == "resolved":
                continue
            issues.append(
                {
                    "source": "enrichment",
                    "module": module["name"],
                    "domain": module.get("domain", ""),
                    "type": module.get("type", ""),
                    "severity": item.get("severity", "medium"),
                    "status": status,
                    **item,
                }
            )
    return issues


def load_activity() -> dict[str, Any] | None:
    """Read pre-computed activity data if it exists."""
    path = DATA_DIR / "activity.json"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def module_resource_symbols(module: dict[str, Any]) -> set[str]:
    """Return all Terraform resource/data source symbols referenced by a module."""
    symbols: set[str] = set()
    for mapping_key in ("resources_managed", "datasources_managed"):
        for values in module.get(mapping_key, {}).values():
            symbols.update(values)
    return symbols

