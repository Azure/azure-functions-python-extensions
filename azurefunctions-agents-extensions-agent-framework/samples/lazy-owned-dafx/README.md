# Endpoint-only durable markdown agent

This sample sets `durable=True` on `AgentFunctionApp` and supplies
`orders.agent.md`. Discovery registers the agent's DAFX entity and
`POST /api/agents/orders/run` endpoint. There are no handwritten HTTP functions,
orchestrators, or agent instance registrations.

Every `.agent.md` file directly in the app root or `agents/` is discovered.
Indexing compiles recipes without constructing clients. Each entity execution
opens and closes a fresh Agent through the compiled binding's `open_agent()`
lifecycle. DAFX stores conversation history separately in durable session state.

`LocalChatClient` counts user messages and echoes the latest prompt. It makes
no model calls and needs no model credentials. It is kept in a standalone module
so tests can import it without indexing the app. For a generator orchestrator
with an injected proxy, see the
[durable binding sample](../durable-markdown-binding/README.md).

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

Run only the sample tests with:

```powershell
python -m pytest -q azurefunctions-agents-extensions-agent-framework/tests/test_samples.py
```

The tests exercise indexing and local entity execution. They do not replace a
deployed Functions host or storage integration test. See
[VALIDATION.md](VALIDATION.md) for the current verification results and limitations.

## Run locally

Running the example under Core Tools additionally requires the Python SDK 2
compatible Functions host/extension and a configured Durable backend. Those are
not provisioned by this sample. Set `FUNCTIONS_WORKER_RUNTIME=python` and
`AzureWebJobsStorage` for your backend, then run `func start` from this directory.

```bash
curl -X POST http://localhost:7071/api/agents/orders/run \
  -H "Content-Type: application/json" \
  -d '{"message":"Assess the order.","session_id":"orders-demo"}'
```

Send another request with the same `session_id` to continue the conversation.
The local client responds with `User turn 1: Assess the order.` on the first
turn and counts subsequent turns from the restored history. Use a new session
ID to start over. Add a function key when calling a hosted app.

## Boundaries

- No DAFX import, inner app, or entity registration on the non-durable path.
- Declare durable agents before indexing. Ambiguous markdown names fail instead
  of silently selecting a file.
- Durable markdown names start with an ASCII letter or digit and contain only
  ASCII letters, digits, hyphens, and underscores. These names become routes and
  entity identifiers, not just filenames.
- The outer app remains the only worker-indexed app and combines both registries.
- Agent HTTP endpoints are enabled. Health and MCP endpoints are disabled. The
  SDK's built-in durable HTTP activity/orchestrator remain registered.
- Normal `markdown_agent()` is unchanged. Durable orchestrators use the new
  binding and yield proxy tasks instead of calling `context.call_agent()`.