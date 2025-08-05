"""Decorators for the Durable Functions Agents framework."""

import functools
import logging
from typing import Callable, Any, Optional
from azure.durable_functions import DurableOrchestrationContext

from .framework import DFAgentFramework, AgentCaller


logger = logging.getLogger(__name__)


def orchestrator(framework: DFAgentFramework, name: Optional[str] = None, agent_caller: Optional[AgentCaller] = None):
    """Decorator that provides activity trigger-less notation for orchestrators.
    
    This decorator automatically injects an AgentCaller instance into the orchestrator
    function, allowing direct agent calls without explicit activity triggers.
    It also registers the orchestrator function with the framework's app.
    
    Args:
        framework: The DFAgentFramework instance
        name: Optional name for the orchestrator function
        agent_caller: Optional pre-configured AgentCaller instance
    
    Example:
        @orchestrator(framework, name="my_orchestrator")
        async def my_orchestrator(context: DurableOrchestrationContext, agents: AgentCaller):
            # Call agents directly using yield (not await) in orchestrator context
            result = yield agents.call_agent(context, "my_agent", "my_method", {"arg1": "value1"})
            yield result  # Use yield to return final result in async generator
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(context: DurableOrchestrationContext, *args, **kwargs) -> Any:
            # Create or use provided agent caller
            caller = agent_caller if agent_caller is not None else framework.create_agent_caller()
            
            # Call the original function with the agent caller
            try:
                # For orchestrator functions, we need to handle both regular functions
                # and async generators (when yield is used)
                result = func(context, caller, *args, **kwargs)
                
                # If it's an async generator, we need to handle it properly
                if hasattr(result, '__aiter__'):
                    # It's an async generator - iterate through it
                    final_result = None
                    async for value in result:
                        final_result = value
                    return final_result
                else:
                    # It's a regular async function
                    return await result
                    
            except Exception as e:
                logger.exception(f"Error in orchestrator {func.__name__}")
                raise
        
        # Register the orchestrator with the framework's app
        orchestrator_name = name or func.__name__
        framework.app.orchestration_trigger(arg_name="context", orchestrator_name=orchestrator_name)(wrapper)
        
        return wrapper
    return decorator


def activity_with_agent_support(framework: DFAgentFramework):
    """Decorator for activity functions that need to call agents.
    
    This decorator provides agent calling capabilities to activity functions,
    which is useful for activities that need to make agent calls.
    
    Args:
        framework: The DFAgentFramework instance
    
    Example:
        @activity_with_agent_support(framework)
        async def my_activity(context, agents: AgentCaller, data):
            result = await agents.call("my_agent", "process", data)
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Create agent caller
            caller = framework.create_agent_caller()
            
            # Inject the agent caller as the second parameter
            # First parameter is typically the activity context
            if args:
                new_args = (args[0], caller) + args[1:]
            else:
                new_args = (caller,)
            
            try:
                return await func(*new_args, **kwargs)
            except Exception as e:
                logger.exception(f"Error in activity {func.__name__}")
                raise
        
        return wrapper
    return decorator


def register_orchestrator_with_agents(app, framework: DFAgentFramework, orchestrator_name: Optional[str] = None):
    """Decorator that combines orchestrator registration with agent support.
    
    This is a convenience decorator that both registers the function as a Durable Functions
    orchestrator and provides agent calling capabilities.
    
    Args:
        app: The FunctionApp instance
        framework: The DFAgentFramework instance
        orchestrator_name: Optional custom name for the orchestrator
    
    Example:
        @register_orchestrator_with_agents(app, framework)
        async def my_orchestrator(context: DurableOrchestrationContext, agents: AgentCaller):
            # Use yield for orchestrator calls, not await
            result = yield agents.call_agent(context, "my_agent", "my_method")
            yield result  # Use yield to return final result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(context: DurableOrchestrationContext, *args, **kwargs) -> Any:
            # Create agent caller
            caller = framework.create_agent_caller()
            
            try:
                # Call the original function with the agent caller
                result = func(context, caller, *args, **kwargs)
                
                # Handle async generators (when yield is used in orchestrators)
                if hasattr(result, '__aiter__'):
                    final_result = None
                    async for value in result:
                        final_result = value
                    return final_result
                else:
                    return await result
                    
            except Exception as e:
                logger.exception(f"Error in orchestrator {func.__name__}")
                raise
        
        # Register with Durable Functions
        name = orchestrator_name or func.__name__
        return app.orchestration_trigger(arg_name="context", orchestrator_name=name)(wrapper)
    
    return decorator