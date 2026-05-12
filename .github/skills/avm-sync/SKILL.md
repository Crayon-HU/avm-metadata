---
name: avm-sync
description: 'Sync AVM module catalog. Use when: checking for new AVM modules, updating module list, refreshing AVM catalog, modules out of date, new terraform-azurerm-avm repos appeared, module archived, update avm-modules.md, update domain yaml config.'
argument-hint: 'Optional: domain to refresh (e.g. "networking") or "all" (default)'
---

# AVM Module Catalog Sync

Keeps `docs/avm-modules.md` and `.config/{domain}.yaml` files up to date with the official AVM module catalog.

## When to Use

- Checking whether new AVM modules have been published
- A module known to exist is missing from the docs or YAML
- A module has been archived and should be marked or removed
- Periodic maintenance refresh of the catalog

---

## Procedure

### Step 1 — Fetch the official module catalog (CSV)

AVM publishes three authoritative module index CSV files in the [`Azure/Azure-Verified-Modules`](https://github.com/Azure/Azure-Verified-Modules) repository. Fetch all three in **parallel** using `fetch_webpage`:

```
https://raw.githubusercontent.com/Azure/Azure-Verified-Modules/main/docs/static/module-indexes/TerraformResourceModules.csv
https://raw.githubusercontent.com/Azure/Azure-Verified-Modules/main/docs/static/module-indexes/TerraformPatternModules.csv
https://raw.githubusercontent.com/Azure/Azure-Verified-Modules/main/docs/static/module-indexes/TerraformUtilityModules.csv
```

> Short alias URLs also work: `https://aka.ms/avm/index/tf/res/csv`, `https://aka.ms/avm/index/tf/ptn/csv`, `https://aka.ms/avm/index/tf/utl/csv`

**CSV schema** (Resource modules — `TerraformResourceModules.csv`):
```
ProviderNamespace, ResourceType, ModuleDisplayName, AlternativeNames, ModuleName, ParentModule,
ModuleStatus, RepoURL, PublicRegistryReference, PrimaryModuleOwnerGHHandle, ..., Description, Comments, FirstPublishedIn
```

**CSV schema** (Pattern and Utility modules):
```
ModuleDisplayName, AlternativeNames, ModuleName, ModuleStatus, RepoURL, PublicRegistryReference,
PrimaryModuleOwnerGHHandle, ..., Description, Comments, FirstPublishedIn
```

Key fields to extract from each row:
- `ModuleName` — short name, e.g. `avm-res-network-virtualnetwork`
- `ModuleStatus` — `Available`, `Proposed`, `Deprecated`, `Orphaned`
- `RepoURL` — full GitHub repo URL, e.g. `https://github.com/Azure/terraform-azure-avm-ptn-alz-sub-vending`
- `Description` — human-readable description

**Derive module type and provider from `RepoURL`:**

```
URL format: https://github.com/Azure/terraform-{provider}-avm-{type}-{suffix}
Provider:   segment between "terraform-" and "-avm-"  → azurerm | azure | azapi
Type:       segment between "-avm-" and the first "-" after it  → res | ptn | utl
```

**Module status handling:**

| Status | Meaning | Include in docs? | Add to YAML? |
|---|---|---|---|
| `Available` | Published on Terraform Registry | ✓ Yes | ✓ Yes |
| `Proposed` | In development — GitHub repo exists, no Terraform release yet | ✓ Yes (informational) | ✗ No |
| `Deprecated` | Archived/superseded — repository still exists | ✓ Yes, marked `_(archived)_` | Comment out in YAML |
| `Orphaned` | No active owner | ✓ Yes (informational) | ✗ No |

### Step 2 — Build current state

Read the existing catalog:
- Parse `docs/avm-modules.md` — collect all module short-names currently listed (the link text, e.g. `avm-res-network-virtualnetwork`)
- Parse `.config/*.yaml` files (skip `modules.yaml`, `workspaces.yaml`) — collect all `name:` values (full repo names, e.g. `terraform-azurerm-avm-res-network-virtualnetwork`)

### Step 3 — Diff

Compare CSV entries vs. current catalog to identify:

| Category | Action |
|---|---|
| **New** — in CSV, not in docs/yaml | Add to docs + yaml (if `Available`) |
| **Deprecated** — CSV `ModuleStatus` is `Deprecated`, docs lacks `_(archived)_` | Update docs marker; comment out in yaml |
| **Removed** — in docs/yaml, not in CSV at all | **Report only** — do NOT auto-delete; may be a GitHub-only archived repo |
| **Unarchived** — archived marker in docs but CSV shows `Available` | Remove `_(archived)_` marker |
| **Wrong URL** — docs/yaml uses wrong provider prefix vs CSV `RepoURL` | Fix to match CSV `RepoURL` |

If the diff is empty, report "catalog is already up to date" and stop.

**Note on GitHub-only archived repos:** Some repos (e.g. `avm-ptn-ai-foundry-enterprise`, `avm-ptn-enterprise-rag`) were never entered into the official CSV. Keep them in docs with `_(archived)_` indefinitely.

### Step 4 — Domain classification

For each **new** module, determine its domain using this mapping.

> **Important:** the provider prefix (`azurerm`, `azure`, `azapi`) is **orthogonal to domain** — classify by the module short-name only.

| Module prefix | Domain yaml | Docs section |
|---|---|---|
| `res-network-*`, `ptn-network-*`, `ptn-alz-connectivity-*`, `ptn-subnets-*`, `ptn-hubnetworking`, `ptn-virtualwan`, `ptn-vnetgateway`, `ptn-azure-ipam`, `utl-network-*`, `utl-privatedns-*` | `networking.yaml` | Networking |
| `res-compute-*`, `res-virtualmachineimages-*`, `ptn-lbvmss`, `ptn-azureimagebuilder`, `ptn-confidential-compute`, `utl-compute-*` | `compute.yaml` | Compute |
| `res-app-*`, `res-containerinstance-*`, `res-containerregistry-*`, `res-containerservice-*`, `res-redhatopenshift-*`, `ptn-aks-*`, `ptn-aca-*` | `containers.yaml` | Containers |
| `res-aad-*`, `res-authorization-*`, `res-keyvault-*`, `res-managedidentity-*`, `ptn-alz-application-landing-zone-*`, `ptn-ephemeral-credential` | `identity.yaml` | Identity & Security |
| `res-storage-*`, `res-netapp-*`, `ptn-function-app-storage-*` | `storage.yaml` | Storage |
| `res-insights-*`, `res-operationalinsights-*`, `res-alertsmanagement-*`, `res-dashboard-grafana`, `ptn-monitoring-*`, `ptn-azuremonitorwindowsagent`, `ptn-subscription-service-health-alerts` | `monitoring.yaml` | Monitoring & Observability |
| `res-resources-*`, `res-appconfiguration-*`, `res-consumption-*`, `res-features-*`, `res-maintenance-*`, `res-management-*`, `res-managedservices-*`, `res-portal-*`, `res-resourcegraph-*`, `res-automation-*`, `ptn-alz-management`, `ptn-policyassignment`, `ptn-cloudshell-*`, `utl-resources-*` | `management.yaml` | Management & Governance |
| `res-recoveryservices-*`, `res-dataprotection-*`, `ptn-bcdr-*` | `recovery.yaml` | Recovery & BCDR |
| `res-web-*`, `res-apimanagement-*`, `res-cdn-*`, `res-certificateregistration-*`, `res-communication-*`, `res-logic-*`, `res-relay-*`, `res-servicenetworking-*` | `web.yaml` | Web & App Services |
| `res-databricks-*`, `res-datafactory-*`, `res-dbform*`, `res-documentdb-*`, `res-sql-*`, `res-sqlvirtualmachine-*`, `res-eventgrid-*`, `res-eventhub-*`, `res-servicebus-*`, `res-cache-*`, `res-batch-*`, `res-kusto-*`, `res-oracledatabase-*`, `res-synapse-*`, `res-analysisservices-*`, `ptn-app-*cosmosdb*`, `ptn-finopstoolkit-*`, `ptn-mongodb-atlas-*`, `ptn-odaa*` | `data.yaml` | Data & Databases |
| `res-cognitiveservices-*`, `res-machinelearningservices-*`, `res-search-*`, `res-botservice-*`, `res-healthbot-*`, `ptn-aiml-*`, `ptn-ai-foundry-*`, `ptn-enterprise-rag`, `ptn-openai-*` | `aiml.yaml` | AI & ML |
| `ptn-alz` (exact), `ptn-alz-sub-vending`, `ptn-cicd-*`, `res-devopsinfrastructure-*`, `utl-interfaces`, `utl-naming`, `utl-regions`, `utl-roledefinitions`, `utl-sku-finder` | `platform.yaml` | Platform & ALZ |
| `res-desktopvirtualization-*`, `ptn-avd-*` | `avd.yaml` | Azure Virtual Desktop (AVD) |
| `res-azurestackhci-*`, `res-hybridcompute-*`, `res-hybridcontainerservice-*`, `res-edge-*`, `ptn-hci-*`, `ptn-azure-local-*` | `hybrid.yaml` | Azure Local & Hybrid |
| `res-deviceregistry-*`, `res-digitaltwins-*`, `res-iotoperations-*` | `iot.yaml` | IoT & Edge |
| `res-devcenter-*`, `res-devtestlab-*`, `res-loadtestservice-*`, `ptn-dev-center-*` | `devtools.yaml` | Developer Tools |
| anything else | _(place in Other / Specialty section)_ | Other / Specialty |

If a new module's domain is ambiguous, ask the user before writing.

### Step 5 — Update `docs/avm-modules.md`

**Table format** — all data tables use three columns:

```markdown
| Module | Provider | Description |
|---|---|---|
| [avm-{type}-{suffix}]({RepoURL from CSV}) | `{provider}` | {Description} |
```

Where `{provider}` is derived from the repo name segment: `azurerm`, `azure`, or `azapi`.

For each **new** module:
1. Identify the correct section (domain heading + type sub-heading `res`/`ptn`/`utl`)
2. Insert a new table row in **alphabetical order** by module short-name
3. Use the `RepoURL` from the CSV as the link target (no `.git` suffix in the URL)
4. Derive a human-readable description from the CSV `Description` field

For each **newly deprecated** module:
- Append ` _(archived)_` to its description cell

For **unarchived** modules:
- Remove the `_(archived)_` suffix

For modules with **wrong provider URLs**:
- Replace the link URL to match `RepoURL` from CSV
- Update the provider column value to match

Update the summary table counts at the top of the file to reflect the new totals.

Update the `Updated:` date in the header to today's date.

### Step 6 — Update `.config/{domain}.yaml`

For each **new `Available`** module that maps to an existing domain yaml:
1. Open the relevant `.config/{domain}.yaml`
2. Append a new module entry using the **exact repo name** from the CSV `RepoURL` field:

```yaml
  - name: terraform-{provider}-avm-{type}-{suffix}   # basename of RepoURL
    type: {res|ptn|utl}
    url: {RepoURL}.git                                # append .git to CSV RepoURL
    branch: main
    description: {human-readable description}
```

> **Critical:** always derive `name` and `url` from the CSV `RepoURL` field — never guess the provider prefix. The three valid prefixes are `terraform-azurerm-avm-*`, `terraform-azure-avm-*`, `terraform-azapi-avm-*`.

3. Do **not** add `workspaces:` — `generate_modules.sh` will inject it on the next `./avm.sh setup` run

For **deprecated** modules already in yaml: add a comment `# archived` above the `- name:` line (do not delete — deletion requires explicit user confirmation).

For modules with **wrong provider URLs** already in yaml: fix both the `name:` and `url:` fields to match the correct provider from `RepoURL`.

### Step 7 — Regenerate workspace files

After updating YAML files, run:

```bash
./avm.sh setup --domains all
```

### Step 8 — Report

Print a summary:

```
AVM Sync — {date}
─────────────────
Added   : {N} modules
Archived: {N} modules marked _(archived)_
Fixed   : {N} modules with wrong provider URL corrected
Removed : {N} modules no longer in catalog (manual review required: ...)
No-change: {N} modules already up to date
```

List each changed module by name. For removed modules, show the full name and ask the user if they want them removed from the yaml files.

---

## Notes

- Fetch all 3 CSV files in parallel for speed
- The official CSV is the **primary source of truth** — prefer it over GitHub HTML scraping
- Module count in the docs header should match the actual table entries after sync
- Do not modify `.config/modules.yaml` or `.config/workspaces.yaml` — these are generated files
- Do not modify `*.code-workspace` files — regenerated by `./avm.sh workspaces`
- `Proposed`-status modules may have GitHub repos but no Terraform Registry releases yet — include in docs but skip in YAML
