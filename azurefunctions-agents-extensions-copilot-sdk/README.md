# Azure Functions GitHub Copilot SDK Extension

Inject GitHub Copilot SDK sessions built from raw Markdown instructions into
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

The extension uses these standard Function App settings:

| Setting | Purpose |
| --- | --- |
| `COPILOT_GITHUB_TOKEN` | GitHub token used by the default client. |
| `COPILOT_BASE_DIRECTORY` | Writable directory for isolated Copilot runtime state. |
| `COPILOT_MODEL` | Model used by Agent sessions. |

Use these exact names in `local.settings.json` and Azure Function App settings.
The extension creates the default `CopilotClient` in `mode="empty"`, disables
SDK telemetry, and does not use interactive logged-in-user authentication:

```python
import azure.functions as func
from copilot.session import CopilotSession
from copilot.session_events import AssistantMessageData
from azurefunctions.agents.extensions.copilot_sdk import AgentFunctionApp

app = AgentFunctionApp()


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
`orders.agent.md`, `orders.md`, or the same filename under `agents/`. The
`.agent.md` suffix is recommended; plain `.md` is also supported. The file is
raw UTF-8 text; no front matter or runtime configuration is interpreted. If
multiple candidates exist, lookup fails as ambiguous.

`AgentFunctionApp()` reads its model from `COPILOT_MODEL` and defaults
`on_permission_request` to `PermissionHandler.approve_all`. Pass `model=` or
`on_permission_request=` only to override those defaults. A `markdown_agent()`
decorator can override `client_factory`, `model`, `on_permission_request`,
`provider`, `tools`, and any typed Copilot session option for one binding.
`app_root` can be set only on `AgentFunctionApp`.

`PermissionHandler.approve_all` should be used only when every exposed tool is
trusted. Supply a restrictive SDK permission handler when tools can access
privileged data or perform external actions.

### Customize Copilot sessions

Pass Copilot session options directly to `markdown_agent()`. Known keyword
arguments provide editor completion and static validation without string keys:

```python
@app.markdown_agent(
	arg_name="agent",
	agent_name="orders",
	reasoning_effort="high",
	streaming=True,
	enable_session_store=True,
)
async def process_order(
	req: func.HttpRequest,
	agent: CopilotSession,
) -> str:
	...
```

The options type remains open so arguments added by newer compatible Copilot
SDK releases can be passed without an extension update. At compile time, the
extension validates every name against the installed SDK's
`CopilotClient.create_session()` signature and rejects unsupported names with a
clear error. Session options are applied after the extension defaults, so they
take precedence. This includes
extension-generated values such as `system_message`, `tools`,
`available_tools`, `mcp_servers`, `skill_directories`, and their enablement
flags. Override those values only when intentionally replacing the Agent's
instructions or discovered capabilities.

For app-wide defaults, construct the exported typed options object:

```python
from azurefunctions.agents.extensions.copilot_sdk import (
	AgentFunctionApp,
	CopilotSessionOptions,
)

app = AgentFunctionApp(
	session_options=CopilotSessionOptions(
		reasoning_effort="high",
		streaming=True,
	),
)
```

Supplying any session option to `markdown_agent()` replaces the app-wide
`session_options` object for that binding.

## Authentication and BYOK

Keep GitHub tokens and model-provider credentials in Function App settings or a
secret store. Do not put them in source, `.agent.md`, or `mcp.json` files. The
default client reads `COPILOT_GITHUB_TOKEN` and `COPILOT_BASE_DIRECTORY` when it
is first needed.

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
	provider=provider,
)
```

The Copilot SDK also supports Azure and Anthropic provider configurations. Use
the provider fields supported by the installed SDK version, and keep all
credentials outside checked-in configuration.

For advanced client authentication or runtime transports, pass a synchronous
zero-argument `client_factory`. The extension calls it once, validates the
result, and caches that `CopilotClient`:

```python
from copilot import CopilotClient


def create_copilot_client() -> CopilotClient:
	return CopilotClient(...)


app = AgentFunctionApp(
	client_factory=create_copilot_client,
)
```

App-level bindings share the app's cached client. A decorator-level
`client_factory` override has a separate cache for that binding. Factories must
return `CopilotClient` synchronously; awaitable results are rejected.

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

The extension creates one client lazily and reuses it across invocations for the
lifetime of the Python worker process. Each invocation creates and closes a
fresh session. Default ephemeral sessions are deleted after disconnect so they
do not accumulate in the cached client's registry. Setting
`enable_session_store=True` preserves session data instead. The extension
replaces the session system message with the raw Agent instructions and disables
ambient Copilot configuration discovery, session persistence, memory,
telemetry, built-in Skills, and tool search.
Explicit Python tools, discovered Skills, and discovered MCP servers remain
available.

Sessions and Entra credentials are closed on success, error, and cancellation.
The cached client remains open so later invocations can reuse its runtime
connection.

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