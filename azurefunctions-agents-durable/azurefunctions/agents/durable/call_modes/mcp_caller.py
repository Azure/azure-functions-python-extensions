"""MCP (Model Context Protocol) agent caller implementation."""

import json
import logging
import subprocess
import asyncio
from typing import Any, Dict, List, Optional, Union
import azure.functions as func
import azure.durable_functions as df

from .base import BaseAgentCaller
from ..types import AgentCallResponse

logger = logging.getLogger(__name__)

# MCP imports (will be optional if not available)
try:
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client
    from mcp import ClientSession
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP client library not available. MCP functionality will be simulated.")


class MCPAgentCaller(BaseAgentCaller):
    """Agent caller for MCP (Model Context Protocol) endpoints with full SSE and stdio support."""
    
    def register_activities(self) -> None:
        """Register MCP activity function."""
        activity_name = self.get_activity_name("default")
        
        @self.app.activity_trigger(arg_name="req", activity_name=activity_name)
        async def mcp_activity(req: str) -> str:
            """Activity function for MCP agent calls."""
            try:
                request_data = json.loads(req)
                response = await self._execute_mcp_call(
                    request_data["method"],
                    request_data.get("args", {}),
                    request_data.get("kwargs", {})
                )
                return json.dumps(response.__dict__)
            except Exception as e:
                logger.exception(f"Error in MCP activity for {self.config.name}")
                error_response = AgentCallResponse.error_response(str(e))
                return json.dumps(error_response.__dict__)
    
    def get_activity_name(self, method: str) -> str:
        """Get the activity name for MCP calls."""
        return f"call_mcp_agent_{self.config.name}"
    
    def call_agent(self, context: df.DurableOrchestrationContext, method: str, 
                        args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Call the MCP agent using the orchestrator context.
        
        Args:
            context: Durable orchestrator context (required)
            method: The method to call on the agent
            args: Positional arguments for the method
            kwargs: Keyword arguments for the method
            
        Returns:
            Result from the MCP agent call
        """
        args = args or {}
        kwargs = kwargs or {}
        
        if context is None:
            raise ValueError("context parameter is required for durable orchestrator framework")
            
        # Use activity pattern with orchestrator context
        activity_name = self.get_activity_name("default")
        request_data = {
            "method": method,
            "args": args,
            "kwargs": kwargs
        }
        return context.call_activity(activity_name, json.dumps(request_data))
    
    async def call_mcp_tool(self, context: df.DurableOrchestrationContext, tool_name: str, 
                           arguments: Dict[str, Any] = None) -> Any:
        """Convenience method to call an MCP tool.
        
        Args:
            context: Durable orchestrator context (required)
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
        """
        return await self.call_agent("call_tool", {"name": tool_name, "arguments": arguments or {}}, context=context)
    
    async def list_mcp_tools(self, context: df.DurableOrchestrationContext) -> Any:
        """List available tools on the MCP server.
        
        Args:
            context: Durable orchestrator context (required)
        """
        return await self.call_agent("list_tools", context=context)
    
    async def list_mcp_resources(self, context: df.DurableOrchestrationContext) -> AgentCallResponse:
        """List available resources on the MCP server."""
        return await self.call_agent(context, "list_resources")
    
    async def read_mcp_resource(self, context: df.DurableOrchestrationContext, uri: str) -> AgentCallResponse:
        """Read a resource from the MCP server."""
        return await self.call_agent(context, "read_resource", {"uri": uri})
    
    async def _execute_mcp_call(self, method: str, args: Dict[str, Any], kwargs: Dict[str, Any]) -> AgentCallResponse:
        """Execute MCP call based on the configured client type."""
        try:
            extra_config = self.config.extra_config or {}
            client_type = extra_config.get("client_type", "sse")
            
            if client_type == "sse":
                return await self._call_via_sse(method, args, kwargs)
            elif client_type == "stdio":
                return await self._call_via_stdio(method, args, kwargs)
            else:
                return AgentCallResponse.error_response(f"Unsupported MCP client type: {client_type}")
        
        except Exception as e:
            logger.exception(f"Error executing MCP call for {self.config.name}")
            return AgentCallResponse.error_response(str(e))
    
    async def _call_via_sse(self, method: str, args: Dict[str, Any], kwargs: Dict[str, Any]) -> AgentCallResponse:
        """Execute MCP call via Server-Sent Events with full MCP protocol implementation."""
        if not MCP_AVAILABLE:
            return AgentCallResponse.error_response("MCP client library not available")
            
        try:
            # Extract SSE configuration
            extra_config = self.config.extra_config or {}
            sse_url = extra_config.get("sse_url") or self.config.endpoint
            
            if not sse_url:
                return AgentCallResponse.error_response("Missing SSE URL for SSE MCP client")
            
            # Extract tool name and arguments from method call
            tool_name = method
            arguments = args.copy()
            arguments.update(kwargs)
            
            # Connect to MCP server via SSE
            async with sse_client(url=sse_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.debug(f"Connected to MCP server at {sse_url}")
                    
                    # Handle different method types
                    if method == "list_tools":
                        response = await session.list_tools()
                        tools = [{"name": tool.name, "description": tool.description} for tool in response.tools]
                        return AgentCallResponse.success_response(tools)
                    
                    elif method == "call_tool":
                        tool_name = arguments.get("name") or arguments.get("tool_name")
                        tool_arguments = arguments.get("arguments", {})
                        
                        if not tool_name:
                            return AgentCallResponse.error_response("Missing tool name for call_tool")
                        
                        response = await session.call_tool(name=tool_name, arguments=tool_arguments)
                        
                        # Convert MCP response to serializable format
                        serializable_result = self._serialize_mcp_response(response)
                        return AgentCallResponse.success_response(serializable_result)
                    
                    elif method == "list_resources":
                        response = await session.list_resources()
                        resources = [{"uri": res.uri, "name": res.name} for res in response.resources]
                        return AgentCallResponse.success_response(resources)
                    
                    elif method == "read_resource":
                        uri = arguments.get("uri")
                        if not uri:
                            return AgentCallResponse.error_response("Missing URI for read_resource")
                        
                        response = await session.read_resource(uri=uri)
                        return AgentCallResponse.success_response({"uri": uri, "content": response.contents})
                    
                    else:
                        # Generic tool call
                        response = await session.call_tool(name=method, arguments=arguments)
                        serializable_result = self._serialize_mcp_response(response)
                        return AgentCallResponse.success_response(serializable_result)
            
        except Exception as e:
            logger.exception(f"MCP SSE call failed for {self.config.name}")
            return AgentCallResponse.error_response(f"MCP SSE call failed: {str(e)}")
    
    async def _call_via_stdio(self, method: str, args: Dict[str, Any], kwargs: Dict[str, Any]) -> AgentCallResponse:
        """Execute MCP call via stdio with full MCP protocol implementation."""
        if not MCP_AVAILABLE:
            return AgentCallResponse.error_response("MCP client library not available")
            
        try:
            # Extract stdio configuration
            extra_config = self.config.extra_config or {}
            command = extra_config.get("command")
            command_args = extra_config.get("args", [])
            
            if not command:
                return AgentCallResponse.error_response("Missing 'command' in extra_config for stdio MCP client")
            
            # Extract tool name and arguments from method call
            tool_name = method
            arguments = args.copy()
            arguments.update(kwargs)
            
            # Connect to MCP server via stdio
            async with stdio_client(command=command, args=command_args) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.debug(f"Connected to MCP server via stdio: {command}")
                    
                    # Handle different method types
                    if method == "list_tools":
                        response = await session.list_tools()
                        tools = [{"name": tool.name, "description": tool.description} for tool in response.tools]
                        return AgentCallResponse.success_response(tools)
                    
                    elif method == "call_tool":
                        tool_name = arguments.get("name") or arguments.get("tool_name")
                        tool_arguments = arguments.get("arguments", {})
                        
                        if not tool_name:
                            return AgentCallResponse.error_response("Missing tool name for call_tool")
                        
                        response = await session.call_tool(name=tool_name, arguments=tool_arguments)
                        
                        # Convert MCP response to serializable format
                        serializable_result = self._serialize_mcp_response(response)
                        return AgentCallResponse.success_response(serializable_result)
                    
                    elif method == "list_resources":
                        response = await session.list_resources()
                        resources = [{"uri": res.uri, "name": res.name} for res in response.resources]
                        return AgentCallResponse.success_response(resources)
                    
                    elif method == "read_resource":
                        uri = arguments.get("uri")
                        if not uri:
                            return AgentCallResponse.error_response("Missing URI for read_resource")
                        
                        response = await session.read_resource(uri=uri)
                        return AgentCallResponse.success_response({"uri": uri, "content": response.contents})
                    
                    else:
                        # Generic tool call
                        response = await session.call_tool(name=method, arguments=arguments)
                        serializable_result = self._serialize_mcp_response(response)
                        return AgentCallResponse.success_response(serializable_result)
            
        except Exception as e:
            logger.exception(f"MCP stdio call failed for {self.config.name}")
            return AgentCallResponse.error_response(f"MCP stdio call failed: {str(e)}")
    
    def _serialize_mcp_response(self, response) -> Dict[str, Any]:
        """Convert MCP response to JSON serializable format."""
        try:
            serializable_result = {}
            
            if hasattr(response, 'content') and response.content:
                # Extract text from content array
                text_content = []
                for content_item in response.content:
                    if hasattr(content_item, 'text'):
                        text_content.append(content_item.text)
                    elif hasattr(content_item, 'type') and content_item.type == 'text':
                        text_content.append(str(content_item))
                    else:
                        text_content.append(str(content_item))
                
                serializable_result = {
                    "content": text_content,
                    "isError": getattr(response, 'isError', False)
                }
            else:
                # Fallback to string representation
                serializable_result = {"content": [str(response)], "isError": False}
            
            return serializable_result
            
        except Exception as e:
            logger.warning(f"Failed to serialize MCP response: {e}")
            return {"content": [str(response)], "isError": False}


class MCPClientHelper:
    """Convenience helper class that provides the exact prototype pattern from mcp_client.py."""
    
    def __init__(self, app: df.DFApp, sse_url: str = "http://localhost:7071/runtime/webhooks/mcp/sse"):
        """Initialize MCP client helper with prototype pattern compatibility.
        
        Parameters
        ----------
        app : df.DFApp
            Durable Functions application instance
        sse_url : str
            MCP SSE endpoint URL
        """
        self.app = app
        self.sse_url = sse_url
        # Register the necessary activity functions using the same pattern as mcp_client.py
        self._register_mcp_activities()
    
    def _register_mcp_activities(self):
        """Register necessary MCP activity functions using the exact prototype pattern."""
        
        @self.app.activity_trigger(input_name="mcp_request")
        async def mcp_call_service(mcp_request: Dict[str, Any]) -> Dict[str, Any]:
            """Generic MCP service call activity function."""
            tool_name = mcp_request.get("tool_name")
            arguments = mcp_request.get("arguments", {})
            sse_url = mcp_request.get("sse_url", self.sse_url)

            response = None
            try:
                if not MCP_AVAILABLE:
                    return {"status": "error", "error": "MCP client library not available"}
                
                # MCP client initialization
                async with sse_client(url=sse_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        logger.debug("Connected successfully to MCP server!")
                        
                        # Tool call
                        response = await session.call_tool(
                            name=tool_name,
                            arguments=arguments
                        )
       
            except Exception as e:
                logger.error("Unexpected exception in mcp_call_service: %s", str(e))
                logger.exception("Full stack trace:")
                return {"status": "error", "error": str(e)}

            # Convert MCP response to JSON serializable format
            if response is None:
                return {"status": "error", "error": "Failed to call MCP service"}
            
            # Extract text content from CallToolResult (same as mcp_client.py)
            serializable_result = {}
            if hasattr(response, 'content') and response.content:
                # Extract text from content array
                text_content = []
                for content_item in response.content:
                    if hasattr(content_item, 'text'):
                        text_content.append(content_item.text)
                    elif hasattr(content_item, 'type') and content_item.type == 'text':
                        text_content.append(str(content_item))
                
                serializable_result = {
                    "content": text_content,
                    "isError": getattr(response, 'isError', False)
                }
            else:
                # Fallback to string representation
                serializable_result = {"content": [str(response)], "isError": False}

            result = {
                "status": "success", 
                "data": f"Called {tool_name} with arguments {arguments}", 
                "result": serializable_result
            }
            return result
    
    def call_service(self, context: df.DurableOrchestrationContext, 
                    tool_name: str, arguments: Optional[Dict] = None, 
                    sse_url: Optional[str] = None) -> Any:
        """Helper method to call MCP service from orchestrator (exact prototype pattern).
        
        Parameters
        ----------
        context : df.DurableOrchestrationContext
            Orchestration context
        tool_name : str
            MCP tool name to call
        arguments : Optional[Dict]
            Tool arguments
        sse_url : Optional[str]
            Custom SSE URL (optional)
            
        Returns
        -------
        Any
            Service call result
        """
        mcp_request = {
            "tool_name": tool_name,
            "arguments": arguments or {},
            "sse_url": sse_url or self.sse_url
        }
        
        # Call pre-registered activity (use yield in orchestrator)
        result = yield context.call_activity("mcp_call_service", mcp_request)
        return result