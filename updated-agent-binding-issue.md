# Enable hybrid Azure Functions with in-process Agent bindings

Enable Azure Function Apps to invoke Microsoft Agent Framework Agents in-process through an extension-owned smart binding, supporting hybrid deterministic and agentic workflows.

## Goal

A Python Function can declare a Markdown Agent binding and receive a fully constructed Microsoft Agent Framework `Agent` in its handler. Customers retain normal Azure Functions triggers and orchestration logic while adding agentic work where needed.

## Scope

- Provide two extension packages:
  - `azurefunctions-agents-extensions-base` for provider-neutral binding, discovery, lifecycle, and Durable contracts.
  - `azurefunctions-agents-extensions-agent-framework` for Microsoft Agent Framework integration.
- Provide `AgentFunctionApp`, a subclass of `azure.functions.FunctionApp`, with a typed `markdown_agent` decorator.
- Resolve raw `<agent_name>.agent.md` instructions from either the Function App root or its `agents/` directory.
- Configure the MAF client through an app-level `client_factory`.
- Support app-level Python tools, with optional per-binding `client_factory` and `tools` overrides.
- Automatically discover Skills and HTTP-based MCP servers from the app root.
- Apply discovered Skills and MCP servers to every Agent binding in the app.
- Create fresh clients, Agents, credentials, HTTP clients, and MCP tools for each invocation and close them on success, failure, or cancellation.
- Cache provider discovery, compiled bindings, and Durable recipes without caching live invocation resources.
- Support optional Durable orchestration through `AgentFunctionApp.orchestration_trigger` and `context.call_agent(...)`.
- Execute Durable Agent calls through a hidden activity using a deterministic, JSON-only schema-v1 payload.
- Preserve function name, invocation ID, and Durable instance ID at the provider boundary where available.
- Validate missing or ambiguous Agent files, unsupported provider options, invalid handler signatures, unsupported capabilities, and malformed MCP configuration.
- Keep Durable Functions and MCP dependencies optional and import-safe.
- Include representative HTTP and Durable hybrid samples and automated lifecycle, validation, discovery, and import-safety tests.
- Document installation, configuration, discovery conventions, lifecycle, and V1 limitations.

## Implemented authoring model

Agent files contain raw UTF-8 instructions only. Front matter, model configuration, tools, and runtime configuration are not parsed from `.agent.md`.

Configuration is divided as follows:

- `client_factory`: configured on `AgentFunctionApp`, optionally overridden per binding.
- Python `tools`: configured explicitly on the app or binding.
- Skills: discovered from `skills/` or `Skills/`.
- MCP servers: discovered from `mcp.json`.
- MCP tool allowlists: configured per server in `mcp.json`.
- Agent instructions: loaded from `<agent_name>.agent.md` or `agents/<agent_name>.agent.md`.

## Out of scope

- Adding Agent decorators directly to `azure.functions.FunctionApp`.
- Modifying the Azure Functions Python SDK or MAF public API.
- Parsing model configuration, tools, or front matter from `.agent.md`.
- App-level or per-binding selection of discovered Skills or MCP servers.
- Per-call provider, client, tool, Skill, or MCP overrides from Durable orchestrators.
- Local-process or stdio MCP servers.
- Standalone declarative Serverless Agent endpoints.
- Multi-agent orchestration, A2A protocol support, or new model-provider policy.
- Caching live clients or Agents across invocations.

## Success criteria

- An existing Python Function App can migrate from `func.FunctionApp` to `AgentFunctionApp` without replacing its existing trigger model.
- A normal Function handler can receive a MAF `Agent` through `@app.markdown_agent(...)` and invoke it directly.
- The Agent receives the selected raw instructions, configured client, explicit Python tools, and automatically discovered Skills and MCP servers.
- Every invocation receives fresh, safely managed runtime resources.
- A Durable orchestrator can invoke an Agent through replay-safe `context.call_agent(...)`.
- Invalid definitions, configuration, signatures, or assets fail with actionable diagnostics.
- Importing either extension does not require or import Durable Functions.
- HTTP and Durable samples and automated tests cover invocation, lifecycle, discovery, validation, and compatibility with standard Azure Functions decorators.

## Python binding API

```python
import azure.functions as func
from agent_framework import Agent
from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp


app = AgentFunctionApp(client_factory=create_chat_client)


@app.function_name(name="ProcessOrder")
@app.route(route="orders/{orderId}", methods=["POST"])
@app.markdown_agent(
    arg_name="order_agent",
    agent_name="order-fulfillment",
)
async def process_order(
    req: func.HttpRequest,
    order_agent: Agent,
) -> func.HttpResponse:
    task = (
        "Validate the order and return fulfillment guidance for "
        f"{req.route_params['orderId']}."
    )
    response = await order_agent.run(task)
    return func.HttpResponse(response.text)
```

`order_agent` is the runtime-managed handler parameter. `order-fulfillment` resolves to exactly one of:

```text
<app_root>/order-fulfillment.agent.md
<app_root>/agents/order-fulfillment.agent.md
```

The extension loads the file as raw instructions and constructs a fresh MAF `Agent` for each invocation.

## Durable API

```python
from typing import Any

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp


app = AgentFunctionApp(client_factory=create_chat_client)


@app.orchestration_trigger(context_name="context")
def order_orchestrator(context: Any):
    assessment = yield context.call_agent(
        "order-fulfillment",
        {"order": context.get_input()},
    )
    return assessment
```

`call_agent()` schedules the extension's hidden activity. It does not execute model, filesystem, credential, or network operations during orchestration replay.
