# Durable YAML workflows

[function_app.py](function_app.py) enables `discover_workflows=True` with no
handwritten handlers or orchestrators. The extension loads YAML through MAF's
public `WorkflowFactory.create_workflow_from_yaml_path()` and passes the
resulting graphs to DAFX's `workflows=` constructor. The default factory receives
adapters for all discovered Markdown agents. DAFX supplies the orchestration,
activities, and HTTP routes.

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

Use **Python 3.13** to reproduce the verified expression execution. Python
support follows MAF's dependencies, with no extension-level Python 3.14 rejection.
MAF declarative 1.0.3 excludes PowerFx on Python 3.14, and expression execution
has only been verified on 3.13. From the repository root, in a Python 3.13
virtual environment, install the local packages and both optional extras.

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

The sample indexes 18 functions. Workflow suffixes below are appended to the
prefix with `-`. Each prefix itself is the orchestrator function.

| Prefix | Generated suffixes |
| --- | --- |
| `dafx-OrderReview` | `start`, `status`, `respond`, `_workflow_entry`, `capture_order`, `prepare_prompt`, `review_order`, `send_review` |
| `dafx-Approval` | `start`, `status`, `respond`, `_workflow_entry`, `request_approval`, `send_answer` |

The other functions are `BuiltIn__HttpActivity` and
`BuiltIn__HttpPollOrchestrator`.

`discover_workflows=True` registers the two graphs and publishes their routes
with the default `expose_workflow_endpoints=True`. Agent discovery is disabled,
so there is no `dafx-writer` entity or `POST /api/agents/writer/run` route. The
default factory still receives the writer Markdown adapter for workflow actions.
The inner DAFX host is created at `app.get_functions()`, not app construction.
Hosted requests need a function key, including requests to returned status and
response URLs.

Inside this sample's YAML graph, the writer action runs as a **durable activity**
through the `MarkdownDurableAgent` lifecycle. Each execution opens and closes a
fresh Agent, client, and tools. It does not call the writer's durable entity or
use an entity session. DAFX carries workflow shared state between actions.

Inline YAML agents and custom-factory agents instead follow MAF's or the
factory's construction and resource lifecycle. Agents and clients may be created
during app initialization/indexing. The extension does not give them the
Markdown adapter's per-execution open/close lifecycle.

## Configure the factory

The default factory supports native MAF agent definitions and dynamic names as
well as Markdown references such as `agent: writer`. Supply `workflow_factory=`
to configure a public `WorkflowFactory` with an `agent_factory`, agents, tools,
HTTP or MCP handlers, or configuration. The supplied object is used unchanged,
without automatically merging discovered Markdown agents into its registry.
Supplying a factory does not enable agent discovery or standalone endpoints.
Factory configuration is also allowed without bulk discovery, for use with a
selective `durable_workflow` binding.

See the [configured factory sample](../configured-workflow-factory/README.md)
for a tool-only workflow using `register_tool()` and `configuration`, with no
agent client or external service.

## Boundaries

See [VALIDATION.md](VALIDATION.md) for historical results and test limitations.

- Workflow hosting needs the `[durable,workflows]` extras. `discover_workflows`
  and `discover_agents` are independent switches, both disabled by default.
- Constructor exposure options apply only to bulk discovery. Selective bindings
  are private unless their own `expose_http_endpoint=True` is set. See the
  [child workflow sample](../durable-workflow-binding/README.md).
- Generated workflow routes bypass any handwritten parent policy. Disabling a
  standalone route is not a separate authorization boundary.
- Only `*.workflow.yaml` and `*.workflow.yml` directly in the app root or its
  `workflows/` directory are discovered. Discovery is not recursive and does not
  load arbitrary YAML files. Discovered entry files must stay within the app root.
- Relative references inside YAML use MAF's native resolution from the workflow
  file's directory, not an extension sandbox. Deploy only trusted workflow files
  and references.
- The returned MAF `Workflow` needs a stable name of 1–63 ASCII letters, digits,
  `_`, or `-`, starting with a letter, unique ignoring case. The resulting name,
  not the filename, determines the route. These samples set explicit names.
- YAML parsing and graph construction follow the installed MAF loader, including
  its warnings, errors, and handler requirements. There is no extension action
  allowlist or separate inline/file/dynamic-agent or tool-action gate. DAFX
  hosting validations still apply. This is not exhaustive execution coverage of
  MAF features.
- The workflows extra accepts `agent-framework-declarative>=1.0.3,<2` and uses
  its public factory API, not a private action registry.
- Keep action IDs stable across reloads. The samples supply explicit IDs.
- `OrderReview` expects the documented input shape and adds no request schema
  validation. Local execution or indexing is not host/backend validation.
