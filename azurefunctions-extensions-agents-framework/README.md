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

Place the complete instructions at `orders.agent.md` or
`agents/orders.agent.md`. The file is raw UTF-8 text; no front matter or runtime
configuration is interpreted.

The generic core form is also supported:

```python
app = func.FunctionApp()


@app.markdown_agent(
    provider="agent_framework",
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
