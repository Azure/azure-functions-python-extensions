# Azure Functions Agents Base Extension

Framework-neutral provider and lifecycle contracts for Python Agent integrations
with Azure Functions.

This package is infrastructure for provider extensions. Applications should
install a provider package such as `azurefunctions-extensions-agents-framework`.

## Provider contract

Provider packages register a zero-argument factory in the
`azurefunctions.extensions.agents.providers` entry-point group. The entry-point
name is the provider ID. The factory returns an `AgentProvider` with a matching
`provider_id`, its distribution name, and a `compile_binding()` implementation.

`compile_binding()` receives the complete markdown instructions, logical Agent
name, immutable provider options, injected parameter annotation, and an
`AgentCapabilities` bundle. Providers declare `supported_capabilities` and
translate neutral Skill/MCP definitions into their own runtime objects. The
compiled recipe creates a fresh Agent context for each invocation and can run
an Agent from a Durable activity.

Applications use `azure.functions.FunctionApp.markdown_agent()` or install a
typed provider package. Each Function App uses one provider. `AiApp` pins it at
construction; a plain `FunctionApp` pins it on its first
`markdown_agent(provider=...)` use. A later different provider is rejected.
Provider discovery is cached, while live Agents and clients are never cached.

Provider defaults are app-scoped. Binding options override defaults only for
that binding. The app root is configured once on `AiApp` or inferred from
`AzureWebJobsScriptRoot` and then the current directory for a plain app;
decorators cannot override it.

## Markdown lookup

An `agent_name` resolves exactly one UTF-8 file:

```text
<app_root>/<agent_name>.agent.md
<app_root>/agents/<agent_name>.agent.md
```

The entire file is passed to the provider unchanged. Front matter, YAML,
substitutions, tools, skills, MCP configuration, and history are not parsed by
this package. If both locations exist, lookup fails as ambiguous. Absolute
paths, separators, traversal components, and symlinks outside `app_root` are
rejected.

## Skills and MCP discovery

The base package discovers immutable definitions from the shared app root:

```text
skills/<skill-name>/SKILL.md
mcp.json
```

Base discovery records safely contained directories that contain `SKILL.md`
without reading or interpreting those files. Each provider owns Skill format
parsing and validation. MCP servers must use `http` or `streamable-http`; local
commands and stdio are rejected. Discovery does not execute scripts, resolve
environment references, create credentials, or connect to servers.

Every Agent binding receives all valid Skills and MCP servers discovered from
the app root. V1 has no app-level or per-binding capability selectors. Treat
placing a definition under the app root as granting every Agent in that app
access to it; use separate Function Apps when capabilities require isolation.

Only immutable definitions are retained in app state. Provider packages must
create and close clients, credentials, tools, and other live resources within
each invocation.

## Durable support

Provider packages expose Durable support through their own `[durable]` extra.
The base extra installs `azure-functions-durable>=1.2.10,<2`; normal imports do
not import or require Durable Functions. `DurableAgentContext.call_agent()`
schedules a hidden activity with a deterministic, JSON-only payload and always
uses the `DurableAiApp` provider. All file, client, Agent, model, and
tool I/O occurs in the activity, never in the orchestrator.
