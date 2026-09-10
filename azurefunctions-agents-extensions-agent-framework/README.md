# Azure Functions Microsoft Agent Framework Extension

Inject Microsoft Agent Framework Agents built from raw `.agent.md` instructions
into Python Azure Functions.

## Install

```text
pip install azurefunctions-agents-extensions-agent-framework
```

Install Durable Functions support with the durable extra:

```text
pip install "azurefunctions-agents-extensions-agent-framework[durable]"
```


Install remote MCP transport and Entra support with the MCP extra:

```text
pip install "azurefunctions-agents-extensions-agent-framework[mcp]"
```

## Use an Agent app

Create a zero-argument factory that returns a fresh MAF chat client. A new
client and Agent context are created and closed for every Function invocation.

```python
import azure.functions as func
from agent_framework import Agent
from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp


def create_chat_client():
    from agent_framework.openai import OpenAIChatClient

    return OpenAIChatClient()


app = AgentFunctionApp(client_factory=create_chat_client)


@app.route(route="orders", methods=["POST"])
@app.markdown_agent(arg_name="agent", agent_name="orders")
async def process_order(req: func.HttpRequest, agent: Agent):
    response = await agent.run(req.get_body().decode())
    return response.text
```

`AgentFunctionApp` is owned by this extension and subclasses
`azure.functions.FunctionApp`. The Azure Functions SDK does not need Agent APIs
or modifications. One app uses the Microsoft Agent Framework provider selected
by this package.

Place the complete instructions at `orders.agent.md` or
`agents/orders.agent.md`. The file is raw UTF-8 text; no front matter or runtime
configuration is interpreted.

## Skills and MCP servers

Skills and MCP servers are discovered automatically from the app root and are
available to each Agent binding by default:

```text
skills/inventory/SKILL.md
mcp.json
```

`SKILL.md` uses Agent Skills frontmatter:

```markdown
---
name: inventory
description: Look up inventory policy and warehouse constraints.
---

Use the references in this skill when assessing stock.
```

The base extension discovers Skill directory paths without reading their
contents. Microsoft Agent Framework parses and validates each `SKILL.md` when
it loads the file-based Skills provider.

V1 MCP discovery supports remote HTTP transports only:

```json
{
    "servers": {
        "inventory": {
            "type": "streamable-http",
            "url": "$INVENTORY_MCP_URL",
            "tools": ["lookup_stock", "reserve_stock"],
            "headers": {"X-Tenant": "%TENANT_ID%"},
            "auth": {
                "scope": "$INVENTORY_MCP_SCOPE",
                "client_id": "%AZURE_CLIENT_ID%"
            }
        }
    }
}
```

`$VAR` and `%VAR%` references are resolved for each invocation, not during
discovery. Missing values fail before connecting. Servers configured with
headers or Entra authentication must use HTTPS; HTTP is accepted only for
loopback development. Exposed MCP tool names are prefixed with the server name
to prevent collisions between servers. Credentials, tokens, HTTP clients, MCP
tools, and Agents are fresh invocation-owned resources and are closed on
success, error, or cancellation. Do not place secrets directly in
source-controlled `mcp.json`; use environment references.

Every Agent in the Function App receives all valid Skills and MCP servers
discovered from the app root:

```python
from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp

app = AgentFunctionApp(client_factory=create_chat_client)


@app.markdown_agent(arg_name="agent", agent_name="orders")
async def process_order(agent: Agent):
        ...
```

V1 has no app-level or per-binding capability selectors. Skill scripts and MCP
tools can perform privileged operations, so placing a definition under the app
root grants every Agent in that app access to it. Use separate Function Apps
when capabilities require isolation. Python `tools=` remain explicit because
they are supplied directly to the Microsoft Agent Framework Agent.

The normal markdown binding accepts `client_factory` and explicit Python
`tools` overrides. The extension owns the Agent client, name, instructions, and
discovered Skills/MCP integration. Configure `app_root` only when constructing
`AgentFunctionApp`; decorators do not override it.

## Durable Agents

Durable support is optional. This prototype pins both DAFX packages to
[DAFX PR #72](https://github.com/microsoft/agent-framework-durable-extension/pull/72)
at `aa9529ec489e16ac64b73bd68d5adbb8e4945258` for SDK 2 compatibility.
These Git dependencies are for local prototyping, not a PyPI release.

```text
pip install "azurefunctions-agents-extensions-agent-framework[durable]"
```

Set `durable=True` to discover every `.agent.md` file directly in the app root
or its `agents/` directory. Each discovered agent gets a DAFX entity and an
automatic `POST /api/agents/{name}/run` endpoint with the default HTTP route
prefix. No handwritten HTTP function or orchestrator is required.

This explicitly publishes every discovered definition. Durable names must start
with an ASCII letter or digit and contain only ASCII letters, digits, hyphens, and
underscores. Ambiguous definitions and generated function-name collisions fail
rather than silently selecting an agent.

```python
app = AgentFunctionApp(client_factory=create_chat_client, durable=True)
```

For orchestration, place `durable_markdown_agent` below `orchestration_trigger`
on a synchronous generator. The binding registers the selected markdown agent
and its HTTP endpoint even without `durable=True`. The injected object is a
DAFX proxy, not a live Agent. Yield its tasks and share a session across turns.

```python
app = AgentFunctionApp(client_factory=create_chat_client)


@app.orchestration_trigger(context_name="context")
@app.durable_markdown_agent(
    arg_name="agent", agent_name="orders", context_name="context"
)
def orders(context, agent):
    session = agent.create_session()
    assessment = yield agent.run("Assess the order.", session=session)
    plan = yield agent.run("Make a fulfillment plan.", session=session)
    return {"assessment": assessment.text, "plan": plan.text}
```

Registration compiles recipes without constructing clients. At entity execution,
the lifecycle adapter enters the compiled binding's `open_agent()` context and
closes it after the run. Each execution creates fresh clients and tools; DAFX
restores conversation history from durable session state. Orchestrators keep the
native SDK context. The old `context.call_agent()` activity path is replaced by
the injected proxy.

Normal `markdown_agent()` remains invocation-scoped and unchanged. Without a
durable opt-in, it does not create an inner DAFX app. With durable agents, the
outer app indexes both registries, including the SDK's `BuiltIn__HttpActivity`
and `BuiltIn__HttpPollOrchestrator`. Agent HTTP endpoints are enabled; health
and MCP endpoints are disabled.

See the [endpoint-only local sample](samples/lazy-owned-dafx/README.md) and the
[durable binding sample](samples/durable-markdown-binding/README.md) for setup
and deterministic examples that do not need a model service.

## YAML workflows

YAML hosting is a separate opt-in and currently requires **Python 3.13**. Install
both optional extras. Python 3.14 is rejected for this feature because the
declarative runtime needs PowerFx.

```text
pip install "azurefunctions-agents-extensions-agent-framework[durable,workflows]"
```

```python
app = AgentFunctionApp(
    client_factory=create_chat_client,
    durable=True,
    workflows=True,
)
```

Only `*.workflow.yaml` and `*.workflow.yml` directly in the app root or its
`workflows/` directory are discovered, not arbitrary YAML or nested files. Each
definition needs `kind: Workflow` and an explicit `name` of 1–63 ASCII letters,
digits, hyphens, or underscores, starting with a letter. Names must be unique
ignoring case.

The extension builds graphs with `WorkflowFactory` and supplies them to DAFX's
`workflows=` constructor. With the default route prefix, each graph gets
`POST /api/workflow/NAME/run`, `GET /api/workflow/NAME/status/{instanceId}`, and
`POST /api/workflow/NAME/respond/{instanceId}/{requestId}`. No custom
orchestration or handwritten HTTP handlers are needed.

`InvokeAzureAgent` accepts static Markdown references, either `agent: writer` or
`agent: {name: writer}`. Inline top-level `agents` definitions, file-based YAML
agents, and dynamic agent names are rejected. Agent actions run as durable
activities using the existing `MarkdownDurableAgent` open/close lifecycle, not
through the agent entity in the same graph. `durable=True` still publishes all
discovered Markdown agents and their standalone HTTP endpoints.

See the [local YAML sample](samples/durable-yaml-workflow/README.md) for shared
state, a Markdown agent call, and a separate question/response workflow. The
sample uses a deterministic client and does not provision a host or backend.
