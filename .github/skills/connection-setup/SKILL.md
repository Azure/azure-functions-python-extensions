---
name: connection-setup
description: 'Create and configure Connector Namespace connections for the Azure Functions Connector Extension. USE WHEN: setting up a new connector connection, creating a Connector Namespace, authorizing OAuth consent, adding access policies, or configuring deployed app settings. Covers Office365, SharePoint, Teams, and any Microsoft.Web/connections connector. NOT FOR: trigger registration (use trigger-registration skill), extension development, or code generation.'
---

# Connector Namespace Connection Setup

Automates the end-to-end connection lifecycle for connector-triggered Azure Functions.

## When to Use

- Developer needs a new connector connection for local dev or a deployed Function App
- Developer needs to authorize (OAuth consent) a connection
- Developer needs to wire connection URLs into deployed app settings
- Developer needs to grant access policies (CLI identity for local, managed identity for deployed)

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Target subscription and resource group known
- For deployed scenarios: Function App with managed identity enabled
- **Supported regions** for Connector Namespace: `brazilsouth`, `centraluseuap`, `eastus2euap`, `centralusstage`, `eastusstage`. Only the Connector Namespace `location` must be in a supported region; the resource group and Function App can be in any region.

## Procedure

### Step 1: Create or Select Connector Namespace

Check for an existing Connector Namespace in the resource group:

```powershell
$subscriptionId = "<subscription-id>"
$resourceGroup = "<resource-group>"

az rest --method GET `
    --uri "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.Web/connectorGateways?api-version=2026-05-01-preview" `
    -o json | ConvertFrom-Json | Select-Object -ExpandProperty value | Select-Object name
```

If none exists, create one:

```powershell
$namespaceName = "<namespace-name>"
$location = "<supported-region>"  # e.g., centraluseuap

$nsBody = "{`"location`":`"$location`",`"identity`":{`"type`":`"SystemAssigned`"},`"properties`":{}}"
$tempFile = Join-Path $env:TEMP "ns-body.json"
[System.IO.File]::WriteAllText($tempFile, $nsBody)
az rest --method PUT `
    --uri "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.Web/connectorGateways/$namespaceName?api-version=2026-05-01-preview" `
    --body "@$tempFile" --headers "Content-Type=application/json" -o json
Remove-Item $tempFile -ErrorAction SilentlyContinue
```

> **Important:** The Connector Namespace must have a managed identity enabled (`SystemAssigned`) for trigger callback authentication.

### Step 2: Create Connection

```powershell
$connectorName = "<connector-name>"      # e.g., "office365", "sharepointonline", "teams"
$connectionName = "<connection-name>"    # e.g., "office365-conn"

$nsId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.Web/connectorGateways/$namespaceName"
$connBody = "{`"properties`":{`"connectorName`":`"$connectorName`"}}"
$tempFile = Join-Path $env:TEMP "conn-body.json"
[System.IO.File]::WriteAllText($tempFile, $connBody)
az rest --method PUT `
    --uri "https://management.azure.com${nsId}/connections/${connectionName}?api-version=2026-05-01-preview" `
    --body "@$tempFile" --headers "Content-Type=application/json" -o json | ConvertFrom-Json | Select-Object name, @{n='status';e={$_.properties.statuses[0].status}}
Remove-Item $tempFile -ErrorAction SilentlyContinue
```

The connection starts in **Error** state (unauthenticated). Proceed to Step 3.

### Step 3: OAuth Consent (In-Browser)

Retrieve the consent link and open it in the default browser:

```powershell
$consentBody = '{"parameters":[{"redirectUrl":"https://portal.azure.com","parameterName":"token"}]}'
$tempFile = Join-Path $env:TEMP "consent-body.json"
[System.IO.File]::WriteAllText($tempFile, $consentBody)
$result = az rest --method POST `
    --uri "https://management.azure.com${nsId}/connections/${connectionName}/listConsentLinks?api-version=2026-05-01-preview" `
    --body "@$tempFile" --headers "Content-Type=application/json" -o json | ConvertFrom-Json
Remove-Item $tempFile -ErrorAction SilentlyContinue

$link = $result.value[0].link
Start-Process $link
```

After consent, verify the connection status:

```powershell
az rest --method GET `
    --uri "https://management.azure.com${nsId}/connections/${connectionName}?api-version=2026-05-01-preview" `
    -o json | ConvertFrom-Json | Select-Object @{n='status';e={$_.properties.statuses[0].status}}
```

Expected: `Connected`.

### Step 4: Get Connection Runtime URL

```powershell
$conn = az rest --method GET `
    --uri "https://management.azure.com${nsId}/connections/${connectionName}?api-version=2026-05-01-preview" `
    -o json | ConvertFrom-Json
$runtimeUrl = $conn.properties.connectionRuntimeUrl
Write-Output "Runtime URL: $runtimeUrl"
```

### Step 5: Add Access Policies

> **Note:** Access policies are only needed when your function calls connector **actions** at runtime. For **trigger-only** scenarios (function only receives callbacks), skip this step.

#### For local development (Azure CLI identity)

```powershell
$userObjectId = az ad signed-in-user show --query "id" -o tsv
$tenantId = az account show --query "tenantId" -o tsv

$policyBody = "{`"properties`":{`"principal`":{`"type`":`"ActiveDirectory`",`"identity`":{`"objectId`":`"$userObjectId`",`"tenantId`":`"$tenantId`"}}}}"
$tempFile = Join-Path $env:TEMP "policy-body.json"
[System.IO.File]::WriteAllText($tempFile, $policyBody)
az rest --method PUT `
    --uri "https://management.azure.com${nsId}/connections/${connectionName}/accessPolicies/local-dev?api-version=2026-05-01-preview" `
    --body "@$tempFile" --headers "Content-Type=application/json" -o json | ConvertFrom-Json | Select-Object name
Remove-Item $tempFile -ErrorAction SilentlyContinue
```

#### For deployed Function App (system-assigned managed identity)

```powershell
$functionAppName = "<function-app-name>"
$msiObjectId = az functionapp identity show -g $resourceGroup -n $functionAppName --query "principalId" -o tsv
$tenantId = az account show --query "tenantId" -o tsv

$policyBody = "{`"properties`":{`"principal`":{`"type`":`"ActiveDirectory`",`"identity`":{`"objectId`":`"$msiObjectId`",`"tenantId`":`"$tenantId`"}}}}"
$tempFile = Join-Path $env:TEMP "msi-policy-body.json"
[System.IO.File]::WriteAllText($tempFile, $policyBody)
az rest --method PUT `
    --uri "https://management.azure.com${nsId}/connections/${connectionName}/accessPolicies/functionapp-msi?api-version=2026-05-01-preview" `
    --body "@$tempFile" --headers "Content-Type=application/json" -o json | ConvertFrom-Json | Select-Object name
Remove-Item $tempFile -ErrorAction SilentlyContinue
```

> ACL propagation takes 1-5 minutes. If you get 403 errors immediately after adding, wait and retry.

## Supported Connectors

`arm`, `azureblob`, `azureeventgrid`, `azuremonitorlogs`, `office365`, `office365users`, `onedriveforbusiness`, `sharepointonline`, `teams`, `kusto`, `smtp`, `keyvault`, `planner`, `todo`, and any `Microsoft.Web/connections` connector name.

## Next Steps

- **Triggers:** To register polling triggers (e.g., OnNewEmail, OnNewFile), use the [trigger-registration skill](../trigger-registration/SKILL.md).
