# Azure Functions Microsoft Agent Framework Extension

Inject Microsoft Agent Framework Agents built from raw `.agent.md` instructions
into Python Azure Functions.

## Install

```text
pip install azurefunctions-extensions-agents-framework
```

The default package installs `agent-framework-core==1.13.0`. Install the MAF
client package required by your application separately. OpenAI, Foundry, Azure
Identity, storage, YAML, MCP, and the Azure Functions Agents runtime are not
dependencies of this extension.

## Use a typed Agent app

Create a zero-argument factory that returns a fresh MAF chat client. A new
client and Agent context are created and closed for every Function invocation.

```python
import azure.functions as func
from agent_framework import Agent
from azurefunctions.extensions.agents.framework import AiApp


def create_chat_client():
    from agent_framework.openai import OpenAIChatClient

    return OpenAIChatClient()


app = AiApp(client_factory=create_chat_client)


@app.route(route="orders", methods=["POST"])
@app.markdown_agent(arg_name="agent", agent_name="orders")
async def process_order(req: func.HttpRequest, agent: Agent):
    response = await agent.run(req.get_body().decode())
    return response.text
```

Provider IDs are the entry-point names published by provider packages. Each
provider package documents its ID; this package exports
`AGENT_FRAMEWORK_PROVIDER_ID` for code that needs to select it explicitly. A
closed SDK enum is not used because third-party packages may add provider IDs
without an Azure Functions SDK release.

The standalone typed decorator also defaults to the Agent Framework provider:

```python
from azurefunctions.extensions.agents.framework import markdown_agent

app = func.FunctionApp()


@markdown_agent(
    app,
    arg_name="agent",
    agent_name="orders",
    client_factory=create_chat_client,
)
async def process_order(req: func.HttpRequest, agent: Agent):
    ...
```

Its optional `provider` parameter can select another installed provider for one
binding. Pass that provider's options as keyword arguments; provider-specific
packages remain the source of truth for their IDs and supported options.

Place the complete instructions at `orders.agent.md` or
`agents/orders.agent.md`. The file is raw UTF-8 text; no front matter or runtime
configuration is interpreted.

The generic core form is also supported:

```python
from azurefunctions.extensions.agents.framework import AGENT_FRAMEWORK_PROVIDER_ID

app = func.FunctionApp()


@app.markdown_agent(
    provider=AGENT_FRAMEWORK_PROVIDER_ID,
    arg_name="agent",
    agent_name="orders",
    client_factory=create_chat_client,
)
async def process_order(req: func.HttpRequest, agent: Agent):
    ...
```

Typed constructors and decorators expose the MAF Agent options supported by
this release: tools, description, default options, context providers,
middleware, per-service-call history persistence, compaction strategy,
tokenizer, and additional properties. The extension owns the Agent client,
name, and instructions.

`AiApp` makes `agent_framework` the default provider, but one app may use other
installed providers too. Select another provider on an individual binding and
pass its options directly:

```python
@app.markdown_agent(
    provider="langgraph",
    arg_name="agent",
    agent_name="researcher",
    recursion_limit=10,
)
async def research(agent: object):
    ...
```

## Durable Agents

Durable orchestration support is optional:

```text
pip install "azurefunctions-extensions-agents-framework[durable]"
```

Use `DurableAiApp` and call `context.call_agent(agent_name, input_)` inside a
synchronous generator orchestrator. Agent execution is isolated in an activity
so replay performs no nondeterministic work. Importing the package remains safe
without Durable installed; constructing `DurableAiApp` reports the exact extra
to install when it is absent.

All `call_agent()` invocations use the provider configured by `DurableAiApp`.
V1 does not support selecting another provider from an orchestrator.
