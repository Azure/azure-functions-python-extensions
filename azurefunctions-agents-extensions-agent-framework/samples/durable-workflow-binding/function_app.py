"""Call a private YAML child workflow from a generator orchestrator."""

from typing import NoReturn

import azure.durable_functions as df
import azure.functions as func
from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp


def no_agent_client() -> NoReturn:
    raise AssertionError("This workflow must not create an agent client.")


app = AgentFunctionApp(client_factory=no_agent_client)


@app.orchestration_trigger(context_name="context")
@app.durable_workflow(arg_name="child", workflow_name="Child")
def parent(context: df.DurableOrchestrationContext, child):
    outputs = yield child.run(context.get_input())
    return {"child_outputs": outputs}


@app.route(route="parent/orchestrations", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_parent(
    req: func.HttpRequest, client: df.DurableFunctionsClient
) -> func.HttpResponse:
    # The child emits fixed text, so this starter does not consume a request body.
    instance_id = await client.start_new("parent", client_input={})
    return client.create_check_status_response(req, instance_id)
