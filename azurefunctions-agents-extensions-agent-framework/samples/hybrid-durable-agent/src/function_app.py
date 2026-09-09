import json
import os
from datetime import timedelta
from typing import Any

import azure.durable_functions as df
import azure.functions as func
from agent_framework import Agent
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
    instance_id = await client.start_new(
        "order_orchestrator",
        client_input=req.get_json(),
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
def order_orchestrator(context: Any):
    prepared_order = yield context.call_activity(
        "prepare_order_activity",
        context.get_input(),
    )

    # context.call_agent equivalent to the following commented-out code:
    #
    # @app.activity_trigger(input_name="payload")
    # @app.markdown_agent(arg_name="agent", agent_name="order-fulfillment")
    # async def process_order(payload: dict, agent: Agent[Any]) -> dict:
    #     response = await agent.run(json.dumps(payload))
    #     return {"text": response.text}

    assessment = yield context.call_agent(
        "order-fulfillment",
        {
            "order": prepared_order,
            "task": "assess fulfillment risk using the trusted calculated fields",
        },
    )
    plan = yield context.call_agent(
        "order-fulfillment",
        {
            "order": prepared_order,
            "risk_assessment": assessment,
            "task": "create a fulfillment plan with prioritized human-review actions",
        },
        retry_options=df.RetryPolicy(
            first_retry_interval=timedelta(seconds=5),
            max_number_of_attempts=3,
        ),
    )
    return {
        "order_id": prepared_order["order_id"],
        "risk_assessment": assessment,
        "fulfillment_plan": plan,
    }