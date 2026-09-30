import json
import os

import azure.functions as func
from copilot import CopilotClient
from copilot.session import CopilotSession, PermissionHandler
from copilot.session_events import AssistantMessageData
from azurefunctions.agents.extensions.copilot_sdk import AgentFunctionApp


def create_copilot_client() -> CopilotClient:
    return CopilotClient(
        mode="empty",
        github_token=os.environ["COPILOT_GITHUB_TOKEN"],
        use_logged_in_user=False,
        log_level="none",
        telemetry=None,
    )


app = AgentFunctionApp(
    client_factory=create_copilot_client,
    model=os.environ["COPILOT_MODEL"],
    on_permission_request=PermissionHandler.approve_all,
)


async def _run(session: CopilotSession, prompt: str) -> str:
    response = await session.send_and_wait(prompt)
    if response is None or not isinstance(response.data, AssistantMessageData):
        raise RuntimeError("Copilot did not return a final assistant message")
    return response.data.content


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

    assessment = await _run(
        order_agent,
        json.dumps(
            {
                "order_id": req.route_params["orderId"],
                "order": order,
                "task": "assess fulfillment readiness",
            }
        ),
    )
    return func.HttpResponse(
        body=json.dumps({"assessment": assessment}),
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
    await _run(order_agent, message.get_body().decode("utf-8"))