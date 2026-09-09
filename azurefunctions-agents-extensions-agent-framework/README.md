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
discovery. Missing values fail before connecting. Credentials, tokens, HTTP
clients, MCP tools, and Agents are fresh invocation-owned resources and are
closed on success, error, or cancellation. Do not place secrets directly in
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

The constructor and decorator expose only `client_factory` and explicit Python
`tools` in V1. The extension owns the Agent client, name, instructions, and
discovered Skills/MCP integration. Configure `app_root` only when constructing
`AgentFunctionApp`; decorators do not override it.

## Durable Agents

Durable orchestration support is optional:

```text
pip install "azurefunctions-agents-extensions-agent-framework[durable]"
```

Use `AgentFunctionApp` and call `context.call_agent(agent_name, input_)` inside a
synchronous generator orchestrator. Agent execution is isolated in an activity
so replay performs no nondeterministic work. Importing the package remains safe
without Durable installed; using a Durable decorator requires the `[durable]`
extra.

All `call_agent()` invocations use the provider configured by `AgentFunctionApp`.
They also use the app-level `skills` and `mcp_servers` defaults. V1 does not
support selecting another provider or capability set from an orchestrator, and
the schema-v1 orchestration payload contains no capability paths, settings, or
secrets.
