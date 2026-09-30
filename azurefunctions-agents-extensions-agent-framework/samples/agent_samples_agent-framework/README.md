---
page_type: sample
languages:
  - python
products:
  - azure
  - azure-functions
  - microsoft-foundry
urlFragment: agent-framework-sample
---

# Azure Function Agent sample

This sample shows how an existing Azure Function App can add agentic reasoning
without replacing its triggers or deterministic application code. An HTTP
trigger and a queue trigger validate and normalize an order before receiving a
fresh Microsoft Agent Framework `Agent` through `@app.markdown_agent`.

The sample demonstrates:

- using `AgentFunctionApp` with standard Azure Functions decorators;
- resolving `order-fulfillment.agent.md` by logical Agent name;
- injecting a fresh Agent into HTTP and queue Function handlers;
- keeping validation, calculations, and data minimization in application code;
- discovering the `order-policy` Skill and `inventory` MCP server from the app
  root; and
- closing invocation-owned clients, Agents, credentials, and MCP resources.

## How the sample works

Both Functions use the same `order-fulfillment` Agent definition:

```python
@app.markdown_agent(
    arg_name="order_agent",
    agent_name="order-fulfillment",
)
```

The decorator resolves `order-fulfillment.agent.md` and supplies the
constructed Agent as the `order_agent` handler argument. The file contains raw
instructions; client and model configuration remain explicit in
`create_chat_client()`.

Before invoking the Agent, `order_processing.py` uses Pydantic to validate the
order and application code to calculate totals and review signals. Unknown
input fields are discarded. The Agent receives only this normalized projection,
not the original request or queue message.

At app startup, the extension also discovers:

- `skills/order-policy/SKILL.md`, which supplies fulfillment policy; and
- `mcp.json`, which exposes only the `lookup_stock` and `reserve_stock` tools
  from the configured `inventory` streamable-HTTP MCP server.

Discovered Skills and MCP servers are app-wide in V1, so both Agent bindings
receive them.

## Project structure

| Path | Purpose |
| --- | --- |
| `function_app.py` | Defines the HTTP and queue Functions and the Foundry client factory. |
| `order_processing.py` | Validates input and calculates the trusted order projection. |
| `order-fulfillment.agent.md` | Contains the raw Agent instructions. |
| `skills/order-policy/SKILL.md` | Defines the automatically discovered order-policy Skill. |
| `mcp.json` | Configures the inventory MCP server and tool allowlist. |
| `local.settings.template.json` | Lists required local application settings. |
| `requirements.txt` | Installs the extension with MCP support and sample dependencies. |

## Prerequisites

- Python 3.13 or later.
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local).
- [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite)
  or an Azure Storage account for `AzureWebJobsStorage` and the queue trigger.
- An Azure subscription and a Microsoft Foundry project with a deployed model.
- A local identity authorized to use the Foundry project. For example, sign in
  with `az login` before running the sample.
- A trusted streamable-HTTP MCP endpoint that exposes the inventory tools.

## Setup

1. Change to the Function project directory:

   ```bash
  cd azurefunctions-agents-extensions-agent-framework/samples/agent_samples_agent-framework
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # macOS or Linux
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

   The editable dependency in `requirements.txt` installs the Agent Framework
   extension from this repository with its `[mcp]` extra. When using the
   published package instead, install
   `azurefunctions-agents-extensions-agent-framework[mcp]`.

4. Create local settings from the template:

   ```powershell
   Copy-Item local.settings.template.json local.settings.json
   ```

   On macOS or Linux, use `cp local.settings.template.json local.settings.json`.

5. Replace the placeholders in `local.settings.json`:

   | Setting | Description |
   | --- | --- |
   | `AzureWebJobsStorage` | Keep `UseDevelopmentStorage=true` for Azurite, or use an Azure Storage connection string. |
   | `FOUNDRY_PROJECT_ENDPOINT` | Microsoft Foundry project endpoint. |
   | `FOUNDRY_MODEL` | Name of the deployed model used by `FoundryChatClient`. |
   | `INVENTORY_MCP_URL` | HTTPS URL of a trusted streamable-HTTP MCP server. |

   Do not commit `local.settings.json`. Use environment references rather than
   placing credentials or tokens in `mcp.json`.

## Run the sample

1. Start Azurite. With the Azurite CLI installed, run:

   ```bash
   azurite --silent --location .azurite
   ```

   You can instead start Azurite from its Visual Studio Code extension.

2. In another terminal, activate the virtual environment from the sample
  directory and start the Functions host:

   ```bash
   func start
   ```

### Invoke the HTTP Function

Send a valid order. The route supplies the order ID:

```bash
curl -X POST http://localhost:7071/orders/42 \
  -H "Content-Type: application/json" \
  -d '{"customer":{"id":"C-1007","loyalty_tier":"gold"},"currency":"usd","shipping":{"country":"ca","method":"overnight"},"items":[{"sku":"A-100","quantity":2,"unit_price":"24.95"}]}'
```

The response contains the route order ID and the Agent's assessment:

```json
{
  "order_id": "42",
  "assessment": "<model-generated fulfillment assessment>"
}
```

Malformed JSON or an invalid order returns HTTP `400`:

```json
{"error":"Order failed validation."}
```

### Invoke the queue Function

Create or open the `orders` queue in Azurite with Azure Storage Explorer, then
add a message containing an order. Unlike the HTTP route, a queue message must
include `order_id`:

```json
{
  "order_id": "Q-1001",
  "customer": {"id": "C-1007", "loyalty_tier": "gold"},
  "currency": "USD",
  "shipping": {"country": "CA", "method": "overnight"},
  "items": [{"sku": "A-100", "quantity": 2, "unit_price": "24.95"}]
}
```

The `process_order_event` Function validates the message and asks the Agent to
triage fulfillment exceptions. It intentionally returns no queue output; inspect
the Functions host and connected model/MCP telemetry to observe the invocation.

## Expected lifecycle and security behavior

- A new Foundry client, Agent, MCP tool, HTTP client, and credential are created
  for each invocation and closed afterward.
- The MCP URL is resolved from `INVENTORY_MCP_URL` for each invocation.
- MCP configurations with headers or Entra authentication require HTTPS, except
  for explicit loopback development endpoints.
- Agent instructions and discovered capability definitions may be cached, but
  live clients and Agents are never shared across invocations.
- The Agent must not claim that an external action succeeded unless an MCP tool
  result confirms it.

## Troubleshooting

- **Agent definition not found:** run `func start` from the sample directory and keep
  `order-fulfillment.agent.md` at the app root.
- **Foundry authentication fails:** run `az login`, verify the active tenant and
  subscription, and confirm the identity can access the Foundry project.
- **MCP connection fails:** verify `INVENTORY_MCP_URL` uses a supported
  streamable-HTTP endpoint and exposes the allowlisted tool names.
- **Queue Function does not run:** confirm Azurite is running and that the
  `orders` queue belongs to the account configured by `AzureWebJobsStorage`.
- **HTTP request returns 400:** confirm the request includes a customer,
  two-letter shipping country, supported shipping method, and at least one item
  with a positive integer quantity.

## Next steps

- Review the extension's [package documentation](../../README.md).
- Compare this sample with the [Durable Agent Framework sample](../agent_samples_agent-framework_durable/README.md)
  when Agent calls must participate in a replay-safe orchestration.
- Learn more about [Python decorators and bindings](https://learn.microsoft.com/azure/azure-functions/functions-reference-python#programming-model).