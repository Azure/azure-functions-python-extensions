# Azure Functions GitHub Copilot SDK Extension

Inject GitHub Copilot SDK sessions built from raw `.agent.md` instructions into
Python Azure Functions.

## Install

```text
pip install azurefunctions-agents-extensions-copilot-sdk
```

Install Entra authentication for remote MCP servers with the MCP extra:

```text
pip install "azurefunctions-agents-extensions-copilot-sdk[mcp]"
```

Install Durable Functions support with the durable extra:

```text
pip install "azurefunctions-agents-extensions-copilot-sdk[durable]"
```

The GitHub Copilot SDK uses a native runtime. Pre-provision it during image or
deployment construction so a Function invocation never downloads executable
content:

```text
python -m copilot download-runtime
```

## Use a Copilot SDK Agent app

Create a zero-argument synchronous factory that returns a fresh
`CopilotClient`. Server environments should use explicit authentication rather
than an interactive logged-in user:

```python
import os

import azure.functions as func
from copilot import CopilotClient
from copilot.session import CopilotSession, PermissionHandler
from copilot.session_events import AssistantMessageData
from azurefunctions.agents.extensions.copilot_sdk import AgentFunctionApp


def create_copilot_client() -> CopilotClient:
	return CopilotClient(
		mode="empty",
		github_token=os.environ["COPILOT_GITHUB_TOKEN"],
		use_logged_in_user=False,
		telemetry=None,
	)


app = AgentFunctionApp(
	client_factory=create_copilot_client,
	model=os.environ["COPILOT_MODEL"],
	on_permission_request=PermissionHandler.approve_all,
)


@app.route(route="orders", methods=["POST"])
@app.markdown_agent(arg_name="agent", agent_name="orders")
async def process_order(
	req: func.HttpRequest,
	agent: CopilotSession,
) -> str:
	response = await agent.send_and_wait(req.get_body().decode())
	if response is None or not isinstance(response.data, AssistantMessageData):
		raise RuntimeError("Copilot did not return a final assistant message")
	return response.data.content
```

`AgentFunctionApp` subclasses `azure.functions.FunctionApp` and pins every
Agent binding in the app to this provider. Place the complete instructions at
`orders.agent.md` or `agents/orders.agent.md`. The file is raw UTF-8 text; no
front matter or runtime configuration is interpreted.

The app-level options are defaults. A `markdown_agent()` decorator can override
`client_factory`, `model`, `on_permission_request`, `provider`, and `tools` for
one binding. `app_root` can be set only on `AgentFunctionApp`.

`PermissionHandler.approve_all` should be used only when every exposed tool is
trusted. Supply a restrictive SDK permission handler when tools can access
privileged data or perform external actions.

## Authentication and BYOK

Keep GitHub tokens and model-provider credentials in Function App settings or a
secret store. Do not put them in source, `.agent.md`, or `mcp.json` files. A
factory is called once per invocation, so it can read current settings without
sharing a client across requests.

The optional `provider` value is passed to the Copilot SDK session for bring
your own key (BYOK) scenarios. For example:

```python
import os

from copilot.session import ProviderConfig

provider: ProviderConfig = {
	"type": "openai",
	"wire_api": "responses",
	"base_url": os.environ["MODEL_BASE_URL"],
	"api_key": os.environ["MODEL_API_KEY"],
}

app = AgentFunctionApp(
	client_factory=create_copilot_client,
	model=os.environ["COPILOT_MODEL"],
	provider=provider,
)
```

The Copilot SDK also supports Azure and Anthropic provider configurations. Use
the provider fields supported by the installed SDK version, and keep all
credentials outside checked-in configuration.

## Skills and MCP servers

Skills and remote MCP servers are discovered automatically from the app root:

```text
skills/inventory/SKILL.md
mcp.json
```

The base extension discovers Skill directory paths without reading their
contents. The Copilot SDK loads and validates the Skill files for each session.

V1 supports remote HTTP MCP transports only:

```json
{
	"servers": {
		"inventory": {
			"type": "streamable-http",
			"url": "$INVENTORY_MCP_URL",
			"tools": ["lookup_stock"],
			"headers": {"X-Tenant": "%TENANT_ID%"},
			"auth": {
				"scope": "$INVENTORY_MCP_SCOPE",
				"client_id": "%AZURE_CLIENT_ID%"
			}
		}
	}
}
```

`$VAR` and `%VAR%` references are resolved for each invocation. Missing values
fail before session creation. Servers with headers or Entra authentication must
use HTTPS, except for explicit loopback development endpoints. Entra tokens are
acquired through `DefaultAzureCredential` and held only for the invocation.

Every Agent in the Function App receives all valid Skills and MCP servers under
the app root. V1 has no app-level or per-binding capability selectors. Skills,
MCP servers, and Python `tools=` can perform privileged operations; use separate
Function Apps when capability sets require isolation.

## Invocation lifecycle

A new client and session are created for every Function invocation. The
extension replaces the session system message with the raw Agent instructions
and disables ambient Copilot configuration discovery, session persistence,
memory, telemetry, built-in Skills, and tool search. Explicit Python tools,
discovered Skills, and discovered MCP servers remain available.

Clients, sessions, and Entra credentials are closed on success, error, and
cancellation. The factory must return `CopilotClient` synchronously; shared or
awaitable clients are rejected.

## Durable Agents

Use `context.call_agent(agent_name, input_)` inside a synchronous generator
orchestrator. Agent execution runs in the extension's hidden activity, keeping
orchestrator replay deterministic:

```python
from azurefunctions.agents.extensions.copilot_sdk import DurableAgentContext


@app.orchestration_trigger(context_name="context")
def order_orchestrator(context: DurableAgentContext):
	assessment = yield context.call_agent(
		"orders",
		{"order": context.get_input()},
	)
	return {"assessment": assessment}
```

Importing the package remains safe without Durable installed. Using Durable
decorators requires the `[durable]` extra. All Durable Agent calls use the
provider and capabilities configured by `AgentFunctionApp`; an orchestrator
cannot select a different provider or capability set in V1.

## Current limitations

- Python 3.13 or later is required.
- Only remote HTTP MCP servers are supported; local process transports are not.
- Agent files contain raw instructions only; front matter is not interpreted.
- Capability filtering within one Function App is not supported in V1.
- Native runtime provisioning is an application deployment responsibility.

See `samples/agent_samples_copilot-sdk` for direct HTTP and queue triggers and
`samples/agent_samples_copilot-sdk_durable` for Durable orchestration.