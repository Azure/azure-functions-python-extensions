---
page_type: sample
languages:
  - python
products:
  - azure
  - azure-functions
  - durable-functions
  - microsoft-foundry
urlFragment: agent-framework-durable-sample
---

# Hybrid Durable Agent sample

This sample combines deterministic Durable Functions orchestration with
Microsoft Agent Framework reasoning. The orchestrator coordinates ordinary
application activities and Agent calls while all filesystem, client, model, and
network work runs outside replay. An ordinary activity prepares the order, and
DAFX entities execute the Agent calls.

The sample demonstrates

- starting an orchestration from an HTTP-triggered Function
- validating and minimizing an order in an ordinary Durable activity
- injecting a DAFX proxy with `durable_markdown_agent` below
  `orchestration_trigger`
- yielding `agent.run()` tasks from a synchronous generator orchestrator
- sharing one durable session between assessment and planning
- passing the prepared order as JSON and returning the responses' text
- polling the standard Durable management endpoint for status and output.

## How the sample works

The request follows this sequence:

1. `start_order_orchestration` receives the HTTP request and starts an
   `order_orchestrator` instance.
2. The orchestrator calls `prepare_order_activity`, which validates the order,
   calculates totals, and produces a minimized projection.
3. The injected Agent proxy creates a session. The first `agent.run()` schedules
    an assessment of the prepared order through the DAFX entity.
4. A second `agent.run()` requests a fulfillment plan using the same session and
    the assessment's text.
5. The orchestration output combines the deterministic order ID with the two
   model-generated results.

The orchestrator never opens files, creates credentials or clients, connects to
a model, or performs network I/O. During replay it recreates the activity and
Agent task schedule from recorded inputs and results.

The logical Agent name `order-fulfillment` resolves
`order-fulfillment.agent.md`. The file contains raw Agent instructions;
Foundry client and model configuration remain explicit in
`create_chat_client()`.

The binding registers only the selected markdown definition, without bulk
discovery or an automatic Agent HTTP endpoint. Clients are created and closed per entity
execution through the compiled markdown binding, not during indexing or replay.
No custom orchestration context wrapper or hidden Agent activity is used.
The inner DAFX host is created when the outer app indexes its functions.

## Project structure

| Path | Purpose |
| --- | --- |
| `function_app.py` | Defines the HTTP starter, preparation activity, orchestrator, and Foundry client factory. |
| `order_processing.py` | Validates input and calculates the trusted order projection. |
| `order-fulfillment.agent.md` | Contains raw instructions used by both Agent turns. |
| `local.settings.template.json` | Lists required local application settings. |
| `requirements.txt` | Installs the extension with Durable support and sample dependencies. |

## Prerequisites

- Python 3.13 or later.
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local).
- [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite)
  or an Azure Storage account. Durable Functions requires storage for history,
  control queues, activity work items, and entity state.
- The prototype's SDK 2-compatible DAFX packages and a compatible Functions
  host/extension and Durable backend. These are not provisioned by this sample.
- An Azure subscription and a Microsoft Foundry project with a deployed model.
- A local identity authorized to use the Foundry project. For example, sign in
  with `az login` before running the sample.

## Setup

1. Change to the Function project directory:

   ```bash
  cd azurefunctions-agents-extensions-agent-framework/samples/agent_samples_agent-framework_durable
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

    First follow the [prototype setup steps](../lazy-owned-dafx/README.md#install-and-verify)
    to install both local extension packages and the pinned SDK 2-compatible DAFX
    dependencies in the same virtual environment. Then, from this sample directory,
    install the Foundry and order-validation dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

   The editable dependency in `requirements.txt` installs the Agent Framework
    extension from this repository with its `[durable]` extra. Use the prototype
    dependencies rather than substituting the published SDK 1.x DAFX packages.

4. Create local settings from the template:

   ```powershell
   Copy-Item local.settings.template.json local.settings.json
   ```

   On macOS or Linux, use `cp local.settings.template.json local.settings.json`.

5. Replace the Foundry placeholders in `local.settings.json`:

   | Setting | Description |
   | --- | --- |
   | `AzureWebJobsStorage` | Keep `UseDevelopmentStorage=true` for Azurite, or use an Azure Storage connection string. |
   | `FOUNDRY_PROJECT_ENDPOINT` | Microsoft Foundry project endpoint. |
   | `FOUNDRY_MODEL` | Name of the deployed model used by `FoundryChatClient`. |

   Do not commit `local.settings.json` or place credentials in source-controlled
   files.

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

3. Start an orchestration with a valid order:

   ```bash
   curl -X POST http://localhost:7071/orders/orchestrations \
     -H "Content-Type: application/json" \
     -d '{"order_id":"D-2048","customer":{"id":"C-1007","loyalty_tier":"gold"},"currency":"usd","shipping":{"country":"ca","method":"overnight"},"items":[{"sku":"A-100","quantity":2,"unit_price":"24.95"}]}'
   ```

The starter returns HTTP `202` with the standard Durable management payload:

```json
{
  "id": "<instance-id>",
  "statusQueryGetUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/<instance-id>?...",
  "sendEventPostUri": "...",
  "terminatePostUri": "...",
  "purgeHistoryDeleteUri": "..."
}
```

Copy `statusQueryGetUri` from the response and poll it until `runtimeStatus` is
`Completed`:

```bash
curl "<statusQueryGetUri>"
```

The completed instance has an output shaped like:

```json
{
  "order_id": "D-2048",
  "risk_assessment": "<model-generated assessment>",
  "fulfillment_plan": "<model-generated plan>"
}
```

Malformed JSON returns HTTP `400` and does not start an orchestration:

```json
{"error":"Order failed validation."}
```

Order schema validation occurs in `prepare_order_activity`. A structurally
invalid order therefore starts successfully but later causes the orchestration
to fail. Inspect the status endpoint and Functions host logs for the activity
failure.

## Durable Agent behavior

- `@app.durable_markdown_agent` sits below `@app.orchestration_trigger` and
  injects a `DurableAIAgent[DurableAgentTask]` proxy into the generator.
- `agent.create_session()` creates one session that both `agent.run()` calls
  reuse. DAFX stores conversation history in durable session state.
- Each Agent call receives a JSON string containing the trusted prepared order.
  The planning request also includes `assessment.text`.
- Agent execution and all related I/O occur in the DAFX entity, never in the
  orchestrator.
- The extension compiles the Agent recipe during registration, then creates and
  closes a fresh Foundry client and Agent for each entity execution.
- The output contains only the order ID, `assessment.text`, and `plan.text`.

### Private Agent registration

This sample's `host.json` removes the default `api` prefix. The handwritten
`POST /orders/orchestrations` starter is the only application HTTP route.
The binding's `expose_http_endpoint=False` default keeps the agent private, so
there is no `POST /agents/order-fulfillment/run` route.

An explicit `expose_http_endpoint=True` on the binding would publish that direct
agent route. It would bypass `prepare_order_activity` and its order validation.
Do not enable it merely to access the agent from the orchestrator. HTTP exposure
and business policy are separate decisions.

## Troubleshooting

- **Agent definition not found:** run `func start` from the sample directory and keep
  `order-fulfillment.agent.md` at the app root.
- **Foundry authentication fails:** run `az login`, verify the active tenant and
  subscription, and confirm the identity can access the Foundry project.
- **Durable extension fails to load:** confirm the `[durable]` extra was
  installed, the SDK 2-compatible host/extension is available, and the extension
  bundle in `host.json` can be downloaded.
- **Orchestration remains Pending:** verify Azurite is running and
  `AzureWebJobsStorage` points to the same storage service used by the host.
- **Orchestration fails in `prepare_order_activity`:** confirm the request has an
  `order_id`, customer, two-letter shipping country, supported shipping method,
  and at least one item with a positive integer quantity.
- **Agent execution fails:** inspect the Functions host logs and the
  instance status response for Foundry authentication, quota, or model errors.

## Next steps

- Review the extension's [package documentation](../../README.md).
- Compare this sample with the [Agent Framework sample](../agent_samples_agent-framework/README.md)
  for direct Agent injection into HTTP and queue handlers.
- Try the [durable markdown binding sample](../durable-markdown-binding/README.md)
  for the same shared-session pattern with a deterministic local client.
- Learn more about [Durable Functions for Python](https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-overview?tabs=python).