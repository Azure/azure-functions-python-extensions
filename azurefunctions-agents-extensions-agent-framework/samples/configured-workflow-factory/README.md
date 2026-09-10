# Configured YAML workflow factory

[function_app.py](function_app.py) configures MAF's public `WorkflowFactory`,
registers the local `format_order` function with `register_tool()`, and passes
that same object to `AgentFunctionApp(workflow_factory=...)`. The configuration
provides `ORDER_PREFIX` for `=Env.ORDER_PREFIX`. With
`restrict_env_to_configuration=True`, MAF does not consult process environment
variables for these workflow expressions.

[ConfiguredTools.workflow.yaml](workflows/ConfiguredTools.workflow.yaml) calls
`InvokeFunctionTool`, stores its result in `Local.result`, then emits it with
`SendActivity`. The function only formats text. No Markdown definition, agent
client, model credentials, or external service is needed. `client_factory` is
still a required app argument, so `no_agent_client()` raises if it is called.
There are no handwritten HTTP handlers or orchestrators.

## Run

Follow the [YAML sample setup](../durable-yaml-workflow/README.md#install-and-run)
for the local packages, `[durable,workflows]` extras, and host/backend settings.
Use Python 3.13 to reproduce the verified PowerFx expression execution. The
extension does not reject Python 3.14, but support follows the installed MAF
dependencies and execution on 3.14 has not been verified.

Start Core Tools from this sample directory rather than the Markdown sample.
The copied [host.json](host.json) does not provision or verify a compatible host
or Durable backend.

With the default `/api` prefix, send `{"order":"42"}` to
`POST /api/workflow/ConfiguredTools/run`. Query the returned `statusQueryGetUri`
until completion. The expected `output` is `["Local order 42."]`. Hosted requests
need a function key. The sample expects this input shape and adds no request
schema validation.

DAFX also generates `GET /api/workflow/ConfiguredTools/status/{instanceId}` and
`POST /api/workflow/ConfiguredTools/respond/{instanceId}/{requestId}`. This
workflow does not request human input.

## Factory and lifecycle

The extension calls `create_workflow_from_yaml_path()` on the supplied factory
unchanged, without merging discovered Markdown adapters into its agent registry.
This sample has no Markdown files or standalone agent endpoints. Adding Markdown
files would still publish their standalone endpoints because `durable=True`, but
would not add them to this factory's registry.

MAF owns parsing and building, including warnings, errors, and native agent/tool
configuration. The extension does not impose a separate action allowlist.
Discovered entry files must stay within the app root, but nested file references
use native MAF resolution and are not sandboxed. Deploy only trusted files.

If you add inline or custom agents, their construction and resource lifecycle
follow MAF or the supplied factory and may create clients during app
initialization/indexing. They do not automatically get the Markdown adapter's
fresh per-execution lifecycle. See the [verification scope](../durable-yaml-workflow/VALIDATION.md)
for the distinction between local replay checks and host/backend validation.
