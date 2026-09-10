# Durable YAML workflows

[function_app.py](function_app.py) enables `durable=True, workflows=True` with no
handwritten handlers or orchestrators. The extension loads YAML through MAF's
`WorkflowFactory` and passes the resulting graphs to DAFX's `workflows=`
constructor. DAFX supplies the orchestration, activities, and HTTP routes.

- [OrderReview.workflow.yaml](workflows/OrderReview.workflow.yaml) copies the
  request's `order` into shared state, builds a prompt, calls the Markdown
  `writer`, and emits `Local.reply`. `resultProperty` belongs on the agent action;
  `output.autoSend: false` leaves output to the final `SendActivity`.
- [Approval.workflow.yaml](workflows/Approval.workflow.yaml) is a separate
  workflow. `Question` waits for input, saves it in `Local.answer`, then
  `SendActivity` emits the answer. It is not an approval gate for `OrderReview`.

[local_chat_client.py](local_chat_client.py) is copied from the
[durable binding sample](../durable-markdown-binding/README.md). It counts user
turns and echoes the prompt without model credentials or network calls. It does
not perform a real order review or interpret the writer's instructions.

## Install and run

Use **Python 3.13**. YAML workflows need PowerFx, and this prototype rejects the
YAML opt-in on Python 3.14. From the repository root, in a Python 3.13 virtual
environment, install the local packages and both optional extras.

```powershell
python -m pip install -e ./azurefunctions-agents-extensions-base
python -m pip install -e './azurefunctions-agents-extensions-agent-framework[durable,workflows]'
```

The durable extra pins the prototype dependencies from
[DAFX PR #72](https://github.com/microsoft/agent-framework-durable-extension/pull/72).
Core Tools execution also needs an SDK 2-compatible Functions host/extension and
a configured Durable backend. This sample does not provision or verify either.
Set `FUNCTIONS_WORKER_RUNTIME=python` and `AzureWebJobsStorage` for your backend,
then start from the sample directory.

```powershell
cd azurefunctions-agents-extensions-agent-framework/samples/durable-yaml-workflow
func start
```

## Invoke OrderReview

In another PowerShell terminal, start a workflow with a nonempty string `order`.
The JSON body is the workflow input, not an agent `message` envelope.

```powershell
$run = Invoke-RestMethod -Method Post `
    -Uri http://localhost:7071/api/workflow/OrderReview/run `
    -ContentType application/json -Body '{"order":"42"}'
Invoke-RestMethod -Uri $run.statusQueryGetUri
```

The start response is `202` with `instanceId` and `statusQueryGetUri`. Query the
status URL again until completion. The expected `output` for this input is
`["User turn 1: Review order 42."]`.

## Invoke Approval

```powershell
$approval = Invoke-RestMethod -Method Post `
    -Uri http://localhost:7071/api/workflow/Approval/run `
    -ContentType application/json -Body '{}'
$status = Invoke-RestMethod -Uri $approval.statusQueryGetUri
$status.pendingHumanInputRequests
```

Query the status URL again until `pendingHumanInputRequests` contains the
question. Use its `respondUrl`, not the YAML action ID. Send the response object
expected by `Question`.

```powershell
$pending = $status.pendingHumanInputRequests[0]
Invoke-RestMethod -Method Post -Uri $pending.respondUrl `
    -ContentType application/json -Body '{"user_input":"approved"}'
Invoke-RestMethod -Uri $approval.statusQueryGetUri
```

Query status again until completion. The expected `output` is `["approved"]`.
This example accepts free text. It demonstrates pause/resume, not approval
validation, authorization, or a business side effect.

## Routes and execution

With the default `/api` prefix, each workflow name (`OrderReview` and `Approval`)
gets these generated routes.

| Method | Route |
| --- | --- |
| POST | `/api/workflow/NAME/run` |
| GET | `/api/workflow/NAME/status/{instanceId}` |
| POST | `/api/workflow/NAME/respond/{instanceId}/{requestId}` |

The pinned dependencies index 20 functions. Workflow suffixes below are appended
to the prefix with `-`; each prefix itself is the orchestrator function.

| Prefix | Generated suffixes |
| --- | --- |
| `dafx-OrderReview` | `start`, `status`, `respond`, `_workflow_entry`, `capture_order`, `prepare_prompt`, `review_order`, `send_review` |
| `dafx-Approval` | `start`, `status`, `respond`, `_workflow_entry`, `request_approval`, `send_answer` |

The other functions are `dafx-writer`, `http-writer`, `BuiltIn__HttpActivity`,
and `BuiltIn__HttpPollOrchestrator`.

`durable=True` still discovers and publishes every Markdown agent directly in
the app root or `agents/`, including `POST /api/agents/writer/run`. Calling that
endpoint bypasses both workflows. Hosted requests need a function key, including
requests to returned status and response URLs.

Inside a YAML graph, agent actions run as **durable activities** through the
`MarkdownDurableAgent` lifecycle. Each run opens and closes a fresh Agent and
client. These actions do not call the writer's durable entity or share that
endpoint's entity session. DAFX carries workflow shared state between actions.

## Boundaries

See [VALIDATION.md](VALIDATION.md) for measured results and test limitations.

- `workflows=True` requires `durable=True` and the `[durable,workflows]` extras.
- Only `*.workflow.yaml` and `*.workflow.yml` directly in the app root or its
  `workflows/` directory are discovered. Discovery is not recursive and does not
  load arbitrary YAML files.
- Each definition uses `kind: Workflow` and an explicit `name` of 1–63 ASCII
  letters, digits, `_`, or `-`, starting with a letter. Names must be unique
  ignoring case. The YAML name, not the filename, determines the route.
- Agent references must be static Markdown names, such as `agent: writer` or
  `agent: {name: writer}`, matching [writer.agent.md](agents/writer.agent.md).
  Inline top-level `agents` definitions, file-based YAML agents, and dynamic
  agent names are not supported. Workflow-level `InvokeFunctionTool`,
  `HttpRequestAction`, and `InvokeMcpTool` are rejected because no handlers are
  configured for them. Python/MCP tools on the referenced agents remain supported.
- Use either root `actions` or `trigger.actions`, not both. `If` supports `then`
  (or `actions`) and `else`; `elseActions` belongs to `ConditionGroup`.
- The declarative loader is pinned to 1.0.3. Its internal action registry is used
  to reject unknown actions rather than allowing the loader to warn and skip them.
- Keep action IDs stable across reloads. The samples supply explicit IDs.
- `OrderReview` expects the documented input shape and adds no request schema
  validation. Local execution or indexing is not host/backend validation.
