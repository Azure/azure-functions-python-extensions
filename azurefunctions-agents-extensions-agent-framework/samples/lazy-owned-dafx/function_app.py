"""Local-model example of optional DAFX ownership. No model credentials needed."""

from collections.abc import Mapping, Sequence
from typing import Any

import azure.functions as func
from agent_framework import Agent, BaseChatClient, ChatResponse, Message

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp


class LocalChatClient(BaseChatClient):
    """Return a deterministic response so the prototype needs no model service."""

    def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ):
        if stream:
            raise TypeError("streaming is not supported by this local client")

        async def respond():
            turns = sum(message.role == "user" for message in messages)
            return ChatResponse(messages=[Message(
                role="assistant", contents=[f"User turn {turns}: {messages[-1].text}"]
            )])

        return respond()


app = AgentFunctionApp(client_factory=LocalChatClient)


@app.route(route="hello", methods=["GET"])
def hello(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Normal HTTP function on the outer app.")


# This is the only opt-in point for DAFX. Register before function indexing.
# The caller owns this agent and any clients/tools it uses.
app.add_durable_agent(Agent(client=LocalChatClient(), name="Orders"))


@app.orchestration_trigger(context_name="context")
def orders(context):
    agent = app.get_agent(context, "Orders")
    session = agent.create_session()
    first = yield agent.run("Assess the order.", session=session)
    second = yield agent.run("Make a fulfillment plan.", session=session)
    return {"assessment": first.text, "plan": second.text}


@app.route(route="orders", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_orders(req: func.HttpRequest, client) -> func.HttpResponse:
    instance_id = await client.start_new("orders", client_input={})
    return client.create_check_status_response(req, instance_id)
