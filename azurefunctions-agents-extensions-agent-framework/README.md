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

YAML hosting is a separate opt-in. Install both optional extras. The workflows
extra uses `agent-framework-declarative>=1.0.3,<2`.

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

`workflows=True` requires `durable=True`. Only `*.workflow.yaml` and
`*.workflow.yml` directly in the app root or its `workflows/` directory are
discovered, not arbitrary YAML or nested files. Discovered entry files must stay
within the app root. Each loaded result must be a MAF `Workflow` with a stable
name of 1–63 ASCII letters, digits, hyphens, or underscores, starting with a
letter. Names must be unique ignoring case. An explicit YAML `name` keeps routes
predictable, but naming and YAML parsing otherwise follow MAF.

The extension calls the public `create_workflow_from_yaml_path(path)` method and
supplies the graphs to DAFX's `workflows=` constructor. With the default route
prefix, each graph gets
`POST /api/workflow/NAME/run`, `GET /api/workflow/NAME/status/{instanceId}`, and
`POST /api/workflow/NAME/respond/{instanceId}/{requestId}`. No custom
orchestration or handwritten HTTP handlers are needed.

By default, `WorkflowFactory(agents=...)` receives `MarkdownDurableAgent`
adapters for **all** discovered Markdown agents, including agents selected by
dynamic names. To configure MAF directly, pass a configured `WorkflowFactory`
object as `workflow_factory=` alongside `workflows=True`. That object is used
unchanged. Its agent registry is not automatically merged with discovered
Markdown agents. Configure its `agent_factory`, agents, registered tools, HTTP
or MCP handlers, and configuration through MAF's public APIs.

The extension does not impose a separate YAML parser, action allowlist, or
restrictions on inline agents, file-based agents, dynamic agent references, or
workflow tool actions. These follow the installed MAF parser and builder,
including their warnings, errors, and required configuration. For example,
`InvokeFunctionTool` can use `WorkflowFactory.register_tool()`, while HTTP and
MCP actions need their MAF handlers. DAFX's hosting validations still apply.
This delegation is not a claim that every MAF feature has been execution-tested.

Relative file references inside YAML use native MAF resolution from the workflow
file's directory. They are not sandboxed by the entry-file containment check.
Treat workflow files and their references as trusted deployment content.

Agent actions execute as durable activities, not through the agent entity in the
same graph. Markdown adapters open and close fresh Agents, clients, and tools
per execution. Inline agents and agents supplied by a custom factory follow
MAF's or that factory's construction and resource lifecycle, which may construct
agents and clients during app initialization/indexing. The extension does not
wrap them in the Markdown lifecycle. `durable=True` still publishes all
discovered Markdown agents and their standalone HTTP endpoints, even with a
custom workflow factory.

Python support follows the installed MAF dependencies, not an extension-level
Python 3.14 rejection. Expression execution has been verified on Python 3.13.
MAF declarative 1.0.3 excludes its PowerFx dependency on Python 3.14, so those
expression checks remain on 3.13. Python 3.14 execution is not claimed as verified.

See the [local YAML sample](samples/durable-yaml-workflow/README.md) for shared
state, a Markdown agent call, and a separate question/response workflow. The
[configured factory sample](samples/configured-workflow-factory/README.md) uses
a registered function tool and configuration without an agent client. Neither
sample provisions a host or backend.
