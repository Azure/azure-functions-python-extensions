# Azure Functions Agents Base Extension

Framework-neutral provider and lifecycle contracts for Python Agent integrations
with Azure Functions.

This package is infrastructure for provider extensions. Applications should
install a provider package such as `azurefunctions-agents-extensions-agent-framework`.

## Provider contract

Provider packages register a zero-argument factory in the
`azurefunctions.agents.extensions.providers` entry-point group. The entry-point
name is the provider ID. The factory returns an `AgentProvider` with a matching
`provider_id`, its distribution name, and a `compile_binding()` implementation.

`compile_binding()` receives the complete markdown instructions, logical Agent
name, immutable provider options, injected parameter annotation, and an
`AgentCapabilities` bundle. Providers declare `supported_capabilities` and
translate neutral Skill/MCP definitions into their own runtime objects. The
compiled recipe exposes `open_agent()` to create a fresh Agent context for each
invocation. Provider-specific adapters can use the same lifecycle for durable
entity execution.

Applications import the app class supplied by a provider package. Each Agent
Function App uses one provider, configured when the app is constructed.
Provider discovery is cached, while live Agents and clients are never cached.

Provider defaults are app-scoped. Binding options override defaults only for
that binding. The app root is configured once when the provider app is
constructed, or inferred from `AzureWebJobsScriptRoot` and then the current
directory; decorators cannot override it.

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

`discover_agent_names()` enumerates `.agent.md` files directly in these two
directories, not nested directories. Provider apps can compile the discovered
names without constructing live clients. The Microsoft Agent Framework app uses
this discovery when `durable=True` is set.

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
The base extra installs `azure-functions-durable>=2.0.0b2`; normal imports do
not import or require Durable Functions. The base package supplies discovery,
compilation, and lifecycle contracts, not an orchestration context wrapper or
hidden Agent activity.

The Microsoft Agent Framework provider offers `durable=True` discovery and a
`durable_markdown_agent()` binding. It registers compiled markdown recipes with
DAFX and injects a durable proxy into generator orchestrators. Concrete clients
and tools are created and closed through `open_agent()` during entity execution,
not indexing or orchestration replay. See the
[provider documentation](../azurefunctions-agents-extensions-agent-framework/README.md#durable-agents).
