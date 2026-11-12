import json

import azure.durable_functions as df
import azure.functions as func
from azurefunctions.agents.extensions.copilot_sdk import (
    AgentFunctionApp,
    DurableAgentContext,
)

app = AgentFunctionApp()


@app.route(route="orders/orchestrations", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_order_orchestration(
    req: func.HttpRequest,
    client: df.DurableFunctionsClient,
) -> func.HttpResponse:
    try:
        order = req.get_json()
    except ValueError:
        return func.HttpResponse(
            body=json.dumps({"error": "Order failed validation."}),
            status_code=400,
            mimetype="application/json",
        )

    instance_id = await client.start_new(
        "order_orchestrator",
        client_input=order,
    )
    management = client.create_http_management_payload(req, instance_id)
    return func.HttpResponse(
        body=json.dumps(management),
        status_code=202,
        mimetype="application/json",
        headers={"Location": management["statusQueryGetUri"]},
    )


@app.orchestration_trigger(context_name="context")
def order_orchestrator(context: DurableAgentContext):
    assessment = yield context.call_agent(
        "order-fulfillment",
        {
            "order": context.get_input(),
            "task": "assess fulfillment readiness",
        },
    )
    return {"assessment": assessment}