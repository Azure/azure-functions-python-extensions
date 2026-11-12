import json

import azure.functions as func
from copilot.session import CopilotSession
from copilot.session_events import AssistantMessageData
from azurefunctions.agents.extensions.copilot_sdk import AgentFunctionApp

app = AgentFunctionApp()


@app.route(route="orders/{orderId}", methods=["POST"])
@app.markdown_agent(arg_name="order_agent", agent_name="order-fulfillment")
async def process_order(
    req: func.HttpRequest,
    order_agent: CopilotSession,
) -> func.HttpResponse:
    try:
        order = req.get_json()
    except ValueError:
        return func.HttpResponse(
            body=json.dumps({"error": "Order failed validation."}),
            status_code=400,
            mimetype="application/json",
        )

    response = await order_agent.send_and_wait(
        json.dumps(
            {
                "order_id": req.route_params["orderId"],
                "order": order,
                "task": "assess fulfillment readiness",
            }
        ),
    )
    if response is None or not isinstance(response.data, AssistantMessageData):
        raise RuntimeError("Copilot did not return a final assistant message")
    return func.HttpResponse(
        body=json.dumps({"assessment": response.data.content}),
        mimetype="application/json",
    )


@app.queue_trigger(
    arg_name="message",
    queue_name="orders",
    connection="AzureWebJobsStorage",
)
@app.markdown_agent(arg_name="order_agent", agent_name="order-fulfillment")
async def process_order_event(
    message: func.QueueMessage,
    order_agent: CopilotSession,
) -> None:
    response = await order_agent.send_and_wait(
        message.get_body().decode("utf-8")
    )
    if response is None or not isinstance(response.data, AssistantMessageData):
        raise RuntimeError("Copilot did not return a final assistant message")