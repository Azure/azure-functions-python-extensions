# Durable markdown binding

This local example places `durable_markdown_agent` below `orchestration_trigger`
on a synchronous generator. The binding selects `agents/orders.agent.md`,
registers its private DAFX entity, and injects an orchestration proxy.
It needs neither bulk discovery nor explicit agent instance registration.
The inner DAFX host is deferred until `app.get_functions()`.

The orchestrator creates one session and yields two `agent.run()` tasks with
that session. The deterministic client counts user messages in the restored
history, so the output is:

```json
{
  "assessment": "User turn 1: Assess the order.",
  "plan": "User turn 2: Make a fulfillment plan."
}
```

The same small `LocalChatClient` helper is included in each local sample so
either directory can be run on its own. There are no model credentials or
network calls in the client. Registration compiles recipes; each entity run
opens and closes a fresh Agent through `open_agent()`. Session history belongs
to DAFX, not the client instance or orchestrator process.

## Run locally

Follow the [endpoint-only sample's installation steps](../lazy-owned-dafx/README.md#install-and-verify).
Both samples use the optional dependencies pinned to DAFX PR #72. Running under
Core Tools requires an SDK 2-compatible Functions host/extension and configured
Durable backend, which this sample does not provision. Set
`FUNCTIONS_WORKER_RUNTIME=python` and `AzureWebJobsStorage`, then run `func start`
from this directory.

```bash
curl -X POST http://localhost:7071/api/orders/orchestrations
```

The HTTP starter returns a check-status response. Follow its status URL to read
the orchestration output. The starter uses fixed prompts and ignores the request
body. Each orchestration creates a new session.

The binding defaults to `expose_http_endpoint=False`, so there is no
`POST /api/agents/orders/run` route. Only the handwritten starter exposes this
flow. Add a function key when calling a hosted app.

To deliberately expose the agent directly, add `expose_http_endpoint=True` to
the binding. That route bypasses the parent orchestration. The constructor's
`expose_agent_endpoints` controls bulk discovery only. Discovery and a binding
reuse one registration, with HTTP exposure enabled if either opts in.

For automatic registration of all root and `agents/` markdown files without
handwritten functions, see the [endpoint-only sample](../lazy-owned-dafx/README.md).