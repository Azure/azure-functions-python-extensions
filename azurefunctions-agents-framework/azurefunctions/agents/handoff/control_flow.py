# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Control Flow Manager for multi-agent handoff system."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

from .types import (
    HandoffContext,
    HandoffResult, 
    HandoffRequest,
    AgentResponse,
    ControlReturn,
    HandoffMode,
    HandoffStrategy
)

if TYPE_CHECKING:
    from ..agents import Agent


class ControlFlowManager:
    """
    Manages control flow and state for multi-agent handoffs.
    
    This class tracks:
    - Active conversations and their control flow
    - Agent call stacks and execution paths
    - Context passing between agents
    - Loop detection and prevention
    """
    
    def __init__(self, max_conversation_lifetime: int = 3600):
        """
        Initialize the control flow manager.
        
        Args:
            max_conversation_lifetime: Maximum lifetime of a conversation in seconds
        """
        self.logger = logging.getLogger("ControlFlowManager")
        self.max_conversation_lifetime = max_conversation_lifetime
        
        # Active conversations and their contexts
        self._conversations: Dict[str, HandoffContext] = {}
        
        # Agent registry (will be set by framework)
        self._agents: Dict[str, 'Agent'] = {}
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        
    def register_agents(self, agents: Dict[str, 'Agent']):
        """Register agents with the control flow manager."""
        self._agents = agents
        self.logger.info(f"Registered {len(agents)} agents: {list(agents.keys())}")
        
    def start_cleanup_task(self):
        """Start the periodic cleanup task for expired conversations."""
        if self._cleanup_task is None:
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._periodic_cleanup())
            except RuntimeError:
                self.logger.info("No event loop running, cleanup will be manual")
    
    def stop_cleanup_task(self):
        """Stop the periodic cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired conversations."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                self._cleanup_expired_conversations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")
    
    def _cleanup_expired_conversations(self):
        """Remove expired conversations from memory."""
        now = datetime.now()
        expired_conversations = []
        
        for conv_id, context in self._conversations.items():
            age = (now - context.created_at).total_seconds()
            if age > self.max_conversation_lifetime:
                expired_conversations.append(conv_id)
        
        for conv_id in expired_conversations:
            del self._conversations[conv_id]
            self.logger.debug(f"Cleaned up expired conversation: {conv_id}")
    
    def create_conversation(self, initial_request: Dict[str, Any]) -> str:
        """
        Create a new conversation and return its ID.
        
        Args:
            initial_request: The initial request that started the conversation
            
        Returns:
            Conversation ID
        """
        conversation_id = str(uuid.uuid4())
        
        context = HandoffContext(
            conversation_id=conversation_id,
            call_stack=[],
            shared_context={},
            handoff_count=0,
            original_request=initial_request,
            metadata={"created_by": "control_flow_manager"}
        )
        
        self._conversations[conversation_id] = context
        self.logger.debug(f"Created conversation: {conversation_id}")
        
        return conversation_id
    
    def get_conversation_context(self, conversation_id: str) -> Optional[HandoffContext]:
        """Get the context for a conversation."""
        return self._conversations.get(conversation_id)
    
    def update_conversation_context(self, conversation_id: str, updates: Dict[str, Any]):
        """Update the shared context for a conversation."""
        if conversation_id in self._conversations:
            self._conversations[conversation_id].shared_context.update(updates)
    
    def push_agent_to_stack(self, conversation_id: str, agent_name: str) -> bool:
        """
        Push an agent onto the call stack.
        
        Args:
            conversation_id: ID of the conversation
            agent_name: Name of the agent to push
            
        Returns:
            True if successful, False if conversation not found or max hops exceeded
        """
        if conversation_id not in self._conversations:
            return False
            
        context = self._conversations[conversation_id]
        
        # Check for infinite loops
        if context.handoff_count >= context.max_hops:
            self.logger.warning(
                f"Max hops ({context.max_hops}) exceeded in conversation {conversation_id}"
            )
            return False
        
        context.call_stack.append(agent_name)
        context.handoff_count += 1
        
        self.logger.debug(
            f"Pushed {agent_name} to stack. Current stack: {context.call_stack}"
        )
        
        return True
    
    def pop_agent_from_stack(self, conversation_id: str) -> Optional[str]:
        """
        Pop an agent from the call stack.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Name of the previous agent in the stack, or None if stack is empty
        """
        if conversation_id not in self._conversations:
            return None
            
        context = self._conversations[conversation_id]
        
        if context.call_stack:
            current_agent = context.call_stack.pop()
            previous_agent = context.call_stack[-1] if context.call_stack else None
            
            self.logger.debug(
                f"Popped {current_agent} from stack. Previous: {previous_agent}"
            )
            
            return previous_agent
        
        return None
    
    def get_current_agent(self, conversation_id: str) -> Optional[str]:
        """Get the current agent at the top of the call stack."""
        if conversation_id not in self._conversations:
            return None
            
        context = self._conversations[conversation_id]
        return context.call_stack[-1] if context.call_stack else None
    
    def get_execution_path(self, conversation_id: str) -> List[str]:
        """Get the full execution path for a conversation."""
        if conversation_id not in self._conversations:
            return []
            
        return self._conversations[conversation_id].call_stack.copy()
    
    def has_agent_in_stack(self, conversation_id: str, agent_name: str) -> bool:
        """Check if an agent is already in the call stack (loop detection)."""
        if conversation_id not in self._conversations:
            return False
            
        return agent_name in self._conversations[conversation_id].call_stack
    
    def validate_handoff(self, conversation_id: str, handoff_request: HandoffRequest) -> tuple[bool, Optional[str]]:
        """
        Validate a handoff request.
        
        Args:
            conversation_id: ID of the conversation
            handoff_request: The handoff request to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if conversation exists
        if conversation_id not in self._conversations:
            return False, f"Conversation {conversation_id} not found"
        
        context = self._conversations[conversation_id]
        
        # Check max hops
        if context.handoff_count >= context.max_hops:
            return False, f"Maximum handoff limit ({context.max_hops}) exceeded"
        
        # Check if target agent exists
        if handoff_request.target_agent not in self._agents:
            return False, f"Target agent '{handoff_request.target_agent}' not found"
        
        # Check for direct loops (agent trying to call itself)
        current_agent = self.get_current_agent(conversation_id)
        if current_agent == handoff_request.target_agent:
            return False, f"Agent cannot hand off to itself: {current_agent}"
        
        # Check for cycles in swarm mode
        if self.has_agent_in_stack(conversation_id, handoff_request.target_agent):
            # Allow in coordinator mode, warn in swarm mode
            current_mode = getattr(self._agents[current_agent], 'handoff_config', None)
            if current_mode and current_mode.mode == HandoffMode.SWARM:
                self.logger.warning(
                    f"Potential cycle detected: {handoff_request.target_agent} "
                    f"already in stack {context.call_stack}"
                )
        
        return True, None
    
    def cleanup_conversation(self, conversation_id: str):
        """Clean up a completed conversation."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            self.logger.debug(f"Cleaned up conversation: {conversation_id}")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about active conversations."""
        return {
            "active_conversations": len(self._conversations),
            "total_handoffs": sum(ctx.handoff_count for ctx in self._conversations.values()),
            "longest_stack": max(
                (len(ctx.call_stack) for ctx in self._conversations.values()), 
                default=0
            ),
            "registered_agents": len(self._agents)
        }
