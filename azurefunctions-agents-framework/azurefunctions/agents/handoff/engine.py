# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Handoff execution engine for multi-agent control flow."""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .control_flow import ControlFlowManager
from .types import AgentResponse, ControlReturn, HandoffRequest, HandoffResult

if TYPE_CHECKING:
    from ..agents import Agent


class HandoffEngine:
    """
    Execution engine for multi-agent handoffs.

    This class handles:
    - Executing handoff requests
    - Routing between different handoff strategies
    - Managing responses and control flow
    - AI-powered agent selection
    """

    def __init__(self, control_flow_manager: ControlFlowManager):
        """Initialize the handoff engine."""
        self.logger = logging.getLogger("HandoffEngine")
        self.control_flow = control_flow_manager
        self._agents: Dict[str, "Agent"] = {}

    def register_agents(self, agents: Dict[str, "Agent"]):
        """Register agents with the handoff engine."""
        self._agents = agents
        self.control_flow.register_agents(agents)
        self.logger.info(f"Registered {len(agents)} agents for handoff")

    async def execute_handoff(
        self, conversation_id: str, handoff_request: HandoffRequest, current_agent: str
    ) -> HandoffResult:
        """
        Execute a handoff request.

        Args:
            conversation_id: ID of the conversation
            handoff_request: The handoff request to execute
            current_agent: Name of the agent making the handoff

        Returns:
            HandoffResult with the outcome
        """
        self.logger.info(
            f"Executing handoff from {current_agent} to {handoff_request.target_agent} "
            f"in conversation {conversation_id}"
        )

        # Validate the handoff
        is_valid, error_msg = self.control_flow.validate_handoff(
            conversation_id, handoff_request
        )
        if not is_valid:
            return HandoffResult(
                success=False,
                error=error_msg,
                context=self.control_flow.get_conversation_context(conversation_id),
            )

        # Get target agent
        target_agent = self._agents.get(handoff_request.target_agent)
        if not target_agent:
            return HandoffResult(
                success=False,
                error=f"Target agent '{handoff_request.target_agent}' not found",
                context=self.control_flow.get_conversation_context(conversation_id),
            )

        try:
            # Update call stack
            self.control_flow.push_agent_to_stack(
                conversation_id, handoff_request.target_agent
            )

            # Prepare input data
            input_data = self._prepare_handoff_input(
                conversation_id, handoff_request, current_agent
            )

            # Execute the target agent
            response = await self._execute_target_agent(
                target_agent, input_data, conversation_id
            )

            # Handle the response based on control return strategy
            result = await self._handle_agent_response(
                conversation_id, response, handoff_request, current_agent
            )

            return result

        except Exception as e:
            self.logger.error(f"Error executing handoff: {e}")
            return HandoffResult(
                success=False,
                error=f"Handoff execution failed: {str(e)}",
                context=self.control_flow.get_conversation_context(conversation_id),
            )

    def _prepare_handoff_input(
        self, conversation_id: str, handoff_request: HandoffRequest, current_agent: str
    ) -> Dict[str, Any]:
        """Prepare input data for the target agent."""
        context = self.control_flow.get_conversation_context(conversation_id)

        # Base input data
        input_data = {
            "message": handoff_request.input_data,
            "handoff_context": {
                "from_agent": current_agent,
                "conversation_id": conversation_id,
                "reason": handoff_request.reason,
                "expected_return": handoff_request.expected_return.value,
                "call_stack": context.call_stack if context else [],
            },
        }

        # Add shared context if available
        if context and context.shared_context:
            # Pass specific context keys if requested
            if handoff_request.context_keys:
                filtered_context = {
                    key: context.shared_context.get(key)
                    for key in handoff_request.context_keys
                    if key in context.shared_context
                }
                input_data["shared_context"] = filtered_context
            else:
                input_data["shared_context"] = context.shared_context

        # Apply input transformation if provided
        if handoff_request.transform_response:
            try:
                input_data = handoff_request.transform_response(input_data)
            except Exception as e:
                self.logger.warning(f"Input transformation failed: {e}")

        return input_data

    async def _execute_target_agent(
        self, target_agent: "Agent", input_data: Dict[str, Any], conversation_id: str
    ) -> AgentResponse:
        """Execute the target agent with the prepared input."""
        try:
            # Call the agent's process_request method
            response = await target_agent.process_request(input_data)

            # Wrap in AgentResponse if not already
            if isinstance(response, AgentResponse):
                return response

            # Convert dict response to AgentResponse
            return AgentResponse(
                agent_name=target_agent.name,
                content=response,
                control_return=ControlReturn.BUBBLE_UP,  # Default behavior
            )

        except Exception as e:
            self.logger.error(f"Error executing target agent {target_agent.name}: {e}")
            return AgentResponse(
                agent_name=target_agent.name,
                content={"error": f"Agent execution failed: {str(e)}"},
                control_return=ControlReturn.BUBBLE_UP,
            )

    async def _handle_agent_response(
        self,
        conversation_id: str,
        response: AgentResponse,
        original_request: HandoffRequest,
        calling_agent: str,
    ) -> HandoffResult:
        """Handle the agent response and determine control flow."""
        context = self.control_flow.get_conversation_context(conversation_id)

        # Update shared context with any updates from the agent
        if response.context_updates:
            self.control_flow.update_conversation_context(
                conversation_id, response.context_updates
            )

        # Handle control return based on the response
        if response.control_return == ControlReturn.BUBBLE_UP:
            # Pop the current agent and return to user
            self.control_flow.pop_agent_from_stack(conversation_id)
            return HandoffResult(
                success=True,
                target_agent=response.agent_name,
                response=response.content,
                control_return=ControlReturn.BUBBLE_UP,
                context=context,
                execution_path=self.control_flow.get_execution_path(conversation_id),
            )

        elif response.control_return == ControlReturn.RETURN_TO_CALLER:
            # Pop current agent and return control to the calling agent
            self.control_flow.pop_agent_from_stack(conversation_id)
            previous_agent = self.control_flow.get_current_agent(conversation_id)

            if previous_agent:
                # Continue with the previous agent
                return HandoffResult(
                    success=True,
                    target_agent=previous_agent,
                    response=response.content,
                    control_return=ControlReturn.RETURN_TO_CALLER,
                    context=context,
                    execution_path=self.control_flow.get_execution_path(
                        conversation_id
                    ),
                )
            else:
                # No previous agent, bubble up to user
                return HandoffResult(
                    success=True,
                    target_agent=response.agent_name,
                    response=response.content,
                    control_return=ControlReturn.BUBBLE_UP,
                    context=context,
                    execution_path=self.control_flow.get_execution_path(
                        conversation_id
                    ),
                )

        elif response.control_return == ControlReturn.CONTINUE_CHAIN:
            # Check if the agent wants to hand off to another agent
            if response.handoff_request:
                # Recursive handoff
                return await self.execute_handoff(
                    conversation_id, response.handoff_request, response.agent_name
                )
            else:
                # No further handoff specified, bubble up
                return HandoffResult(
                    success=True,
                    target_agent=response.agent_name,
                    response=response.content,
                    control_return=ControlReturn.BUBBLE_UP,
                    context=context,
                    execution_path=self.control_flow.get_execution_path(
                        conversation_id
                    ),
                )

        elif response.control_return == ControlReturn.END_CONVERSATION:
            # End the conversation
            self.control_flow.cleanup_conversation(conversation_id)
            return HandoffResult(
                success=True,
                target_agent=response.agent_name,
                response=response.content,
                control_return=ControlReturn.END_CONVERSATION,
                context=None,
                execution_path=self.control_flow.get_execution_path(conversation_id),
            )

        # Default: bubble up
        return HandoffResult(
            success=True,
            target_agent=response.agent_name,
            response=response.content,
            control_return=ControlReturn.BUBBLE_UP,
            context=context,
            execution_path=self.control_flow.get_execution_path(conversation_id),
        )

    async def route_to_best_agent(
        self,
        conversation_id: str,
        request_data: Dict[str, Any],
        available_agents: List[str],
        routing_instructions: Optional[str] = None,
    ) -> Optional[str]:
        """
        Use AI to route a request to the best available agent.

        Args:
            conversation_id: ID of the conversation
            request_data: The request data to route
            available_agents: List of available agent names
            routing_instructions: Instructions for the routing decision

        Returns:
            Name of the selected agent, or None if routing fails
        """
        try:
            # Get agent descriptions for routing
            agent_descriptions = {}
            for agent_name in available_agents:
                agent = self._agents.get(agent_name)
                if agent:
                    agent_descriptions[agent_name] = {
                        "name": agent.name,
                        "description": agent.description,
                        "tools": [
                            tool["name"]
                            for tool in agent.tool_registry.list_all_tools()
                        ],
                    }

            # Create routing prompt
            routing_prompt = self._create_routing_prompt(
                request_data, agent_descriptions, routing_instructions
            )

            # Use the first available agent with LLM capabilities for routing
            routing_agent = None
            for agent_name in available_agents:
                agent = self._agents.get(agent_name)
                if agent and agent.llm_client:
                    routing_agent = agent
                    break

            if not routing_agent:
                self.logger.warning(
                    "No agent with LLM capabilities available for routing"
                )
                return None

            # Get routing decision
            response = await routing_agent.llm_client.chat(
                messages=[{"role": "user", "content": routing_prompt}], max_tokens=100
            )

            # Parse the response to extract agent name
            selected_agent = self._parse_routing_response(response, available_agents)

            if selected_agent in available_agents:
                self.logger.info(f"AI routing selected agent: {selected_agent}")
                return selected_agent
            else:
                self.logger.warning(
                    f"AI routing returned invalid agent: {selected_agent}"
                )
                return None

        except Exception as e:
            self.logger.error(f"AI routing failed: {e}")
            return None

    def _create_routing_prompt(
        self,
        request_data: Dict[str, Any],
        agent_descriptions: Dict[str, Dict],
        routing_instructions: Optional[str],
    ) -> str:
        """Create a prompt for AI-powered agent routing."""
        base_prompt = f"""You are a routing assistant. Given the following request and available agents, select the SINGLE best agent to handle this request.

Request: {json.dumps(request_data, indent=2)}

Available Agents:
{json.dumps(agent_descriptions, indent=2)}

{routing_instructions or "Choose the agent whose description and tools best match the request."}

Respond with ONLY the agent name, nothing else."""

        return base_prompt

    def _parse_routing_response(
        self, response: str, available_agents: List[str]
    ) -> Optional[str]:
        """Parse the routing response to extract the selected agent name."""
        response = response.strip().lower()

        # Try exact match first
        for agent_name in available_agents:
            if agent_name.lower() == response:
                return agent_name

        # Try partial match
        for agent_name in available_agents:
            if agent_name.lower() in response or response in agent_name.lower():
                return agent_name

        return None
