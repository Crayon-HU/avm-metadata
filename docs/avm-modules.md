# Azure Verified Modules — Complete Index

> Source: [Azure/Azure-Verified-Modules — official CSV index](https://github.com/Azure/Azure-Verified-Modules/tree/main/docs/static/module-indexes)  
> Total: 204 modules  
> Updated: May 2026 · Sorted alphabetically within each section

**Legend:** _(archived)_ — repository archived, no longer maintained

---

## Table of Contents

| Domain | `res` | `ptn` | `utl` | Total |
|---|---|---|---|---|
| [Networking](#networking) | 30 | 9 | 3 | **42** |
| [Compute](#compute) | 11 | 3 | 3 | **17** |
| [Containers](#containers) | 8 | 5 | — | **13** |
| [Identity & Security](#identity--security) | 4 | 2 | — | **6** |
| [Storage](#storage) | 2 | 1 | — | **3** |
| [Monitoring & Observability](#monitoring--observability) | 13 | 3 | — | **16** |
| [Management & Governance](#management--governance) | 11 | 3 | 1 | **15** |
| [Recovery & BCDR](#recovery--bcdr) | 3 | 1 | — | **4** |
| [Web & App Services](#web--app-services) | 12 | — | — | **12** |
| [Data & Databases](#data--databases) | 25 | 6 | — | **31** |
| [AI & ML](#ai--ml) | 5 | 5 | — | **10** |
| [Platform & ALZ](#platform--alz) | 1 | 4 | 5 | **10** |
| [Azure Virtual Desktop (AVD)](#azure-virtual-desktop-avd) | 4 | 3 | — | **7** |
| [Azure Local & Hybrid](#azure-local--hybrid) | 6 | 3 | — | **9** |
| [IoT & Edge](#iot--edge) | 3 | — | — | **3** |
| [Developer Tools](#developer-tools) | 3 | 1 | — | **4** |
| [Other / Specialty](#other--specialty) | 1 | 1 | — | **2** |
| **Total** | **142** | **50** | **12** | **204** |

---

## Networking

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-network-applicationgateway](https://github.com/Azure/terraform-azurerm-avm-res-network-applicationgateway) | `azurerm` | Application Gateway |
| [avm-res-network-applicationgatewaywebapplicationfirewallpolicy](https://github.com/Azure/terraform-azurerm-avm-res-network-applicationgatewaywebapplicationfirewallpolicy) | `azurerm` | Application Gateway WAF Policy |
| [avm-res-network-applicationsecuritygroup](https://github.com/Azure/terraform-azurerm-avm-res-network-applicationsecuritygroup) | `azurerm` | Application Security Group (ASG) |
| [avm-res-network-azurefirewall](https://github.com/Azure/terraform-azurerm-avm-res-network-azurefirewall) | `azurerm` | Azure Firewall |
| [avm-res-network-bastionhost](https://github.com/Azure/terraform-azurerm-avm-res-network-bastionhost) | `azurerm` | Bastion Host |
| [avm-res-network-connection](https://github.com/Azure/terraform-azurerm-avm-res-network-connection) | `azurerm` | Virtual Network Gateway Connection |
| [avm-res-network-ddosprotectionplan](https://github.com/Azure/terraform-azurerm-avm-res-network-ddosprotectionplan) | `azurerm` | DDoS Protection Plan |
| [avm-res-network-dnsforwardingruleset](https://github.com/Azure/terraform-azurerm-avm-res-network-dnsforwardingruleset) | `azurerm` | DNS Forwarding Ruleset |
| [avm-res-network-dnsresolver](https://github.com/Azure/terraform-azurerm-avm-res-network-dnsresolver) | `azurerm` | DNS Resolver |
| [avm-res-network-dnszone](https://github.com/Azure/terraform-azurerm-avm-res-network-dnszone) | `azurerm` | Public DNS Zone |
| [avm-res-network-expressroutecircuit](https://github.com/Azure/terraform-azurerm-avm-res-network-expressroutecircuit) | `azurerm` | ExpressRoute Circuit |
| [avm-res-network-firewallpolicy](https://github.com/Azure/terraform-azurerm-avm-res-network-firewallpolicy) | `azurerm` | Firewall Policy |
| [avm-res-network-frontdoorwebapplicationfirewallpolicy](https://github.com/Azure/terraform-azurerm-avm-res-network-frontdoorwebapplicationfirewallpolicy) | `azurerm` | Front Door WAF Policy |
| [avm-res-network-ipgroup](https://github.com/Azure/terraform-azurerm-avm-res-network-ipgroup) | `azurerm` | IP Group |
| [avm-res-network-loadbalancer](https://github.com/Azure/terraform-azurerm-avm-res-network-loadbalancer) | `azurerm` | Load Balancer |
| [avm-res-network-localnetworkgateway](https://github.com/Azure/terraform-azurerm-avm-res-network-localnetworkgateway) | `azurerm` | Local Network Gateway |
| [avm-res-network-natgateway](https://github.com/Azure/terraform-azurerm-avm-res-network-natgateway) | `azurerm` | NAT Gateway |
| [avm-res-network-networkinterface](https://github.com/Azure/terraform-azurerm-avm-res-network-networkinterface) | `azurerm` | Network Interface |
| [avm-res-network-networkmanager](https://github.com/Azure/terraform-azurerm-avm-res-network-networkmanager) | `azurerm` | Virtual Network Manager |
| [avm-res-network-networksecuritygroup](https://github.com/Azure/terraform-azurerm-avm-res-network-networksecuritygroup) | `azurerm` | Network Security Group (NSG) |
| [avm-res-network-networkwatcher](https://github.com/Azure/terraform-azurerm-avm-res-network-networkwatcher) | `azurerm` | Network Watcher |
| [avm-res-network-privatednszone](https://github.com/Azure/terraform-azurerm-avm-res-network-privatednszone) | `azurerm` | Private DNS Zone |
| [avm-res-network-privateendpoint](https://github.com/Azure/terraform-azurerm-avm-res-network-privateendpoint) | `azurerm` | Private Endpoint |
| [avm-res-network-privatelinkservice](https://github.com/Azure/terraform-azurerm-avm-res-network-privatelinkservice) | `azurerm` | Private Link Service |
| [avm-res-network-publicipaddress](https://github.com/Azure/terraform-azurerm-avm-res-network-publicipaddress) | `azurerm` | Public IP Address |
| [avm-res-network-publicipprefix](https://github.com/Azure/terraform-azurerm-avm-res-network-publicipprefix) | `azurerm` | Public IP Prefix |
| [avm-res-network-routetable](https://github.com/Azure/terraform-azurerm-avm-res-network-routetable) | `azurerm` | Route Table |
| [avm-res-network-serviceendpointpolicy](https://github.com/Azure/terraform-azurerm-avm-res-network-serviceendpointpolicy) | `azurerm` | Service Endpoint Policy |
| [avm-res-network-trafficmanagerprofile](https://github.com/Azure/terraform-azurerm-avm-res-network-trafficmanagerprofile) | `azurerm` | Traffic Manager Profile |
| [avm-res-network-virtualnetwork](https://github.com/Azure/terraform-azurerm-avm-res-network-virtualnetwork) | `azurerm` | Virtual Network |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-alz-connectivity-hub-and-spoke-vnet](https://github.com/Azure/terraform-azurerm-avm-ptn-alz-connectivity-hub-and-spoke-vnet) | `azurerm` | ALZ Hub and Spoke VNet Connectivity |
| [avm-ptn-alz-connectivity-virtual-wan](https://github.com/Azure/terraform-azurerm-avm-ptn-alz-connectivity-virtual-wan) | `azurerm` | ALZ Virtual WAN Connectivity |
| [avm-ptn-azure-ipam](https://github.com/Azure/terraform-azurerm-avm-ptn-azure-ipam) | `azurerm` | Azure IPAM (IP Address Management) |
| [avm-ptn-hubnetworking](https://github.com/Azure/terraform-azurerm-avm-ptn-hubnetworking) | `azurerm` | Hub Networking _(archived)_ |
| [avm-ptn-network-private-link-private-dns-zones](https://github.com/Azure/terraform-azurerm-avm-ptn-network-private-link-private-dns-zones) | `azurerm` | Private Link Private DNS Zones |
| [avm-ptn-network-routeserver](https://github.com/Azure/terraform-azurerm-avm-ptn-network-routeserver) | `azurerm` | Azure Route Server |
| [avm-ptn-subnets-nsgs-routes](https://github.com/Azure/terraform-azurerm-avm-ptn-subnets-nsgs-routes) | `azurerm` | Subnets, NSGs, and Routes |
| [avm-ptn-virtualwan](https://github.com/Azure/terraform-azurerm-avm-ptn-virtualwan) | `azurerm` | Virtual WAN _(archived)_ |
| [avm-ptn-vnetgateway](https://github.com/Azure/terraform-azurerm-avm-ptn-vnetgateway) | `azurerm` | Virtual Network Gateway _(archived)_ |

### Utility modules (`utl`)

| Module | Provider | Description |
|---|---|---|
| [avm-utl-network-ip-addresses](https://github.com/Azure/terraform-azurerm-avm-utl-network-ip-addresses) | `azurerm` | Network IP Address Calculations |
| [avm-utl-network-virtualnetwork-azapi-replicator](https://github.com/Azure/terraform-azure-avm-utl-network-virtualnetwork-azapi-replicator) | `azure` | Virtual Network AzRM → AzAPI replicator |
| [avm-utl-privatedns-privatednszone-azapi-replicator](https://github.com/Azure/terraform-azure-avm-utl-privatedns-privatednszone-azapi-replicator) | `azure` | Private DNS Zone AzRM → AzAPI replicator |

---

## Compute

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-compute-capacityreservationgroup](https://github.com/Azure/terraform-azurerm-avm-res-compute-capacityreservationgroup) | `azurerm` | Capacity Reservation Group |
| [avm-res-compute-disk](https://github.com/Azure/terraform-azurerm-avm-res-compute-disk) | `azurerm` | Managed Disk |
| [avm-res-compute-diskencryptionset](https://github.com/Azure/terraform-azurerm-avm-res-compute-diskencryptionset) | `azurerm` | Disk Encryption Set |
| [avm-res-compute-gallery](https://github.com/Azure/terraform-azurerm-avm-res-compute-gallery) | `azurerm` | Compute Gallery |
| [avm-res-compute-hostgroup](https://github.com/Azure/terraform-azurerm-avm-res-compute-hostgroup) | `azurerm` | Dedicated Host Group |
| [avm-res-compute-image](https://github.com/Azure/terraform-azurerm-avm-res-compute-image) | `azurerm` | Compute Image |
| [avm-res-compute-proximityplacementgroup](https://github.com/Azure/terraform-azurerm-avm-res-compute-proximityplacementgroup) | `azurerm` | Proximity Placement Group |
| [avm-res-compute-sshpublickey](https://github.com/Azure/terraform-azurerm-avm-res-compute-sshpublickey) | `azurerm` | SSH Public Key |
| [avm-res-compute-virtualmachine](https://github.com/Azure/terraform-azurerm-avm-res-compute-virtualmachine) | `azurerm` | Virtual Machine |
| [avm-res-compute-virtualmachinescaleset](https://github.com/Azure/terraform-azurerm-avm-res-compute-virtualmachinescaleset) | `azurerm` | Virtual Machine Scale Set (VMSS) |
| [avm-res-virtualmachineimages-imagetemplate](https://github.com/Azure/terraform-azurerm-avm-res-virtualmachineimages-imagetemplate) | `azurerm` | VM Image Template (Azure Image Builder) |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-azureimagebuilder](https://github.com/Azure/terraform-azure-avm-ptn-azureimagebuilder) | `azure` | Azure Image Builder Pipeline |
| [avm-ptn-confidential-compute](https://github.com/Azure/terraform-azurerm-avm-ptn-confidential-compute) | `azurerm` | Confidential Compute |
| [avm-ptn-lbvmss](https://github.com/Azure/terraform-azurerm-avm-ptn-lbvmss) | `azurerm` | Load Balancer + VMSS Flex Deployment |

### Utility modules (`utl`)

| Module | Provider | Description |
|---|---|---|
| [avm-utl-compute-linuxvirtualmachine-azapi-replicator](https://github.com/Azure/terraform-azure-avm-utl-compute-linuxvirtualmachine-azapi-replicator) | `azure` | Linux VM AzRM → AzAPI replicator |
| [avm-utl-compute-orchestratedvirtualmachinescaleset-azapi-replicator](https://github.com/Azure/terraform-azure-avm-utl-compute-orchestratedvirtualmachinescaleset-azapi-replicator) | `azure` | VMSS AzRM → AzAPI replicator |
| [avm-utl-compute-windowsvirtualmachine-azapi-replicator](https://github.com/Azure/terraform-azure-avm-utl-compute-windowsvirtualmachine-azapi-replicator) | `azure` | Windows VM AzRM → AzAPI replicator |

---

## Containers

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-app-containerapp](https://github.com/Azure/terraform-azurerm-avm-res-app-containerapp) | `azurerm` | Container App |
| [avm-res-app-job](https://github.com/Azure/terraform-azurerm-avm-res-app-job) | `azurerm` | Container App Job |
| [avm-res-app-managedenvironment](https://github.com/Azure/terraform-azurerm-avm-res-app-managedenvironment) | `azurerm` | Container Apps Managed Environment |
| [avm-res-containerinstance-containergroup](https://github.com/Azure/terraform-azurerm-avm-res-containerinstance-containergroup) | `azurerm` | Container Instance (ACI) |
| [avm-res-containerregistry-registry](https://github.com/Azure/terraform-azurerm-avm-res-containerregistry-registry) | `azurerm` | Container Registry (ACR) |
| [avm-res-containerservice-fleet](https://github.com/Azure/terraform-azurerm-avm-res-containerservice-fleet) | `azurerm` | AKS Fleet |
| [avm-res-containerservice-managedcluster](https://github.com/Azure/terraform-azurerm-avm-res-containerservice-managedcluster) | `azurerm` | AKS Managed Cluster |
| [avm-res-redhatopenshift-openshiftcluster](https://github.com/Azure/terraform-azurerm-avm-res-redhatopenshift-openshiftcluster) | `azurerm` | Red Hat OpenShift Cluster (ARO) |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-aca-lza-hosting-environment](https://github.com/Azure/terraform-azurerm-avm-ptn-aca-lza-hosting-environment) | `azurerm` | Container Apps Landing Zone Accelerator |
| [avm-ptn-aks-dev](https://github.com/Azure/terraform-azurerm-avm-ptn-aks-dev) | `azurerm` | AKS Dev |
| [avm-ptn-aks-economy](https://github.com/Azure/terraform-azurerm-avm-ptn-aks-economy) | `azurerm` | AKS Economy |
| [avm-ptn-aks-enterprise](https://github.com/Azure/terraform-azurerm-avm-ptn-aks-enterprise) | `azurerm` | AKS Enterprise |
| [avm-ptn-aks-production](https://github.com/Azure/terraform-azurerm-avm-ptn-aks-production) | `azurerm` | AKS Production Standard |

---

## Identity & Security

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-aad-domainservice](https://github.com/Azure/terraform-azurerm-avm-res-aad-domainservice) | `azurerm` | Entra ID Domain Services |
| [avm-res-authorization-roleassignment](https://github.com/Azure/terraform-azurerm-avm-res-authorization-roleassignment) | `azurerm` | Role Assignment |
| [avm-res-keyvault-vault](https://github.com/Azure/terraform-azurerm-avm-res-keyvault-vault) | `azurerm` | Key Vault |
| [avm-res-managedidentity-userassignedidentity](https://github.com/Azure/terraform-azurerm-avm-res-managedidentity-userassignedidentity) | `azurerm` | User Assigned Identity |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-alz-application-landing-zone-identity-and-access](https://github.com/Azure/terraform-azurerm-avm-ptn-alz-application-landing-zone-identity-and-access) | `azurerm` | ALZ Application LZ Identity and Access |
| [avm-ptn-ephemeral-credential](https://github.com/Azure/terraform-azure-avm-ptn-ephemeral-credential) | `azure` | Ephemeral Credentials Generator |

---

## Storage

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-netapp-netappaccount](https://github.com/Azure/terraform-azurerm-avm-res-netapp-netappaccount) | `azurerm` | Azure NetApp Files |
| [avm-res-storage-storageaccount](https://github.com/Azure/terraform-azurerm-avm-res-storage-storageaccount) | `azurerm` | Storage Account |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-function-app-storage-private-endpoints](https://github.com/Azure/terraform-azurerm-avm-ptn-function-app-storage-private-endpoints) | `azurerm` | Function App with Private Endpoint Storage |

---

## Monitoring & Observability

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-alertsmanagement-actionrule](https://github.com/Azure/terraform-azurerm-avm-res-alertsmanagement-actionrule) | `azurerm` | Alert Processing Rule (Action Rule) |
| [avm-res-dashboard-grafana](https://github.com/Azure/terraform-azurerm-avm-res-dashboard-grafana) | `azurerm` | Azure Managed Grafana |
| [avm-res-insights-actiongroup](https://github.com/Azure/terraform-azurerm-avm-res-insights-actiongroup) | `azurerm` | Action Group |
| [avm-res-insights-activitylogalert](https://github.com/Azure/terraform-azurerm-avm-res-insights-activitylogalert) | `azurerm` | Activity Log Alert |
| [avm-res-insights-autoscalesetting](https://github.com/Azure/terraform-azurerm-avm-res-insights-autoscalesetting) | `azurerm` | Autoscale Setting |
| [avm-res-insights-component](https://github.com/Azure/terraform-azurerm-avm-res-insights-component) | `azurerm` | Application Insights |
| [avm-res-insights-datacollectionendpoint](https://github.com/Azure/terraform-azurerm-avm-res-insights-datacollectionendpoint) | `azurerm` | Data Collection Endpoint |
| [avm-res-insights-datacollectionrule](https://github.com/Azure/terraform-azurerm-avm-res-insights-datacollectionrule) | `azurerm` | Data Collection Rule |
| [avm-res-insights-logprofile](https://github.com/Azure/terraform-azurerm-avm-res-insights-logprofile) | `azurerm` | Monitor Log Profile |
| [avm-res-insights-metricalert](https://github.com/Azure/terraform-azurerm-avm-res-insights-metricalert) | `azurerm` | Metric Alert |
| [avm-res-insights-privatelinkscope](https://github.com/Azure/terraform-azurerm-avm-res-insights-privatelinkscope) | `azurerm` | Azure Monitor Private Link Scope |
| [avm-res-insights-scheduledqueryrule](https://github.com/Azure/terraform-azurerm-avm-res-insights-scheduledqueryrule) | `azurerm` | Scheduled Query Rule (Log Alert) |
| [avm-res-operationalinsights-workspace](https://github.com/Azure/terraform-azurerm-avm-res-operationalinsights-workspace) | `azurerm` | Log Analytics Workspace |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-azuremonitorwindowsagent](https://github.com/Azure/terraform-azurerm-avm-ptn-azuremonitorwindowsagent) | `azurerm` | Azure Monitor Windows Agent |
| [avm-ptn-monitoring-amba-alz](https://github.com/Azure/terraform-azurerm-avm-ptn-monitoring-amba-alz) | `azurerm` | Azure Monitor Baseline Alerts (AMBA) for ALZ |
| [avm-ptn-subscription-service-health-alerts](https://github.com/Azure/terraform-azurerm-avm-ptn-subscription-service-health-alerts) | `azurerm` | Subscription Service Health Alerts |

---

## Management & Governance

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-appconfiguration-configurationstore](https://github.com/Azure/terraform-azure-avm-res-appconfiguration-configurationstore) | `azure` | App Configuration Store |
| [avm-res-automation-automationaccount](https://github.com/Azure/terraform-azurerm-avm-res-automation-automationaccount) | `azurerm` | Automation Account |
| [avm-res-consumption-budget](https://github.com/Azure/terraform-azurerm-avm-res-consumption-budget) | `azurerm` | Consumption Budget |
| [avm-res-features-feature](https://github.com/Azure/terraform-azurerm-avm-res-features-feature) | `azurerm` | Subscription Feature Registration |
| [avm-res-maintenance-maintenanceconfiguration](https://github.com/Azure/terraform-azurerm-avm-res-maintenance-maintenanceconfiguration) | `azurerm` | Maintenance Configuration |
| [avm-res-management-managementgroup](https://github.com/Azure/terraform-azurerm-avm-res-management-managementgroup) | `azurerm` | Management Group |
| [avm-res-management-servicegroup](https://github.com/Azure/terraform-azurerm-avm-res-management-servicegroup) | `azurerm` | Service Group |
| [avm-res-managedservices-registrationdefinition](https://github.com/Azure/terraform-azurerm-avm-res-managedservices-registrationdefinition) | `azurerm` | Managed Services Registration Definition |
| [avm-res-portal-dashboard](https://github.com/Azure/terraform-azurerm-avm-res-portal-dashboard) | `azurerm` | Azure Portal Dashboard |
| [avm-res-resourcegraph-query](https://github.com/Azure/terraform-azurerm-avm-res-resourcegraph-query) | `azurerm` | Resource Graph Query |
| [avm-res-resources-resourcegroup](https://github.com/Azure/terraform-azurerm-avm-res-resources-resourcegroup) | `azurerm` | Resource Group |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-alz-management](https://github.com/Azure/terraform-azurerm-avm-ptn-alz-management) | `azurerm` | ALZ Management Subscription |
| [avm-ptn-cloudshell-vnet](https://github.com/Azure/terraform-azurerm-avm-ptn-cloudshell-vnet) | `azurerm` | Cloud Shell VNet Integration |
| [avm-ptn-policyassignment](https://github.com/Azure/terraform-azurerm-avm-ptn-policyassignment) | `azurerm` | Policy Assignment |

### Utility modules (`utl`)

| Module | Provider | Description |
|---|---|---|
| [avm-utl-resources-resourcegroup-azapi-replicator](https://github.com/Azure/terraform-azure-avm-utl-resources-resourcegroup-azapi-replicator) | `azure` | Resource Group AzRM → AzAPI replicator |

---

## Recovery & BCDR

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-dataprotection-backupvault](https://github.com/Azure/terraform-azurerm-avm-res-dataprotection-backupvault) | `azurerm` | Backup Vault |
| [avm-res-dataprotection-resourceguard](https://github.com/Azure/terraform-azurerm-avm-res-dataprotection-resourceguard) | `azurerm` | Resource Guard |
| [avm-res-recoveryservices-vault](https://github.com/Azure/terraform-azurerm-avm-res-recoveryservices-vault) | `azurerm` | Recovery Services Vault |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-bcdr-vm-replication](https://github.com/Azure/terraform-azurerm-avm-ptn-bcdr-vm-replication) | `azurerm` | Site Recovery VM Replication |

---

## Web & App Services

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-apimanagement-service](https://github.com/Azure/terraform-azurerm-avm-res-apimanagement-service) | `azurerm` | API Management Service |
| [avm-res-cdn-profile](https://github.com/Azure/terraform-azurerm-avm-res-cdn-profile) | `azurerm` | CDN Profile (Azure Front Door / CDN) |
| [avm-res-certificateregistration-certificateorder](https://github.com/Azure/terraform-azurerm-avm-res-certificateregistration-certificateorder) | `azurerm` | App Service Certificate Order |
| [avm-res-communication-emailservice](https://github.com/Azure/terraform-azurerm-avm-res-communication-emailservice) | `azurerm` | Email Communication Service |
| [avm-res-logic-workflow](https://github.com/Azure/terraform-azurerm-avm-res-logic-workflow) | `azurerm` | Logic Apps Workflow |
| [avm-res-relay-namespace](https://github.com/Azure/terraform-azurerm-avm-res-relay-namespace) | `azurerm` | Azure Relay Namespace |
| [avm-res-servicenetworking-trafficcontroller](https://github.com/Azure/terraform-azurerm-avm-res-servicenetworking-trafficcontroller) | `azurerm` | Application Gateway for Containers |
| [avm-res-web-connection](https://github.com/Azure/terraform-azurerm-avm-res-web-connection) | `azurerm` | API Connection |
| [avm-res-web-hostingenvironment](https://github.com/Azure/terraform-azurerm-avm-res-web-hostingenvironment) | `azurerm` | App Service Environment (ASE) |
| [avm-res-web-serverfarm](https://github.com/Azure/terraform-azurerm-avm-res-web-serverfarm) | `azurerm` | App Service Plan |
| [avm-res-web-site](https://github.com/Azure/terraform-azurerm-avm-res-web-site) | `azurerm` | Web App / Function App |
| [avm-res-web-staticsite](https://github.com/Azure/terraform-azurerm-avm-res-web-staticsite) | `azurerm` | Static Web App |

---

## Data & Databases

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-analysisservices-server](https://github.com/Azure/terraform-azurerm-avm-res-analysisservices-server) | `azurerm` | Analysis Services Server |
| [avm-res-batch-batchaccount](https://github.com/Azure/terraform-azurerm-avm-res-batch-batchaccount) | `azurerm` | Batch Account |
| [avm-res-cache-redis](https://github.com/Azure/terraform-azurerm-avm-res-cache-redis) | `azurerm` | Redis Cache |
| [avm-res-cache-redisenterprise](https://github.com/Azure/terraform-azurerm-avm-res-cache-redisenterprise) | `azurerm` | Redis Enterprise |
| [avm-res-databricks-accessconnector](https://github.com/Azure/terraform-azurerm-avm-res-databricks-accessconnector) | `azurerm` | Databricks Access Connector |
| [avm-res-databricks-workspace](https://github.com/Azure/terraform-azurerm-avm-res-databricks-workspace) | `azurerm` | Databricks Workspace |
| [avm-res-datafactory-factory](https://github.com/Azure/terraform-azurerm-avm-res-datafactory-factory) | `azurerm` | Data Factory |
| [avm-res-dbformysql-flexibleserver](https://github.com/Azure/terraform-azurerm-avm-res-dbformysql-flexibleserver) | `azurerm` | MySQL Flexible Server |
| [avm-res-dbforpostgresql-flexibleserver](https://github.com/Azure/terraform-azurerm-avm-res-dbforpostgresql-flexibleserver) | `azurerm` | PostgreSQL Flexible Server |
| [avm-res-documentdb-databaseaccount](https://github.com/Azure/terraform-azurerm-avm-res-documentdb-databaseaccount) | `azurerm` | Cosmos DB Account |
| [avm-res-documentdb-mongocluster](https://github.com/Azure/terraform-azurerm-avm-res-documentdb-mongocluster) | `azurerm` | Cosmos DB for MongoDB (vCore) |
| [avm-res-eventgrid-domain](https://github.com/Azure/terraform-azurerm-avm-res-eventgrid-domain) | `azurerm` | Event Grid Domain |
| [avm-res-eventgrid-namespace](https://github.com/Azure/terraform-azurerm-avm-res-eventgrid-namespace) | `azurerm` | Event Grid Namespace |
| [avm-res-eventgrid-systemtopic](https://github.com/Azure/terraform-azurerm-avm-res-eventgrid-systemtopic) | `azurerm` | Event Grid System Topic |
| [avm-res-eventgrid-topic](https://github.com/Azure/terraform-azurerm-avm-res-eventgrid-topic) | `azurerm` | Event Grid Topic |
| [avm-res-eventhub-namespace](https://github.com/Azure/terraform-azurerm-avm-res-eventhub-namespace) | `azurerm` | Event Hub Namespace |
| [avm-res-kusto-cluster](https://github.com/Azure/terraform-azurerm-avm-res-kusto-cluster) | `azurerm` | Azure Data Explorer (Kusto) Cluster |
| [avm-res-oracledatabase-autonomous](https://github.com/Azure/terraform-azurerm-avm-res-oracledatabase-autonomous) | `azurerm` | Oracle Autonomous Database |
| [avm-res-oracledatabase-cloudexadatainfrastructure](https://github.com/Azure/terraform-azurerm-avm-res-oracledatabase-cloudexadatainfrastructure) | `azurerm` | Oracle Exadata Infrastructure |
| [avm-res-oracledatabase-cloudvmcluster](https://github.com/Azure/terraform-azurerm-avm-res-oracledatabase-cloudvmcluster) | `azurerm` | Oracle VM Cluster |
| [avm-res-servicebus-namespace](https://github.com/Azure/terraform-azurerm-avm-res-servicebus-namespace) | `azurerm` | Service Bus Namespace |
| [avm-res-sql-managedinstance](https://github.com/Azure/terraform-azurerm-avm-res-sql-managedinstance) | `azurerm` | SQL Managed Instance |
| [avm-res-sql-server](https://github.com/Azure/terraform-azurerm-avm-res-sql-server) | `azurerm` | Azure SQL Server |
| [avm-res-sqlvirtualmachine-sqlvirtualmachine](https://github.com/Azure/terraform-azurerm-avm-res-sqlvirtualmachine-sqlvirtualmachine) | `azurerm` | SQL Virtual Machine |
| [avm-res-synapse-workspace](https://github.com/Azure/terraform-azurerm-avm-res-synapse-workspace) | `azurerm` | Synapse Analytics Workspace |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-app-iaas-vm-cosmosdb-tier-four](https://github.com/Azure/terraform-azurerm-avm-ptn-app-iaas-vm-cosmosdb-tier-four) | `azurerm` | IaaS VM + Cosmos DB Tier 4 Application |
| [avm-ptn-app-paas-ase-cosmosdb-tier-four](https://github.com/Azure/terraform-azurerm-avm-ptn-app-paas-ase-cosmosdb-tier-four) | `azurerm` | PaaS ASE + Cosmos DB Tier 4 Application |
| [avm-ptn-finopstoolkit-finopshub](https://github.com/Azure/terraform-azurerm-avm-ptn-finopstoolkit-finopshub) | `azurerm` | FinOps Toolkit FinOps Hub |
| [avm-ptn-mongodb-atlas-lza](https://github.com/Azure/terraform-azurerm-avm-ptn-mongodb-atlas-lza) | `azurerm` | MongoDB Atlas Landing Zone |
| [avm-ptn-odaa](https://github.com/Azure/terraform-azurerm-avm-ptn-odaa) | `azurerm` | Oracle Exadata Workload (ODAA) |
| [avm-ptn-odaa-identity](https://github.com/Azure/terraform-azurerm-avm-ptn-odaa-identity) | `azurerm` | Oracle Database @ Azure Identity |

---

## AI & ML

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-botservice-botservice](https://github.com/Azure/terraform-azurerm-avm-res-botservice-botservice) | `azurerm` | Bot Service |
| [avm-res-cognitiveservices-account](https://github.com/Azure/terraform-azurerm-avm-res-cognitiveservices-account) | `azurerm` | Cognitive Services / Azure OpenAI |
| [avm-res-healthbot-healthbot](https://github.com/Azure/terraform-azurerm-avm-res-healthbot-healthbot) | `azurerm` | Health Bot |
| [avm-res-machinelearningservices-workspace](https://github.com/Azure/terraform-azurerm-avm-res-machinelearningservices-workspace) | `azurerm` | Machine Learning Workspace |
| [avm-res-search-searchservice](https://github.com/Azure/terraform-azurerm-avm-res-search-searchservice) | `azurerm` | AI Search Service |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-ai-foundry-enterprise](https://github.com/Azure/terraform-azurerm-avm-ptn-ai-foundry-enterprise) | `azurerm` | AI Foundry Enterprise _(archived)_ |
| [avm-ptn-aiml-ai-foundry](https://github.com/Azure/terraform-azurerm-avm-ptn-aiml-ai-foundry) | `azurerm` | Azure AI Foundry |
| [avm-ptn-aiml-landing-zone](https://github.com/Azure/terraform-azurerm-avm-ptn-aiml-landing-zone) | `azurerm` | AI/ML Landing Zone |
| [avm-ptn-enterprise-rag](https://github.com/Azure/terraform-azurerm-avm-ptn-enterprise-rag) | `azurerm` | Enterprise RAG _(archived)_ |
| [avm-ptn-openai-cognitivesearch](https://github.com/Azure/terraform-azurerm-avm-ptn-openai-cognitivesearch) | `azurerm` | OpenAI + Cognitive Search ChatBot |

---

## Platform & ALZ

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-devopsinfrastructure-pool](https://github.com/Azure/terraform-azurerm-avm-res-devopsinfrastructure-pool) | `azurerm` | Managed DevOps Pools |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-alz](https://github.com/Azure/terraform-azurerm-avm-ptn-alz) | `azurerm` | Azure Landing Zone (Core) |
| [avm-ptn-alz-sub-vending](https://github.com/Azure/terraform-azure-avm-ptn-alz-sub-vending) | `azure` | ALZ Subscription Vending |
| [avm-ptn-cicd-agents-and-runners](https://github.com/Azure/terraform-azurerm-avm-ptn-cicd-agents-and-runners) | `azurerm` | CI/CD Agents and Runners |
| [avm-ptn-cicd-bootstrap](https://github.com/Azure/terraform-azurerm-avm-ptn-cicd-bootstrap) | `azurerm` | CI/CD Bootstrap |

### Utility modules (`utl`)

| Module | Provider | Description |
|---|---|---|
| [avm-utl-interfaces](https://github.com/Azure/terraform-azure-avm-utl-interfaces) | `azure` | AVM Interfaces — shared input variable schemas |
| [avm-utl-naming](https://github.com/Azure/terraform-azurerm-avm-utl-naming) | `azurerm` | AVM Naming Conventions |
| [avm-utl-regions](https://github.com/Azure/terraform-azurerm-avm-utl-regions) | `azurerm` | Azure Regions Data |
| [avm-utl-roledefinitions](https://github.com/Azure/terraform-azure-avm-utl-roledefinitions) | `azure` | Azure Role Definitions |
| [avm-utl-sku-finder](https://github.com/Azure/terraform-azapi-avm-utl-sku-finder) | `azapi` | AVM SKU Finder |

---

## Azure Virtual Desktop (AVD)

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-desktopvirtualization-applicationgroup](https://github.com/Azure/terraform-azurerm-avm-res-desktopvirtualization-applicationgroup) | `azurerm` | AVD Application Group |
| [avm-res-desktopvirtualization-hostpool](https://github.com/Azure/terraform-azurerm-avm-res-desktopvirtualization-hostpool) | `azurerm` | AVD Host Pool |
| [avm-res-desktopvirtualization-scalingplan](https://github.com/Azure/terraform-azurerm-avm-res-desktopvirtualization-scalingplan) | `azurerm` | AVD Scaling Plan |
| [avm-res-desktopvirtualization-workspace](https://github.com/Azure/terraform-azurerm-avm-res-desktopvirtualization-workspace) | `azurerm` | AVD Workspace |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-avd-lza-insights](https://github.com/Azure/terraform-azurerm-avm-ptn-avd-lza-insights) | `azurerm` | AVD LZA Insights |
| [avm-ptn-avd-lza-managementplane](https://github.com/Azure/terraform-azurerm-avm-ptn-avd-lza-managementplane) | `azurerm` | AVD LZA Management Plane |
| [avm-ptn-avd-lza-sessionhosts](https://github.com/Azure/terraform-azurerm-avm-ptn-avd-lza-sessionhosts) | `azurerm` | AVD LZA Session Hosts |

---

## Azure Local & Hybrid

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-azurestackhci-cluster](https://github.com/Azure/terraform-azurerm-avm-res-azurestackhci-cluster) | `azurerm` | Azure Stack HCI Cluster |
| [avm-res-azurestackhci-logicalnetwork](https://github.com/Azure/terraform-azurerm-avm-res-azurestackhci-logicalnetwork) | `azurerm` | Azure Stack HCI Logical Network |
| [avm-res-azurestackhci-virtualmachineinstance](https://github.com/Azure/terraform-azurerm-avm-res-azurestackhci-virtualmachineinstance) | `azurerm` | Azure Stack HCI VM Instance |
| [avm-res-edge-site](https://github.com/Azure/terraform-azurerm-avm-res-edge-site) | `azurerm` | Azure Arc Site Manager |
| [avm-res-hybridcompute-machine](https://github.com/Azure/terraform-azurerm-avm-res-hybridcompute-machine) | `azurerm` | Arc-enabled Server (Hybrid Compute Machine) |
| [avm-res-hybridcontainerservice-provisionedclusterinstance](https://github.com/Azure/terraform-azurerm-avm-res-hybridcontainerservice-provisionedclusterinstance) | `azurerm` | AKS on Azure Local (AKS Arc) |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-azure-local-migrate](https://github.com/Azure/terraform-azurerm-avm-ptn-azure-local-migrate) | `azurerm` | Azure Local Migrate Project |
| [avm-ptn-hci-ad-provisioner](https://github.com/Azure/terraform-azurerm-avm-ptn-hci-ad-provisioner) | `azurerm` | HCI Active Directory Registration |
| [avm-ptn-hci-server-provisioner](https://github.com/Azure/terraform-azurerm-avm-ptn-hci-server-provisioner) | `azurerm` | HCI Server Registration |

---

## IoT & Edge

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-deviceregistry-assetendpointprofile](https://github.com/Azure/terraform-azurerm-avm-res-deviceregistry-assetendpointprofile) | `azurerm` | Device Registry Asset Endpoint Profile (AKRI) |
| [avm-res-digitaltwins-digitaltwinsinstance](https://github.com/Azure/terraform-azurerm-avm-res-digitaltwins-digitaltwinsinstance) | `azurerm` | Azure Digital Twins |
| [avm-res-iotoperations-instance](https://github.com/Azure/terraform-azurerm-avm-res-iotoperations-instance) | `azurerm` | IoT Operations Instance |

---

## Developer Tools

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-devcenter-devcenter](https://github.com/Azure/terraform-azurerm-avm-res-devcenter-devcenter) | `azurerm` | Dev Center |
| [avm-res-devtestlab-lab](https://github.com/Azure/terraform-azurerm-avm-res-devtestlab-lab) | `azurerm` | Dev/Test Lab |
| [avm-res-loadtestservice-loadtest](https://github.com/Azure/terraform-azurerm-avm-res-loadtestservice-loadtest) | `azurerm` | Azure Load Testing |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-dev-center-dev-box](https://github.com/Azure/terraform-azurerm-avm-ptn-dev-center-dev-box) | `azurerm` | Dev Center Dev Box |

---

## Other / Specialty

Modules that do not map to a primary domain above.

### Resource modules (`res`)

| Module | Provider | Description |
|---|---|---|
| [avm-res-avs-privatecloud](https://github.com/Azure/terraform-azurerm-avm-res-avs-privatecloud) | `azurerm` | Azure VMware Solution (AVS) Private Cloud |

### Pattern modules (`ptn`)

| Module | Provider | Description |
|---|---|---|
| [avm-ptn-commercial-marketplace](https://github.com/Azure/terraform-azurerm-avm-ptn-commercial-marketplace) | `azurerm` | Commercial Marketplace |
