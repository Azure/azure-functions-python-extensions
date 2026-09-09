# Lazy-owned DAFX prototype

This branch explores app composition, not a replacement of `context.call_agent()`.
The bindings `AgentFunctionApp` remains the only worker-indexed app. Calling
`add_durable_agent()` creates a private DAFX app and registers an entity there.
The outer `get_functions()` combines both registries and rejects name collisions.
`get_agent()` delegates to DAFX without creating functions during execution.

The example has a normal HTTP function and a two-turn durable orchestration.
It uses a deterministic local chat client, so no model credentials are needed.
The two turns explicitly share a session. Caller-owned registered agents do not
use the markdown binding's per-invocation client/tool lifecycle.

## Install and verify

Use Python 3.13 or later. From the repository root, in a fresh virtual environment:

```powershell
python -m pip install -e ./azurefunctions-agents-extensions-base
python -m pip install -e './azurefunctions-agents-extensions-agent-framework[dev,durable]'
python -m pytest -q --import-mode=importlib azurefunctions-agents-extensions-base/tests azurefunctions-agents-extensions-agent-framework/tests
```

The optional extra pins both DAFX packages to commit
`aa9529ec489e16ac64b73bd68d5adbb8e4945258` from
[DAFX PR #72](https://github.com/microsoft/agent-framework-durable-extension/pull/72).
The published DAFX packages currently require SDK 1.x and cannot satisfy this
PR's SDK 2.x requirements. These Git dependencies are for local prototyping, not
for publishing this package to PyPI. Normal installs do not install DAFX.

The tests invoke the SDK's indexed entity handler with the protobuf request and
response format used by the Functions host. They round-trip entity state between
two turns and complete real DAFX tasks. The scheduler and model service are local
test substitutes. This is not a deployed Functions host or storage integration test.

Running the example under Core Tools additionally requires the Python SDK 2
compatible Functions host/extension and a configured Durable backend. Those are
not provisioned by this sample. POST `/api/orders` to start it and follow the
returned status URL. GET `/api/hello` exercises the normal HTTP path.

## Boundaries

- No DAFX import, inner app, or entity registration on the non-durable path.
- Register all durable agents before indexing. Late registration is rejected.
- Re-registering the same instance is harmless. Different agents with the same
  case-insensitive name are rejected rather than silently shadowed.
- DAFX's generated agent HTTP, health, and MCP endpoints are disabled. The SDK's
  built-in durable HTTP activity/orchestrator remain registered.
- Existing `markdown_agent()` and activity-based `context.call_agent()` are
  unchanged. Markdown-to-DAFX factory/lifecycle adaptation is not implemented.