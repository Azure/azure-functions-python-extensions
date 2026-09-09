"""Inject a durable markdown agent into a two-turn generator orchestrator."""

import azure.durable_functions as df
import azure.functions as func
from agent_framework_durabletask import DurableAgentTask, DurableAIAgent
from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from local_chat_client import LocalChatClient

# The binding below opts in only the selected agent, without durable=True.
app = AgentFunctionApp(client_factory=LocalChatClient)


@app.orchestration_trigger(context_name="context")
@app.durable_markdown_agent(
    arg_name="agent", agent_name="orders", context_name="context"
)
def orders(
    context: df.DurableOrchestrationContext,
    agent: DurableAIAgent[DurableAgentTask],
):
    session = agent.create_session()
    first = yield agent.run("Assess the order.", session=session)
    second = yield agent.run("Make a fulfillment plan.", session=session)
    return {"assessment": first.text, "plan": second.text}


@app.route(route="orders/orchestrations", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_orders(
    req: func.HttpRequest, client: df.DurableFunctionsClient
) -> func.HttpResponse:
    # Fixed prompts keep this example focused on durable session continuity.
    instance_id = await client.start_new("orders", client_input={})
    return client.create_check_status_response(req, instance_id)
