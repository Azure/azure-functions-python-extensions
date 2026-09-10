# Durable workflow binding

[function_app.py](function_app.py) places `durable_workflow` below
`orchestration_trigger` on a synchronous generator. The binding selects
[Child.workflow.yaml](workflows/Child.workflow.yaml) without bulk discovery.
The child uses only `SendActivity`, with no agent, model credentials, or external
service. The required `client_factory` is a `NoReturn` sentinel that raises if
anything tries to create an agent client.

The parent yields `child.run(context.get_input())`. This schedules the
`dafx-Child` sub-orchestration, not an in-process `Workflow.run()` call. The
yielded task returns decoded workflow outputs. The parent returns

```json
{"child_outputs": ["Child workflow completed."]}
```

`child.run(input_, instance_id="child-instance-id")` can supply a child instance
ID. Otherwise the native Durable scheduler chooses it. Each invocation has its
own workflow state.

## Registration and exposure

Neither `discover_agents` nor `discover_workflows` is enabled. The binding loads
only the matching `Child.workflow.yaml` or `Child.workflow.yml` in the app root
or its `workflows/` directory. Its loaded workflow must be named `Child`.
For a differently named file, pass an app-root-relative `workflow_file`, such as
`workflow_file="workflows/review.workflow.yaml"`, while keeping the YAML name
equal to the requested workflow name. The selected entry must stay inside the
app root.

The child is private by default. Indexing registers `parent`, `start_parent`,
`dafx-Child`, `dafx-Child-_workflow_entry`, `dafx-Child-send_result`, and the SDK's
`BuiltIn__HttpActivity` and `BuiltIn__HttpPollOrchestrator`. There are no generated
child HTTP routes or agent functions. The inner DAFX host is created at
`app.get_functions()`, after declarations have been collected.

To also publish the child's run, status, and response endpoints, explicitly add
`expose_http_endpoint=True` to `@app.durable_workflow(...)`. That opts in to
`POST /api/workflow/Child/run`, `GET /api/workflow/Child/status/{instanceId}`, and
`POST /api/workflow/Child/respond/{instanceId}/{requestId}`. It is not needed to
call the child from the parent. Constructor exposure options govern bulk
discovery only and do not turn a private binding into a public endpoint.

Input forwarding strips DAFX's reserved checkpoint/envelope markers, matching
the public workflow HTTP boundary. The generic parent does not aggregate child
human-input requests into a parent management endpoint. A child that requests
human input needs exposed child management routes or application management
using its instance ID. This sample's child does not request human input.

## Run locally

Follow the [YAML sample setup](../durable-yaml-workflow/README.md#install-and-run)
for Python 3.13, local packages, and the `[durable,workflows]` extras. Core Tools
also requires an SDK 2-compatible Functions host/extension and a configured
Durable backend. This sample does not provision or verify them.

Set `FUNCTIONS_WORKER_RUNTIME=python` and `AzureWebJobsStorage`, then run
`func start` from this directory. With the default `/api` prefix, start the parent

```bash
curl -X POST http://localhost:7071/api/parent/orchestrations
```

The handwritten starter ignores the body and returns a check-status response.
Follow its status URL to read the parent output. Hosted requests need a function
key. The starter can be omitted when another Durable caller starts `parent`.
This example adds no request schema or business policy validation.

MAF owns YAML parsing and native factory lifecycle. A configured
`workflow_factory` can be supplied without enabling discovery. Native YAML file
references are trusted deployment content, not sandboxed by the entry-file
containment check. See the [package documentation](../../README.md#yaml-workflows)
for factory configuration and lifecycle boundaries.
