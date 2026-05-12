#!/usr/bin/env python3
"""sync_catalog.py — Fetch AVM module indexes and generate/update data/modules/{type}/*.yaml

Each module file has three top-level sections separated by region markers:
  # BEGIN CATALOG ... # END CATALOG      — auto-generated from upstream CSV (this script)
  # BEGIN SCRAPED ... # END SCRAPED      — auto-scraped from GitHub (scripts/scrape_modules.py)
  enrichment:                             — hand-maintained by contributors (never overwritten)

Usage:
    python3 scripts/sync_catalog.py [--dry-run]
    ./avm.sh sync [--dry-run]
"""

import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Sources — official AVM module index CSVs
# ---------------------------------------------------------------------------
SOURCES = [
    (
        "https://raw.githubusercontent.com/Azure/Azure-Verified-Modules/main/docs/static/module-indexes/TerraformResourceModules.csv",
        "res",
    ),
    (
        "https://raw.githubusercontent.com/Azure/Azure-Verified-Modules/main/docs/static/module-indexes/TerraformPatternModules.csv",
        "ptn",
    ),
    (
        "https://raw.githubusercontent.com/Azure/Azure-Verified-Modules/main/docs/static/module-indexes/TerraformUtilityModules.csv",
        "utl",
    ),
]

# Region markers — catalog section (CSV-derived, managed by this script)
BEGIN_MARKER = "# BEGIN CATALOG"
END_MARKER   = "# END CATALOG"

# Region markers — scraped section (GitHub-derived, managed by scrape_modules.py)
SCRAPED_BEGIN_MARKER = "# BEGIN SCRAPED"
SCRAPED_END_MARKER   = "# END SCRAPED"

# Empty scraped placeholder inserted into new files until first scrape
EMPTY_SCRAPED_BLOCK = SCRAPED_BEGIN_MARKER + "\n" + SCRAPED_END_MARKER

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
MODULES_DIR = os.path.join(REPO_ROOT, "data", "modules")

# ---------------------------------------------------------------------------
# Domain and provider derivation
# ---------------------------------------------------------------------------

# ARM provider namespace → functional domain (used for res modules)
NAMESPACE_TO_DOMAIN: dict[str, str] = {
    # Networking
    "Microsoft.Network":             "networking",
    "Microsoft.ServiceNetworking":   "networking",
    "Microsoft.Cdn":                 "networking",
    # Compute
    "Microsoft.Compute":             "compute",
    "Microsoft.HybridCompute":       "compute",
    "Microsoft.Batch":               "compute",
    "Microsoft.VirtualMachineImages":"compute",
    "Microsoft.DevTestLab":          "compute",
    # Containers
    "Microsoft.ContainerService":    "containers",
    "Microsoft.ContainerRegistry":   "containers",
    "Microsoft.ContainerInstance":   "containers",
    "Microsoft.App":                 "containers",
    "Microsoft.RedHatOpenShift":     "containers",
    "Microsoft.HybridContainerService": "containers",
    # Identity & Security
    "Microsoft.ManagedIdentity":     "identity-security",
    "Microsoft.Authorization":       "identity-security",
    "Microsoft.KeyVault":            "identity-security",
    "Microsoft.ManagedServices":     "identity-security",
    "Microsoft.AAD":                 "identity-security",
    # Storage
    "Microsoft.Storage":             "storage",
    "Microsoft.NetApp":              "storage",
    # Monitoring
    "Microsoft.Insights":            "monitoring",
    "Microsoft.OperationalInsights": "monitoring",
    "Microsoft.AlertsManagement":    "monitoring",
    "Microsoft.Dashboard":           "monitoring",
    "Microsoft.OperationsManagement":"monitoring",
    "Microsoft.Consumption":         "monitoring",
    # Management & Governance
    "Microsoft.Resources":           "management",
    "Microsoft.Management":          "management",
    "Microsoft.ResourceGraph":       "management",
    "Microsoft.Maintenance":         "management",
    "Microsoft.Portal":              "management",
    "Microsoft.Features":            "management",
    "Microsoft.Automation":          "management",
    "Microsoft.AppConfiguration":    "management",
    # Recovery & BCDR
    "Microsoft.RecoveryServices":    "recovery-bcdr",
    "Microsoft.DataProtection":      "recovery-bcdr",
    # Web & App Services
    "Microsoft.Web":                 "web-app-services",
    "Microsoft.ApiManagement":       "web-app-services",
    "Microsoft.SignalRService":      "web-app-services",
    "Microsoft.Logic":               "web-app-services",
    "Microsoft.Relay":               "web-app-services",
    "Microsoft.CertificateRegistration": "web-app-services",
    "Microsoft.ServiceFabric":       "web-app-services",
    "Microsoft.Communication":       "web-app-services",
    # Data & Databases
    "Microsoft.Sql":                 "data-databases",
    "Microsoft.SqlVirtualMachine":   "data-databases",
    "Microsoft.DocumentDB":          "data-databases",
    "Microsoft.DBforPostgreSQL":     "data-databases",
    "Microsoft.DBforMySQL":          "data-databases",
    "Microsoft.Cache":               "data-databases",
    "Microsoft.DataFactory":         "data-databases",
    "Microsoft.Synapse":             "data-databases",
    "Microsoft.AnalysisServices":    "data-databases",
    "Microsoft.EventHub":            "data-databases",
    "Microsoft.ServiceBus":          "data-databases",
    "Microsoft.Search":              "data-databases",
    "Microsoft.Databricks":          "data-databases",
    "Microsoft.Kusto":               "data-databases",
    "Microsoft.PowerBIDedicated":    "data-databases",
    "Oracle.Database":               "data-databases",
    "Microsoft.Purview":             "data-databases",
    # AI & ML
    "Microsoft.CognitiveServices":   "ai-ml",
    "Microsoft.MachineLearningServices": "ai-ml",
    "Microsoft.BotService":          "ai-ml",
    "Microsoft.HealthBot":           "ai-ml",
    # Azure Virtual Desktop
    "Microsoft.DesktopVirtualization": "avd",
    # Hybrid / Azure Local
    "Microsoft.AzureStackHCI":       "hybrid",
    "Microsoft.Edge":                "hybrid",
    "Microsoft.DevOpsInfrastructure":"hybrid",
    # IoT & Edge
    "Microsoft.Devices":             "iot",
    "Microsoft.EventGrid":           "iot",
    "Microsoft.IoTOperations":       "iot",
    "Microsoft.DigitalTwins":        "iot",
    "Microsoft.DeviceRegistry":      "iot",
    # Developer Tools
    "Microsoft.DevCenter":           "developer-tools",
    "Microsoft.LoadTestService":     "developer-tools",
    # Other
    "Microsoft.AVS":                 "other",
}

# Pattern module name → domain (explicit mapping; ptn modules have no ARM namespace)
PTN_NAME_TO_DOMAIN: dict[str, str] = {
    "avm-ptn-aca-lza-hosting-environment":                          "containers",
    "avm-ptn-ai-platform-baseline":                                 "ai-ml",
    "avm-ptn-aiml-ai-foundry":                                      "ai-ml",
    "avm-ptn-aiml-ai-gateway":                                      "ai-ml",
    "avm-ptn-aiml-landing-zone":                                    "ai-ml",
    "avm-ptn-aks-dev":                                              "containers",
    "avm-ptn-aks-economy":                                          "containers",
    "avm-ptn-aks-enterprise":                                       "containers",
    "avm-ptn-aks-production":                                       "containers",
    "avm-ptn-alz":                                                  "platform-alz",
    "avm-ptn-alz-application-landing-zone-cicd-bootstrap-azure-devops": "platform-alz",
    "avm-ptn-alz-application-landing-zone-cicd-bootstrap-github":   "platform-alz",
    "avm-ptn-alz-application-landing-zone-identity-and-access":     "platform-alz",
    "avm-ptn-alz-connectivity-hub-and-spoke-vnet":                  "platform-alz",
    "avm-ptn-alz-connectivity-virtual-wan":                         "platform-alz",
    "avm-ptn-alz-identity":                                         "platform-alz",
    "avm-ptn-alz-management":                                       "platform-alz",
    "avm-ptn-alz-policy-exemptions":                                "platform-alz",
    "avm-ptn-alz-sub-vending":                                      "platform-alz",
    "avm-ptn-app-iaas-vm-cosmosdb-tier-four":                       "web-app-services",
    "avm-ptn-app-service-landing-zone":                             "web-app-services",
    "avm-ptn-avd-lza-insights":                                     "avd",
    "avm-ptn-avd-lza-managementplane":                              "avd",
    "avm-ptn-avd-lza-sessionhosts":                                 "avd",
    "avm-ptn-azure-aws-s2s-vpn":                                    "networking",
    "avm-ptn-azure-ipam":                                           "networking",
    "avm-ptn-azureimagebuilder":                                    "compute",
    "avm-ptn-azuremonitorwindowsagent":                             "monitoring",
    "avm-ptn-bcdr-vm-replication":                                  "recovery-bcdr",
    "avm-ptn-botservice-teamsapp":                                  "ai-ml",
    "avm-ptn-cicd-agents-and-runners":                              "developer-tools",
    "avm-ptn-cicd-bootstrap":                                       "developer-tools",
    "avm-ptn-cloudshell-vnet":                                      "networking",
    "avm-ptn-commercial-marketplace":                               "other",
    "avm-ptn-confidential-compute":                                 "compute",
    "avm-ptn-dev-center-dev-box":                                   "developer-tools",
    "avm-ptn-ephemeral-credential":                                 "identity-security",
    "avm-ptn-function-app-storage-private-endpoints":               "web-app-services",
    "avm-ptn-hci-ad-provisioner":                                   "hybrid",
    "avm-ptn-hci-server-provisioner":                               "hybrid",
    "avm-ptn-hubnetworking":                                        "networking",
    "avm-ptn-lbvmss":                                               "compute",
    "avm-ptn-mongodb-atlas-lza":                                    "data-databases",
    "avm-ptn-monitoring-amba-alz":                                  "monitoring",
    "avm-ptn-network-private-link-private-dns-zones":               "networking",
    "avm-ptn-network-routeserver":                                  "networking",
    "avm-ptn-odaa":                                                 "data-databases",
    "avm-ptn-odaa-identity":                                        "identity-security",
    "avm-ptn-openai-cognitivesearch":                               "ai-ml",
    "avm-ptn-openai-e2e-baseline":                                  "ai-ml",
    "avm-ptn-oracle-iaas":                                          "data-databases",
    "avm-ptn-pipeline-agent-container-job":                         "developer-tools",
    "avm-ptn-policyassignment":                                     "management",
    "avm-ptn-purestorage-cbs-array":                                "storage",
    "avm-ptn-sentinel-solutions":                                   "monitoring",
    "avm-ptn-subnets-nsgs-routes":                                  "networking",
    "avm-ptn-subscription-service-health-alerts":                   "monitoring",
    "avm-ptn-virtualwan":                                           "networking",
    "avm-ptn-vnetgateway":                                          "networking",
}

# Utility module name → domain (explicit mapping; utl modules have no ARM namespace)
UTL_NAME_TO_DOMAIN: dict[str, str] = {
    "avm-utl-compute-linuxvirtualmachine-azapi-replicator":              "compute",
    "avm-utl-compute-orchestratedvirtualmachinescaleset-azapi-replicator": "compute",
    "avm-utl-compute-windowsvirtualmachine-azapi-replicator":            "compute",
    "avm-utl-containerregistry-containerregistry-azapi-replicator":      "containers",
    "avm-utl-interfaces":                                                "platform-alz",
    "avm-utl-naming":                                                    "management",
    "avm-utl-network-ip-addresses":                                      "networking",
    "avm-utl-network-subnet-azapi-replicator":                           "networking",
    "avm-utl-network-virtualnetwork-azapi-replicator":                   "networking",
    "avm-utl-privatedns-privatednszone-azapi-replicator":                "networking",
    "avm-utl-regions":                                                   "management",
    "avm-utl-resources-resourcegroup-azapi-replicator":                  "management",
    "avm-utl-roledefinitions":                                           "identity-security",
    "avm-utl-sku-finder":                                                "compute",
}

_PROVIDER_RE = re.compile(r"/terraform-(azurerm|azure|azapi)-avm-")

# Default enrichment block written into new module files
ENRICHMENT_TEMPLATE = """\
enrichment:
  version_pinned: ""         # latest version you have tested/pinned, e.g. "0.7.0"
  terraform_version: ""      # Terraform CLI version tested with, e.g. "1.9.0"
  provider_version: ""       # azurerm/azapi provider version tested with
  use_cases: []              # short tags, e.g. ["alz", "hub-spoke", "landing-zone"]
  known_issues: []
  # known_issues item shape:
  #   - title: "brief description"
  #     status: open           # open | resolved | wontfix
  #     severity: medium       # low | medium | high
  #     workaround: ""         # optional workaround description
  #     url: ""                # optional issue/PR/discussion URL
  notes: []
  # notes item shape:
  #   - date: "YYYY-MM-DD"
  #     author: "github-handle"
  #     content: "free-text observation"
"""


def _module_path(mod: dict) -> str:
    """Return the canonical file path for a module: data/modules/{type}/{name}.yaml"""
    return os.path.join(MODULES_DIR, mod["type"], f"{mod['name']}.yaml")


def _derive_domain(mod: dict) -> str:
    """Derive the functional domain for a module.

    res modules: use NAMESPACE_TO_DOMAIN keyed by provider_namespace.
    ptn/utl modules: use explicit name-based lookup tables.
    Falls back to 'other' for unknown entries.
    """
    if mod["type"] == "res":
        return NAMESPACE_TO_DOMAIN.get(mod.get("provider_namespace", ""), "other")
    if mod["type"] == "ptn":
        return PTN_NAME_TO_DOMAIN.get(mod["name"], "other")
    if mod["type"] == "utl":
        return UTL_NAME_TO_DOMAIN.get(mod["name"], "other")
    return "other"


def _extract_provider(repo_url: str) -> str:
    """Extract the Terraform provider name from a GitHub repo URL.

    Matches the segment between 'terraform-' and '-avm-' in the repo name.
    Returns 'azurerm' as a safe default if the URL pattern is unrecognised.
    """
    m = _PROVIDER_RE.search(repo_url)
    return m.group(1) if m else "azurerm"


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def _s(v: str) -> str:
    """Return a JSON-encoded YAML double-quoted scalar for string v.
    JSON strings are valid YAML double-quoted scalars (same escape rules).
    Empty / n-a values are returned as empty string."""
    if not v or v.strip().lower() in ("n/a", ""):
        return '""'
    return json.dumps(v.strip())


# ---------------------------------------------------------------------------
# CSV fetching and parsing
# ---------------------------------------------------------------------------

def fetch_csv(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:
        # utf-8-sig strips the BOM present on the first column of AVM CSV files
        return resp.read().decode("utf-8-sig")


def parse_modules(csv_text: str, module_type: str) -> list[dict]:
    modules = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        name = row.get("ModuleName", "").strip()
        if not name:
            continue
        modules.append({
            "name":                   name,
            "type":                   module_type,
            "display_name":           row.get("ModuleDisplayName", "").strip(),
            "alternative_names":      row.get("AlternativeNames", "").strip(),
            "status":                 row.get("ModuleStatus", "").strip(),
            "repo_url":               row.get("RepoURL", "").strip(),
            "registry_url":           row.get("PublicRegistryReference", "").strip(),
            "description":            row.get("Description", "").strip(),
            "first_published":        row.get("FirstPublishedIn", "").strip(),
            "comments":               row.get("Comments", "").strip(),
            "owner_primary_handle":   row.get("PrimaryModuleOwnerGHHandle", "").strip(),
            "owner_primary_name":     row.get("PrimaryModuleOwnerDisplayName", "").strip(),
            "owner_secondary_handle": row.get("SecondaryModuleOwnerGHHandle", "").strip(),
            "owner_secondary_name":   row.get("SecondaryModuleOwnerDisplayName", "").strip(),
            # res-only fields
            "provider_namespace":     row.get("ProviderNamespace", "").strip(),
            "resource_type":          row.get("ResourceType", "").strip(),
            "parent_module":          row.get("ParentModule", "").strip(),
        })
    return modules


# ---------------------------------------------------------------------------
# Catalog YAML building
# ---------------------------------------------------------------------------

def build_catalog_section(mod: dict, timestamp: str | None = None) -> str:
    """Build the catalog YAML block (between BEGIN/END CATALOG markers).
    All string scalars are JSON-encoded for safe YAML quoting.
    domain and provider are auto-derived and always written.
    timestamp, when provided, is written as last_synced and is excluded
    from the equality comparison used to detect changes.
    """
    lines = [
        f"# AVM Module — {mod['name']}",
        "# catalog: auto-generated from AVM upstream CSV. Run: ./avm.sh sync to refresh.",
        "# enrichment: hand-maintained — NEVER overwritten by sync.",
        "",
        "catalog:",
        f"  name:         {_s(mod['name'])}",
        f"  type:         {mod['type']}",
        f"  domain:       {_derive_domain(mod)}",
        f"  provider:     {_extract_provider(mod['repo_url'])}",
        f"  display_name: {_s(mod['display_name'])}",
    ]
    if mod["alternative_names"]:
        lines.append(f"  alternative_names: {_s(mod['alternative_names'])}")
    lines += [
        f"  status:       {_s(mod['status'])}",
        f"  repo_url:     {_s(mod['repo_url'])}",
        f"  registry_url: {_s(mod['registry_url'])}",
        f"  description:  {_s(mod['description'])}",
    ]
    if mod["first_published"]:
        lines.append(f"  first_published: {_s(mod['first_published'])}")
    if mod["type"] == "res":
        if mod["provider_namespace"]:
            lines.append(f"  provider_namespace: {_s(mod['provider_namespace'])}")
        if mod["resource_type"]:
            lines.append(f"  resource_type: {_s(mod['resource_type'])}")
        if mod["parent_module"] and mod["parent_module"].lower() not in ("n/a", ""):
            lines.append(f"  parent_module: {_s(mod['parent_module'])}")
    lines += [
        "  owners:",
        "    primary:",
        f"      handle: {_s(mod['owner_primary_handle'])}",
        f"      name:   {_s(mod['owner_primary_name'])}",
        "    secondary:",
        f"      handle: {_s(mod['owner_secondary_handle'])}",
        f"      name:   {_s(mod['owner_secondary_name'])}",
    ]
    if mod["comments"]:
        lines.append(f"  comments: {_s(mod['comments'])}")
    if timestamp is not None:
        lines.append(f"  last_synced: {_s(timestamp)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File read/write helpers
# ---------------------------------------------------------------------------

def get_existing_catalog_content(filepath: str) -> str | None:
    """Return the catalog text between BEGIN/END CATALOG markers, or None if not found.
    The last_synced line is stripped before returning so it is excluded from change detection.
    """
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    begin_idx = content.find(BEGIN_MARKER)
    end_idx   = content.find(END_MARKER)
    if begin_idx == -1 or end_idx == -1:
        return None
    block = content[begin_idx + len(BEGIN_MARKER) : end_idx].strip()
    # Strip last_synced so it doesn't trigger spurious re-writes on every sync
    lines = [l for l in block.splitlines() if not l.strip().startswith("last_synced:")]
    return "\n".join(lines).strip()


def read_existing_scraped_block(filepath: str) -> str | None:
    """Return the full scraped block including markers, or None if not present."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    begin_idx = content.find(SCRAPED_BEGIN_MARKER)
    end_idx   = content.find(SCRAPED_END_MARKER)
    if begin_idx == -1 or end_idx == -1:
        return None
    return content[begin_idx : end_idx + len(SCRAPED_END_MARKER)]


def read_existing_enrichment(filepath: str) -> str | None:
    """Return the enrichment block (everything after END SCRAPED, or END CATALOG if no scraped block)."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Prefer content after END SCRAPED (new file format)
    scraped_end_idx = content.find(SCRAPED_END_MARKER)
    if scraped_end_idx != -1:
        after = content[scraped_end_idx + len(SCRAPED_END_MARKER):].lstrip("\n")
        return after if after.strip() else None
    # Fall back to after END CATALOG (old file format without scraped block)
    end_idx = content.find(END_MARKER)
    if end_idx == -1:
        return None
    after = content[end_idx + len(END_MARKER):].lstrip("\n")
    return after if after.strip() else None


def write_module_file(
    filepath: str,
    catalog_content: str,
    scraped_block: str,
    enrichment_block: str,
) -> None:
    """Write the module file atomically via a temp file + rename.

    File layout:
        # BEGIN CATALOG
        <catalog_content>
        # END CATALOG
        # BEGIN SCRAPED
        [scraped content or empty]
        # END SCRAPED
        <enrichment_block>
    """
    file_content = (
        BEGIN_MARKER + "\n"
        + catalog_content + "\n"
        + END_MARKER + "\n"
        + scraped_block + "\n"
        + enrichment_block + "\n"
    )
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(file_content)
    os.replace(tmp, filepath)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def write_manifest(
    timestamp: str,
    all_modules: list[dict],
    created: int,
    updated: int,
    unchanged: int,
) -> None:
    manifest_path = os.path.join(REPO_ROOT, "data", "catalog-manifest.yaml")
    by_type: dict[str, int]   = {}
    by_status: dict[str, int] = {}
    for m in all_modules:
        by_type[m["type"]]         = by_type.get(m["type"], 0) + 1
        st = m["status"] or "unknown"
        by_status[st.lower()]      = by_status.get(st.lower(), 0) + 1

    lines = [
        "# AVM catalog manifest — auto-generated by sync_catalog.py",
        "# Do not edit manually.",
        f'last_synced: "{timestamp}"',
        f"total: {len(all_modules)}",
        "by_type:",
        f'  res: {by_type.get("res", 0)}',
        f'  ptn: {by_type.get("ptn", 0)}',
        f'  utl: {by_type.get("utl", 0)}',
        "by_status:",
    ]
    for st, cnt in sorted(by_status.items()):
        lines.append(f"  {st}: {cnt}")
    lines += [
        "last_run:",
        f"  created:   {created}",
        f"  updated:   {updated}",
        f"  unchanged: {unchanged}",
    ]
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    dry_run = "--dry-run" in sys.argv
    force   = "--force"   in sys.argv

    # Create subdirectories for each module type
    for t in ("res", "ptn", "utl"):
        os.makedirs(os.path.join(MODULES_DIR, t), exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Fetch and parse all CSVs ─────────────────────────────────────────────
    all_modules: list[dict] = []
    for url, module_type in SOURCES:
        print(f"  ↓ Fetching {module_type} catalog from upstream CSV…")
        try:
            csv_text = fetch_csv(url)
        except Exception as exc:
            print(f"    ERROR: failed to fetch {url}: {exc}", file=sys.stderr)
            sys.exit(1)
        modules = parse_modules(csv_text, module_type)
        print(f"    → {len(modules)} modules")
        all_modules.extend(modules)

    # ── Validate: no duplicate module names ──────────────────────────────────
    names = [m["name"] for m in all_modules]
    dups  = {n for n in names if names.count(n) > 1}
    if dups:
        print(f"ERROR: Duplicate module names in upstream CSV: {dups}", file=sys.stderr)
        sys.exit(1)

    # ── Write/update module files ─────────────────────────────────────────────
    created = updated = unchanged = failed = 0

    for mod in all_modules:
        filepath = _module_path(mod)
        # Migrate from old flat layout (data/modules/{name}.yaml) if present
        old_flat = os.path.join(MODULES_DIR, f"{mod['name']}.yaml")
        if os.path.exists(old_flat) and not os.path.exists(filepath):
            os.rename(old_flat, filepath)

        # Equality check uses catalog without timestamp to avoid spurious re-writes
        catalog_content_cmp   = build_catalog_section(mod)
        catalog_content_write = build_catalog_section(mod, timestamp)
        existing_cat          = get_existing_catalog_content(filepath)
        is_new                = not os.path.exists(filepath)
        needs_write           = force or is_new or (existing_cat != catalog_content_cmp.strip())

        if not needs_write:
            unchanged += 1
            continue

        # Preserve scraped block and enrichment from existing file
        scraped_block    = read_existing_scraped_block(filepath) or EMPTY_SCRAPED_BLOCK
        enrichment_block = read_existing_enrichment(filepath) or ENRICHMENT_TEMPLATE

        action = "CREATE" if is_new else "UPDATE"
        if dry_run:
            print(f"  {action:<6}  {mod['type']}/{mod['name']}.yaml")
        else:
            try:
                write_module_file(filepath, catalog_content_write, scraped_block, enrichment_block)
            except OSError as exc:
                print(f"  ERROR writing {filepath}: {exc}", file=sys.stderr)
                failed += 1
                continue

        if is_new:
            created += 1
        else:
            updated += 1

    # ── Write manifest ────────────────────────────────────────────────────────
    if not dry_run:
        write_manifest(timestamp, all_modules, created, updated, unchanged)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("────────────────────────────────────────────────────────")
    if dry_run:
        print(f"Dry run — would create: {created}, update: {updated}, skip unchanged: {unchanged}")
    else:
        print(f"Done — created: {created}, updated: {updated}, unchanged: {unchanged}, failed: {failed}")
        if created + updated > 0:
            print("Manifest: data/catalog-manifest.yaml")


if __name__ == "__main__":
    main()
