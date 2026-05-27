---
name: trigger-registration
description: 'Register Connector Namespace trigger configs for Azure Functions with the ConnectorTrigger extension. USE WHEN: setting up polling triggers (e.g., OnNewEmail, OnNewFile) that call back to an Azure Function, scaffolding a new Function App project with ConnectorTrigger, wiring callback URLs, or troubleshooting trigger configs. NOT FOR: connection setup (use connection-setup skill), extension internals development.'
---

# Connector Trigger Registration for Azure Functions

Registers polling trigger configs on a Connector Namespace so that connector events (new email, new file, etc.) call back to your Azure Function via the ConnectorTrigger extension.

## When to Use

- Developer needs a connector trigger (e.g., "when a new email arrives in Office365")
- Developer has an existing Connector Namespace connection (use the `connection-setup` skill first if not)
- Developer needs to scaffold a new Function App project with `[ConnectorTrigger]`
- Developer needs to wire the callback URL from a deployed or local Function App

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Connector Namespace with a connected connector (see `connection-setup` skill)
- The Connector Namespace must have a **system-assigned managed identity** enabled
- **Supported regions** for Connector Namespace: `westcentralus`

## Key Concepts

### Extension Webhook Endpoint

The connector extension (`Microsoft.Azure.Functions.Worker.Extensions.Connector` for isolated worker — recommended; `Microsoft.Azure.Functions.Extensions.Connector` for in-process) registers a webhook route on the Function App:

```text
POST /runtime/webhooks/connector?functionName={FunctionName}&code={connector_extension_key}
```

- `functionName` must exactly match the `[Function("...")]` attribute name
- `connector_extension` is a system key auto-generated when the extension loads
- Locally (`func start`), the system key is not enforced

### Trigger Config vs Connection

```text
Connector Namespace
├── connections/
│   └── office365-conn         ← auth + runtime URL (connection-setup skill)
└── triggerConfigs/
    └── onnewemail-trigger     ← poll + callback config (THIS skill)
```

## Scaffolding a New Function App Project

### 1. Initialize with azd

#### .NET

```shell
azd init -t functions-quickstart-dotnet-azd
```

#### Python

```shell
azd init -t functions-quickstart-python-azd
```

#### TypeScript

```shell
azd init -t functions-quickstart-typescript-azd
```

#### JavaScript

```shell
azd init -t functions-quickstart-javascript-azd
```

> **Note:** The `azd init` templates create a `host.json` file. For non-.NET languages (Node.js, Python, etc.), update `host.json` to use the **experimental extension bundle** version 4.6.0 or greater:
> ```json
> {
>     "version": "2.0",
>     "extensionBundle": {
>         "id": "Microsoft.Azure.Functions.ExtensionBundle.Experimental",
>         "version": "[4.6.0, 5.0.0)"
>     }
> }
> ```

### 2. Install connector packages

Add the connector extension and SDK packages:

#### .NET

Install the latest pre-release NuGet packages:

```bash
# Connector trigger binding for the isolated worker (recommended)
dotnet add package Microsoft.Azure.Functions.Worker.Extensions.Connector --prerelease

# Connector SDK (typed payloads and action clients)
dotnet add package Azure.Connectors.Sdk --prerelease
```

> **In-proc customers only:** if you are still on the .NET in-process model, replace `Microsoft.Azure.Functions.Worker.Extensions.Connector` with `Microsoft.Azure.Functions.Extensions.Connector`. The isolated worker (above) is the recommended path for new projects.

#### Python

Add to `requirements.txt` (include packages based on your approach):

```text
# >=2.2.0b4 only required for @app.connector_trigger decorator (Python 3.13+ only), regular azure-functions is enough for generic_trigger
azure-functions>=2.2.0b4

# Currently only supports Office 365 OnNewEmail operation
azurefunctions-extensions-connectors

# Required for @app.generic_trigger with typed SDK models or str payloads, don't include if using azurefunctions-extensions-connectors 
azure-connectors
```

#### TypeScript / JavaScript

```bash
npm install @azure/functions@4.15.1-preview
npm install @azure/functions-extensions-connectors@0.0.1-preview
npm install @azure/connectors
```

### 3. Replace the HTTP trigger with a ConnectorTrigger function

Delete any sample HTTP trigger functions and replace with:

#### .NET

```csharp
using Microsoft.Azure.Functions.Worker.Extensions.Connector;
using Azure.Connectors.Sdk.Office365.Models;

[Function("OnNewEmail")]
public void OnNewEmail(
    [ConnectorTrigger]
    Office365OnNewEmailTriggerPayload payload)
{
    _logger.LogInformation("From: {From}, Subject: {Subject}",
        payload.From, payload.Subject);
}
```

#### Python

```python
import azure.functions as func
import azurefunctions.extensions.connectors.office365 as office365
import logging
from typing import List

app = func.FunctionApp()

@app.function_name(name="OnNewEmail")
@app.connector_trigger(arg_name="emails")
def on_new_email(emails: List[office365.ClientReceiveMessage]) -> None:
    logging.info("OnNewEmail trigger received")

    for email in emails:
        logging.info(f"Subject: {email.subject}")
        logging.info(f"From: {email.from_}")
```

#### TypeScript

```typescript
import { app, InvocationContext } from "@azure/functions";

app.generic("OnNewEmail", {
  trigger: { type: "connectorTrigger", name: "payload" },
  handler: async (payload: unknown, context: InvocationContext) => {
    const data = typeof payload === "string" ? JSON.parse(payload) : payload;
    for (const email of data?.body?.value ?? []) {
      context.log(`From: ${email.from}, Subject: ${email.subject}`);
    }
  },
});
```

**OneDrive for Business example (OnNewFile trigger):**

```typescript
import { app, InvocationContext } from "@azure/functions";

app.generic("OnNewFile", {
  trigger: { type: "connectorTrigger", name: "payload" },
  handler: async (payload: unknown, context: InvocationContext) => {
    const data = typeof payload === "string" ? JSON.parse(payload) : payload;
    for (const file of data?.body?.value ?? []) {
      context.log(`File: ${file.name}, Path: ${file.path}`);
    }
  },
});
```

### 4. Run locally

Before starting the Function App, ensure **Azurite** (local Azure Storage emulator) is running. The Functions runtime requires `AzureWebJobsStorage` for local development.

#### Start Azurite (required for local development)

Choose one option:

**Option 1: VS Code Extension (simplest)**
1. Install the [Azurite extension](https://marketplace.visualstudio.com/items?itemName=Azurite.azurite) from VS Code Marketplace
2. Open Command Palette (`Ctrl+Shift+P`) and run "Azurite: Start"

**Option 2: npm global install**
```bash
npm install -g azurite
azurite
```

**Option 3: npx (no installation)**
```bash
npx azurite
```

Verify `local.settings.json` includes:
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "dotnet-isolated"
  }
}
```

#### Start the Function App

```shell
func start
```

The extension logs the webhook endpoint at startup:
```
Connector endpoint: http://localhost:7071/runtime/webhooks/connector
```

> **⚠️ Troubleshooting:** If `func start` fails with `AzureWebJobsStorage` or storage connection error:
> - Verify **Azurite is running** in a separate terminal
> - Confirm `local.settings.json` has `"AzureWebJobsStorage": "UseDevelopmentStorage=true"`
> - Check that **no other process is using port 10000** (Azurite's default port)
> - Clear identity cache if switching between cloud/local storage: `%LOCALAPPDATA%\.IdentityService\cache` (Windows) or `~/.IdentityService/cache` (Mac/Linux)

## Local Development with Port Forwarding

To test triggers locally, you need to expose your local Function App so the Connector Namespace can reach it.

Start the Function App with `--enableAuth` to secure the endpoint behind a system key:

```powershell
func start --enableAuth
```

> **⚠️ Important:** Always use `--enableAuth` when exposing your app via a dev tunnel. Without it, your function endpoint is completely unauthenticated on the public internet.

Confirm the app is running on `http://localhost:7071`.

> **🔔 Confirm:** Is the Function App running with `--enableAuth`? (Yes / No)

### Create a dev tunnel

> ⚠️ **Security Warning:** The following steps expose your local Function App to the public internet. Only proceed for local testing and if you understand the implications.

> 💡 Prefer the CLI over VS Code UI? Use the `devtunnel` CLI instead — see [Dev Tunnels CLI quickstart](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started).
> ```bash
> devtunnel user login  # choose the option that matches your org policy
> devtunnel create <your-tunnel-id> -a  # custom tunnel id for a persistent, reusable URL
> devtunnel port create <your-tunnel-id> -p 7071
> devtunnel host <your-tunnel-id> --allow-anonymous
> ```

> **🍎 Mac note:** If `devtunnel host` returns `Tunnel service error: Request not permitted. Unauthorized tunnel creation access: Anonymous does not have 'create' access scope`, your login didn't actually stick. On macOS, `devtunnel user login` without a provider flag silently leaves you as Anonymous. Fix:
> ```bash
> devtunnel user login -g     # GitHub (or -m Microsoft, -e Entra)
> devtunnel user show         # confirm — should NOT print "Anonymous"
> devtunnel host -p 7071 --allow-anonymous
> ```
> If your corp tenant blocks `--allow-anonymous` on the default tunnel domain, drop the flag and grant per-port anon access instead:
> ```bash
> devtunnel host -p 7071
> devtunnel access create -p 7071 --anonymous   # in a separate terminal
> ```

#### VS Code port forwarding

1. Navigate to the **Ports** view in the Panel region (`Ports: Focus on Ports View`) and select **Forward a Port**
2. If you haven't logged in with GitHub before, you'll be prompted to sign in
3. Enter port `7071` — port forwarding starts and the Ports view updates to show the forwarded port and its **Forwarded Address** (e.g., `https://<id>-7071.uks1.devtunnels.ms`)
4. Change the visibility by right-clicking on the port and selecting **Port Visibility** → **Public**. Public ports don't require sign in

> **🔔 Confirm:** Is the port forwarded with Public visibility and do you see the tunnel URL in the Ports panel? (Yes / No)

## Registering a Trigger Config

### Step 1: Get the Callback URL

#### Deployed Function App

```powershell
$resourceGroup = "<resource-group>"
$functionAppName = "<function-app-name>"
$functionName = "<function-name>"  # must match [Function("...")] attribute

$connectorExtensionKey = az functionapp keys list -g $resourceGroup -n $functionAppName --query "systemKeys.connector_extension" -o tsv
$callbackUrl = "https://$functionAppName.azurewebsites.net/runtime/webhooks/connector?functionName=$functionName&code=$connectorExtensionKey"
```

#### Local development (with dev tunnel)

Use the tunnel URL from the **Local Development with Port Forwarding** section above.

> **Important:** Always start your Function App with `--enableAuth` when using a dev tunnel.
> Without it, your function endpoint is completely unauthenticated on the public internet.
> ```powershell
> func start --enableAuth
> ```

Retrieve the `connector_extension` system key from local Azurite storage:

```powershell
# Use the well-known Azurite connection string
# See: https://learn.microsoft.com/azure/storage/common/storage-use-emulator#authorize-with-shared-key-credentials
$connStr = "<azurite-connection-string>"

# Find the most recent host.json blob
$blobs = az storage blob list --container-name azure-webjobs-secrets --connection-string $connStr -o json | ConvertFrom-Json
$blobName = ($blobs | Sort-Object { $_.properties.lastModified } | Select-Object -Last 1).name

# Download and parse
az storage blob download --container-name azure-webjobs-secrets --name $blobName --connection-string $connStr --file host-keys.json --no-progress
$keys = Get-Content host-keys.json | ConvertFrom-Json
$connectorKey = ($keys.systemKeys | Where-Object { $_.name -eq "connector_extension" }).value
```

Build the callback URL:

```powershell
$tunnelUrl = "<your-tunnel-url>"  # from VS Code Ports panel, e.g., https://<id>-7071.uks1.devtunnels.ms
$functionName = "<function-name>"
$callbackUrl = "$tunnelUrl/runtime/webhooks/connector?functionName=$functionName&code=$connectorKey"
```

> **Note:** The tunnel must have **Public** visibility (anonymous access). The Connector Namespace cannot authenticate to private tunnels. We use connector extension keys for auth instead of the tunnel's built-in auth.

### Step 2: Create Trigger Config

```powershell
$subscriptionId = "<subscription-id>"
$resourceGroup = "<resource-group>"
$namespaceName = "<namespace-name>"
$nsId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.Web/connectorGateways/$namespaceName"

$triggerName = "<trigger-config-name>"   # e.g., "onnewemail-trigger"
$connectionName = "<connection-name>"    # e.g., "office365-conn"
$connectorName = "<connector-name>"      # e.g., "office365"
$operationName = "<operation-name>"      # e.g., "OnNewEmail" or "OnNewFile"

$token = az account get-access-token `
    --resource "https://management.core.windows.net/" `
    --query "accessToken" -o tsv

$body = @{
    properties = @{
        operationName = $operationName
        connectionDetails = @{
            connectorName = $connectorName
            connectionName = $connectionName
        }
        notificationDetails = @{
            callbackUrl = $callbackUrl
            httpMethod = "Post"
        }
        parameters = @(
            # Add connector-specific parameters here
            # Office 365 OnNewEmailV3 example:
            # @{ name = "folderPath"; value = "Inbox" }
            
            # OneDrive for Business OnNewFile example:
            # @{ name = "folderId"; value = "root" }
        )
    }
} | ConvertTo-Json -Depth 4

$uri = "https://management.azure.com${nsId}/triggerConfigs/${triggerName}?api-version=2026-05-01-preview"
try {
    $response = Invoke-WebRequest -Uri $uri -Method PUT -Body $body `
        -ContentType "application/json" `
        -Headers @{ Authorization = "Bearer $token" }
    Write-Output "Status: $($response.StatusCode)"
} catch {
    Write-Output "Error: $($_.Exception.Response.StatusCode)"
    $_.ErrorDetails.Message
}
```

**Common trigger parameters:**
- **Office 365 `OnNewEmailV3`**: Requires `folderPath` (e.g., `"Inbox"`)
- **OneDrive for Business `OnNewFile`**: Requires `folderId` (e.g., `"root"` for the root folder)
- **SharePoint `OnNewFile`**: Requires `dataset` (site URL) and `table` (library or list ID)

> **Note:** Trigger parameters are connector-specific. Use `az connector-namespace connection operation list --operation-type trigger` to discover available triggers and their required parameters.

### Step 3: Verify Trigger Config

```powershell
az rest --method GET `
    --uri "https://management.azure.com${nsId}/triggerConfigs/${triggerName}?api-version=2026-05-01-preview" `
    --query "properties.{operation:operationName, state:state, callback:notificationDetails.callbackUrl}" `
    -o table
```

Expected: `state = Enabled`.

### Step 4: Test the Trigger

Trigger the connector event (e.g., send an email to the Office 365 inbox, upload a file to OneDrive root folder, etc.). Watch the Function App logs for execution:

**Expected success output:**

```
Executing 'Functions.OnNewEmail' (Reason='', Id=9c4e2415-bc91-430c-bda4-d8953725a432)
Received Microsoft 365 OnNewEmail trigger
Email received from: user@contoso.com
Email subject: Test Email
Executed 'Functions.OnNewEmail' (Succeeded, Id=9c4e2415-bc91-430c-bda4-d8953725a432, Duration=123ms)
```

If no logs appear:
1. Verify the trigger config `state = Enabled` (Step 3)
2. Check that the callback URL is correct and publicly accessible (for local dev tunnels, verify `--allow-anonymous` or per-port anonymous access)
3. Review [Troubleshooting](#troubleshooting) section below
4. Query trigger run history:
   ```powershell
   az connector-namespace trigger-config run list \
       --namespace-name $namespaceName \
       --resource-group $resourceGroup \
       --name $triggerName \
       -o table
   ```

### Step 5: Update Callback URL

To point an existing trigger config to a different callback (e.g., after redeploying or switching tunnels):

```powershell
# Re-run the PUT from Step 2 with the updated callbackUrl
```

### Step 6: List All Trigger Configs

```powershell
   az connector-namespace trigger-config list \
       --namespace-name $namespaceName \
       --resource-group $resourceGroup \
       --name $triggerName \
       -o table
```

### Step 7: Clean up after testing

When done testing, **always** revoke public access:

1. In the **Ports** panel, right-click the forwarded port
2. Select **Stop Forwarding Port** (or set visibility back to **Private**)

> ⚠️ Do not leave your local Function App publicly exposed longer than necessary.


## Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Could not find member 'connectionName'` | Used `connectionName` at top level | Wrap in `connectionDetails` object |
| `Could not find member 'callbackUrl'` | Put `callbackUrl` at properties level | Wrap in `notificationDetails` object |
| `Could not find member 'parameterName'` | Used `parameterName` in params array | Use `name` field instead |
| Trigger provisions but never fires | Missing `notificationDetails` or empty `callbackUrl` | Ensure `notificationDetails.callbackUrl` is set |
| `az rest` PUT returns no output | `az rest` swallows non-2xx responses | Use `Invoke-WebRequest` for PUT operations |

### Polling Interval

The Connector Namespace polls the connector every 1-5 minutes. After polling detects new content, it POSTs the payload to your callback URL.

## Reference

For a complete mapping of trigger operations to function signatures across .NET, Python, and TypeScript (including which typed payload to use and how to specify the function), see [Operations to Functions Signature Match](https://github.com/Azure/azure-functions-connector-extension/blob/main/docs/operations-functions-match.md).

