import json
import os

import azure.durable_functions as df
import azure.functions as func
from agent_framework_durabletask import DurableAgentTask, DurableAIAgent
from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from order_processing import prepare_order_for_agent


def create_chat_client():
    from agent_framework.foundry import FoundryChatClient
    from azure.identity.aio import DefaultAzureCredential

    return FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["FOUNDRY_MODEL"],
        credential=DefaultAzureCredential(),
    )


app = AgentFunctionApp(client_factory=create_chat_client)


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
        headers={
            "Location": management["statusQueryGetUri"],
            "Retry-After": "10",
        },
    )


@app.activity_trigger(input_name="order")
def prepare_order_activity(order: dict) -> dict[str, object]:
    return prepare_order_for_agent(order)


@app.orchestration_trigger(context_name="context")
@app.durable_markdown_agent(
    arg_name="agent", agent_name="order-fulfillment", context_name="context"
)
def order_orchestrator(
    context: df.DurableOrchestrationContext,
    agent: DurableAIAgent[DurableAgentTask],
):
    prepared_order = yield context.call_activity(
        "prepare_order_activity",
        context.get_input(),
    )

    session = agent.create_session()
    assessment = yield agent.run(
        json.dumps({
            "order": prepared_order,
            "task": "assess fulfillment risk using the trusted calculated fields",
        }),
        session=session,
    )
    plan = yield agent.run(
        json.dumps({
            "order": prepared_order,
            "risk_assessment": assessment.text,
            "task": "create a fulfillment plan with prioritized human-review actions",
        }),
        session=session,
    )
    return {
        "order_id": prepared_order["order_id"],
        "risk_assessment": assessment.text,
        "fulfillment_plan": plan.text,
    }
