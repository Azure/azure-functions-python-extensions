---
name: add-agent-binding
description: 'Add a new SDK-backed Agent binding provider to azure-functions-python-extensions. USE WHEN: integrating another agent SDK, creating an AgentFunctionApp and markdown_agent decorator, injecting an SDK Agent/session type, forwarding SDK creation arguments, implementing provider lifecycle or capability adapters, adding Durable support, samples, tests, packaging, or CI wiring. NOT FOR: adding features to an existing provider without a new binding package, Connector SDK types (use add-connector-type), or application-only Agent samples.'
---

# Add an Agent Binding

Use this workflow to add an SDK-backed provider package built on
`azurefunctions-agents-extensions-base`.

The binding should let customers author a normal Azure Function while receiving
the SDK's native Agent or session type as an injected parameter. Keep SDK setup,
configuration discovery, lifecycle management, and Durable execution inside the
extension.

## Reference Implementations

Choose the nearest existing provider before writing code:

| Provider | Use as a reference when |
| --- | --- |
| `azurefunctions-agents-extensions-agent-framework` | The SDK creates a fresh client and Agent for each invocation. |
| `azurefunctions-agents-extensions-copilot-sdk` | The SDK has a process-owning client that should be cached while sessions remain invocation-scoped. |
| `azurefunctions-agents-extensions-base` | The provider contract, discovery model, binding injection, and Durable bridge need clarification. |

Do not copy a lifecycle merely because it exists. Determine what the target SDK
owns and how each object is safely closed.

## Required Decisions

Before editing, identify and record these decisions in the working notes or PR:

| Decision | Questions to answer |
| --- | --- |
| Injected SDK type | What native SDK type should the Function parameter receive? Is it async-context-managed? |
| Client lifecycle | Is the client cheap and invocation-scoped, or a process/runtime owner that must be cached? Is construction thread-safe? |
| Invocation lifecycle | What fresh Agent/session/context is created per invocation, and how is it closed on success, failure, and cancellation? |
| Execution API | How does the native object execute a prompt, and how is the final text validated and returned from `run_agent()`? |
| Configuration | Which settings have secure defaults? Which require explicit environment variables or factories? |
| SDK arguments | Which `create_*` arguments should customers pass directly on `@app.markdown_agent(...)`? Which names are reserved by the extension? |
| Capabilities | Can the SDK support discovered Skills and remote HTTP MCP without changing their meaning or security? |
| Durable | Can a compiled binding execute from the shared Durable activity without relying on a live injected object? |

If one of these is unknown, inspect the installed SDK signatures and lifecycle
documentation or run a focused probe before implementing it.

## Package Shape

Use the provider ID `{provider_id}` and normalized package suffix
`{provider-id}`:

```text
azurefunctions-agents-extensions-{provider-id}/
├── LICENSE
├── MANIFEST.in
├── README.md
├── pyproject.toml
├── azurefunctions/agents/extensions/{provider_module}/
│   ├── __init__.py
│   ├── apps.py
│   ├── provider.py
│   └── py.typed
├── samples/
└── tests/
```

Add another module such as `options.py` only when it provides meaningful public
typing or separates substantial logic. Do not create abstractions solely to
match another provider's file count.

## Procedure

### 1. Define the Public Customer Experience

Start with the intended Function code. The injected parameter should use the
SDK-native type:

```python
from target_sdk import NativeAgent
from azurefunctions.agents.extensions.target import AgentFunctionApp

app = AgentFunctionApp()


@app.route(route="orders", methods=["POST"])
@app.markdown_agent(
    arg_name="agent",
    agent_name="orders",
    streaming=True,
    reasoning_effort="high",
)
async def process_order(req: func.HttpRequest, agent: NativeAgent) -> str:
    ...
```

Use the SDK's names and types where practical. Avoid inventing an extension-only
configuration vocabulary for arguments the SDK already exposes.

### 2. Register the Provider Package

In `pyproject.toml`:

- Name the distribution `azurefunctions-agents-extensions-{provider-id}`.
- Depend on `azurefunctions-agents-extensions-base` and the target SDK.
- Add `mcp`, `durable`, and `dev` extras only when applicable.
- Include `py.typed` as package data.
- Register a zero-argument provider factory:

```toml
[project.entry-points."azurefunctions.agents.extensions.providers"]
{provider_id} = "azurefunctions.agents.extensions.{provider_module}.provider:create_provider"
```

The entry-point name, `provider_id`, and normalized distribution name must agree.

### 3. Implement the Provider Contract

In `provider.py`:

1. Define a stable provider ID constant.
2. Implement an immutable compiled binding that satisfies `CompiledAgent`:
   - `open_agent(invocation)` returns an async context manager yielding the
     injected SDK-native object.
   - `run_agent(prompt, invocation)` opens the same object, executes one prompt,
     validates the SDK response, and returns text for Durable activities.
3. Implement `AgentProvider` with:
   - `provider_id`
   - `distribution_name`
   - `supported_capabilities`
   - `compile_binding(...)`
4. Validate the injected parameter annotation when one is present. Durable
   compilation may provide `inspect.Signature.empty`, which must remain valid.
5. Validate factories synchronously and reject awaitable results with a clear
   error rather than leaking an unawaited coroutine.
6. Reject unsupported provider options with a sorted, provider-specific error.
7. Return a zero-argument `create_provider()` factory.

Keep compilation side-effect-free. It should validate and freeze a recipe, not
connect to networks or create invocation-scoped SDK objects.

### 4. Design and Test Lifecycle Ownership

Implement the lifecycle established in the Required Decisions section:

- Use `AsyncExitStack` when several SDK, MCP, credential, or session contexts
  must close together.
- Create fresh invocation state unless the SDK explicitly requires a shared
  process owner.
- If a client is cached, make first creation thread-safe, validate its concrete
  type, share it only at the intended app/binding scope, and keep sessions fresh.
- Close invocation objects on normal return, exception, and cancellation.
- Do not close a cached process client after every invocation.
- Document shutdown limitations if the host does not provide an awaited
  application-lifetime hook.

At minimum, tests must prove object counts, identity, entered/exited state,
concurrent first use when caching, and failure/cancellation cleanup.

### 5. Expose SDK Creation Arguments Directly

The decorator should accept the arguments customers would pass to the target
SDK's Agent/session creation method:

```python
def markdown_agent(
    self,
    *,
    arg_name: str,
    agent_name: str,
    client_factory: ClientFactory | None = None,
    **sdk_options: Unpack[SdkCreationOptions],
) -> Callable[[_F], _F]:
    ...
```

Follow these rules:

- Keep `arg_name` and `agent_name` extension-owned.
- Reserve only options the extension must interpret, such as
  `client_factory`, provider credentials, or custom tools.
- Forward all other supported SDK options unchanged to the SDK creation call.
- Apply customer values after extension defaults so explicit values win.
- Provide a `TypedDict` plus `Unpack` when the SDK does not publish a reusable
  typed kwargs object. Match the installed SDK signature exactly.
- At runtime, compare option names with `inspect.signature(...)` or an equally
  authoritative SDK surface and fail with a clear list of unsupported names.
- Do not silently drop unknown options.
- Test representative direct arguments, extension-default overrides, and an
  unsupported argument.

If an SDK argument collides with an extension-owned name, document and test the
chosen mapping. Prefer a top-level decorator argument when it is central to the
binding, while still passing the corresponding value to the SDK.

### 6. Add `AgentFunctionApp`

In `apps.py`:

- Subclass `azure.functions.FunctionApp` through a provider-specific mixin.
- Configure the provider once with `configure_app(...)`.
- Keep `app_root` app-scoped; never expose it as a per-binding option.
- Put app-wide defaults on `AgentFunctionApp(...)`.
- Let decorator values override app defaults for only that binding.
- Delegate `orchestration_trigger(...)` to `durable_orchestration_trigger(...)`
  when Durable is supported.
- Export only intentional public symbols from `__init__.py`.

The provider package owns this app class. Do not require changes to
`azure.functions.FunctionApp` for a provider-specific API.

### 7. Translate Discovered Capabilities

Declare only capabilities the provider actually implements. Current neutral
capabilities are `skills` and `mcp`.

For Skills:

- Consume `SkillDefinition` paths supplied by the base package.
- Let the SDK load content when that preserves its native behavior.
- Do not rediscover or reinterpret app files in the provider.

For MCP:

- Consume `MCPServerDefinition` values from the base package.
- Preserve server names, remote HTTP URLs, tool allowlists, headers, and Entra
  authentication semantics.
- Expand `$VAR` and `%VAR%` references at invocation time and report all missing
  names clearly.
- Require HTTPS when credentials or headers leave loopback.
- Keep credentials and tokens out of logs and persisted config.
- Acquire and close credentials at the narrowest safe scope; refresh tokens per
  request when the SDK transport permits it.

If the SDK cannot preserve a capability contract, omit it from
`supported_capabilities`; the base package will reject the configuration.

### 8. Add Durable Support

When supported:

- Add the base package's `durable` extra.
- Export `DurableAgentContext`.
- Add `orchestration_trigger(...)` to the provider app.
- Ensure `run_agent()` uses the same compiled instructions, options, and
  capabilities as direct injection.
- Keep SDK calls in the generated activity, never in deterministic orchestrator
  code.
- Test hidden activity registration, serialization, execution, failures, and
  missing parameter annotations.

Add a Durable sample with an HTTP starter, orchestrator, and Agent activity.
Run it with Core Tools and poll a real instance to a terminal state.

### 9. Add Samples That Demonstrate the Value

Provide a minimal non-Durable sample containing:

- `function_app.py`
- `host.json`
- `local.settings.template.json` with placeholders, never secrets
- `requirements.txt`
- at least one raw `.agent.md` file
- Skill and `mcp.json` assets when those capabilities are supported
- a concise README with runtime provisioning and local-run steps

Use the extension's defaults in the primary sample. Do not make customers
recreate the client factory merely to run the happy path.

When the SDK setup is non-trivial, add a standalone direct-SDK script that
performs the same task. It should honestly show the authentication, client and
session lifecycle, instruction loading, capability wiring, option defaults, and
response validation that the binding removes.

Add sample-indexing tests that import `function_app.py` in a subprocess and
assert the exact Function names without making live SDK calls.

### 10. Document the Binding

The package README must state:

- The SDK-native type injected by the binding.
- What client is created by default and which settings it reads.
- Which object is cached and which object is fresh per invocation.
- That `@app.markdown_agent(...)` accepts SDK creation arguments directly, with
  a short example such as `streaming=True` and `reasoning_effort="high"`.
- Reserved extension arguments and app-wide defaults.
- Permission/security defaults and when customers must replace them.
- Skill, MCP, Durable, authentication, and runtime-provisioning behavior.
- How to supply an advanced custom client factory.

Favor customer behavior over internal helper type names.

### 11. Add Tests

Mirror the provider modules under `tests/`. Cover:

- Public imports and package version.
- Provider entry-point discovery and metadata.
- Correct annotation acceptance and rejection.
- Required, defaulted, malformed, and unknown options.
- Direct forwarding of SDK creation arguments.
- App defaults and per-binding overrides.
- Native response extraction and malformed responses.
- Client and invocation lifecycle, including cancellation and concurrency.
- Skills and MCP mapping, allowlists, environment expansion, HTTPS rules,
  authentication, and cleanup.
- Durable compilation and activity execution when supported.
- Sample indexing and standard setting names.

Use SDK fakes for focused unit tests. Add a real local smoke test for the primary
sample and Durable workflow when credentials and emulators are available.

### 12. Wire Build and Release Pipelines

Add the package to all relevant matrices and jobs, not just the PR build:

- `eng/templates/jobs/build.yml`
- `eng/templates/official/jobs/build-artifacts.yml`
- `eng/templates/official/jobs/unit-tests.yml`

Install the editable base package before provider tests. Build both the source
distribution and wheel, and ensure package imports work from the built artifact.

## Validation

Run from the new package directory using its supported Python versions:

```text
python -m pip install -U -e .[dev]
python -m flake8 azurefunctions tests samples
python -m mypy azurefunctions
python -m pytest -q --instafail tests
python -m build
python -m twine check dist/*
```

Adjust paths only to match established package configuration. Also run:

- Sample indexing tests.
- A direct local invocation through Core Tools.
- A complete Durable orchestration when Durable is supported.
- `git diff --check` over the changed files.

## PR Description

Keep the PR summary customer-facing and concise. Include:

1. The package and SDK being integrated.
2. The native SDK type injected into Functions.
3. The default client and client/session lifecycle.
4. That SDK creation arguments can be passed directly to
   `@app.markdown_agent(...)`, with one short code example.
5. Supported Skills, MCP, Durable, samples, and validation.

Do not lead with internal typing helpers or implementation-only classes.

## Definition of Done

- Provider package and entry point are discoverable.
- SDK-native injection works with a fresh invocation context.
- Client ownership and cleanup behavior are explicit and tested.
- SDK creation arguments are directly usable and unknown names fail clearly.
- Supported capabilities preserve the base package contracts.
- Direct and Durable execution share one compiled binding behavior.
- Samples show both the simple binding path and, when useful, direct SDK setup.
- README, tests, build, official artifacts, and official test pipelines are updated.
- Focused checks and relevant local end-to-end workflows pass.