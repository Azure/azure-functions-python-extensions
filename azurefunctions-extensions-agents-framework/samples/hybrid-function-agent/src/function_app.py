import json
import os

import azure.functions as func
from agent_framework import Agent
from azurefunctions.extensions.agents_framework import AiApp
from order_processing import prepare_order_for_agent
from pydantic import ValidationError


def create_chat_client():
    from agent_framework.foundry import FoundryChatClient
    from azure.identity.aio import DefaultAzureCredential

    return FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["FOUNDRY_MODEL"],
        credential=DefaultAzureCredential(),
    )


app = AiApp(client_factory=create_chat_client)


@app.route(route="orders/{orderId}", methods=["POST"])
@app.markdown_agent(arg_name="order_agent", agent_name="order-fulfillment")
async def process_order(
    req: func.HttpRequest,
    order_agent: Agent,
) -> func.HttpResponse:
    order_id = req.route_params["orderId"]
    order = req.get_json()
    try:
        prepared_order = prepare_order_for_agent(order, order_id=order_id)
    except (ValidationError, ValueError):
        return func.HttpResponse(
            body=json.dumps({"error": "Order failed validation."}),
            status_code=400,
            media_type="application/json",
        )

    response = await order_agent.run(
        json.dumps(
            {
                "order": prepared_order,
                "task": "assess fulfillment readiness using the trusted calculated fields",
            }
        )
    )
    return func.HttpResponse(
        body=json.dumps({"order_id": order_id, "assessment": response.text}),
        media_type="application/json",
    )


# @app.queue_trigger(
#     arg_name="message",
#     queue_name="orders",
#     connection="AzureWebJobsStorage",
# )
# @app.markdown_agent(arg_name="order_agent", agent_name="order-fulfillment")
# async def process_order_event(
#     message: func.QueueMessage,
#     order_agent: Agent,
# ) -> None:
#     event = json.loads(message.get_body().decode("utf-8"))
#     prepared_order = prepare_order_for_agent(event)
#     await order_agent.run(
#         json.dumps(
#             {
#                 "order": prepared_order,
#                 "task": "triage fulfillment exceptions using the trusted calculated fields",
#             }
#         )
#     )