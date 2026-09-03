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
name, immutable provider options, and the injected parameter annotation. It
returns a `CompiledAgent` recipe that creates a fresh Agent context for each
invocation and can run an Agent from a Durable activity.

Applications use `azure.functions.FunctionApp.markdown_agent()` or install a
typed provider package. Each Agent binding selects a provider, so providers may
coexist in one app. `AiApp` supplies a default provider; an explicit
`markdown_agent(provider=...)` overrides it for one binding. Provider discovery
is cached, while live Agents and clients are never cached.

Provider defaults are stored independently. Configure reusable defaults for an
additional provider during startup with:

```python
app.configure_agent_provider(
    provider="langgraph",
    client_factory=create_langgraph_client,
)
```

The first call that uses a provider freezes its defaults. Binding options
override those defaults only for that binding. All providers share one app root.

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

## Durable support

Provider packages expose Durable support through their own `[durable]` extra.
The base extra installs `azure-functions-durable>=1.2.10,<2`; normal imports do
not import or require Durable Functions. `DurableAgentContext.call_agent()`
schedules a hidden activity with a deterministic, JSON-only payload containing
the selected provider ID. It uses the app default unless
`call_agent(..., provider="langgraph")` is explicit. Additional Durable
providers must be registered with `configure_agent_provider()` during startup
so their non-serializable defaults remain outside orchestration state. All file,
client, Agent, model, and tool I/O occurs in the activity, never in the
orchestrator.
