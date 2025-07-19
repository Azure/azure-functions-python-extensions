"""
Azure Functions Agent Framework - Advanced Streaming Examples

This module demonstrates advanced streaming capabilities using the unified chat endpoint:
- Streaming via Accept header or stream parameter
- Multi-agent streaming workflows
- Custom Server-Sent Events
- Progress tracking and metadata
- Error handling in streams
- Frontend integration patterns

Streaming is activated by:
- Adding "Accept: text/event-stream" header, OR
- Adding "stream": true in request body, OR
- Adding "X-Stream: true" header

Requires: enable_streaming=True and azurefunctions-extensions-http-fastapi
"""

import azure.functions as func
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
from azurefunctions.agents import AgentFunctionApp, AgentExecutor

# Create function app with streaming enabled
app = AgentFunctionApp(enable_streaming=True)

# Define multiple agents for demonstration
@app.agent(name="analyzer")
def analyzer_agent() -> Dict[str, Any]:
    """Agent that analyzes input and provides detailed insights."""
    return {
        "name": "analyzer",
        "instructions": "You are a thorough analyst. Break down user input into key components and provide detailed insights.",
        "llm_client": None,  # Configure with your preferred LLM
    }

@app.agent(name="reporter")
def reporter_agent() -> Dict[str, Any]:
    """Agent that creates summary reports."""
    return {
        "name": "reporter",
        "instructions": "You are a concise reporter. Create clear, structured summaries from provided information.",
        "llm_client": None,  # Configure with your preferred LLM
    }

@app.agent(name="creative_writer")
def creative_writer_agent() -> Dict[str, Any]:
    """Agent that writes creative content."""
    return {
        "name": "creative_writer",
        "instructions": "You are a creative writer. Transform ideas into engaging, imaginative content.",
        "llm_client": None,  # Configure with your preferred LLM
    }

# All streaming now happens through the standard chat endpoints!
# No need for separate /stream endpoints

# The chat endpoints automatically detect streaming requests via:
# 1. Accept: text/event-stream header
# 2. "stream": true in request body
# 3. X-Stream: true header

# Enhanced collaborative workflow example
@app.route(route="workflow/analyze-and-report", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
async def collaborative_workflow(req: func.HttpRequest) -> func.HttpResponse:
    """Example of multi-agent workflow using streaming chat endpoints."""
    try:
        from azurefunctions.extensions.http.fastapi import StreamingResponse
    except ImportError:
        return func.HttpResponse(
            "Streaming requires azurefunctions-extensions-http-fastapi",
            status_code=501
        )

import azure.functions as func
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
from azurefunctions.agents import AgentFunctionApp, AgentExecutor
from azurefunctions.agents.streaming import AgentStreamingResponse, create_agent_stream

# Create the function app with streaming enabled
app = AgentFunctionApp(enable_streaming=True)

# Define multiple agents for demonstration
@app.agent(name="analyzer")
def analyzer_agent() -> Dict[str, Any]:
    """Agent that analyzes input and provides detailed insights."""
    return {
        "name": "analyzer",
        "instructions": "You are a thorough analyst. Break down user input into key components and provide detailed insights.",
        "llm_client": None,  # Configure with your preferred LLM
    }

@app.agent(name="reporter")
def reporter_agent() -> Dict[str, Any]:
    """Agent that creates summary reports."""
    return {
        "name": "reporter",
        "instructions": "You are a concise reporter. Create clear, structured summaries from provided information.",
        "llm_client": None,  # Configure with your preferred LLM
    }

@app.agent(name="creative_writer")
def creative_writer_agent() -> Dict[str, Any]:
    """Agent that writes creative content."""
    return {
        "name": "creative_writer",
        "instructions": "You are a creative writer. Transform ideas into engaging, imaginative content.",
        "llm_client": None,  # Configure with your preferred LLM
    }

# Standard enhanced streaming endpoint
@app.route(route="stream/enhanced/{agent_name}", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
async def enhanced_streaming_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Enhanced streaming with custom events and metadata."""
    try:
        from azurefunctions.extensions.http.fastapi import StreamingResponse
    except ImportError:
        return func.HttpResponse(
            "Streaming requires azurefunctions-extensions-http-fastapi",
            status_code=501
        )

    agent_name = req.route_params.get("agent_name")
    if not agent_name or agent_name not in app.agents:
        return func.HttpResponse("Agent not found", status_code=404)

    try:
        req_json = req.get_json()
        user_input = req_json.get("message", "")

        if not user_input:
            return func.HttpResponse("Message is required", status_code=400)

    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)

    # Create agent executor
    agent_executor = AgentExecutor(app.agents)

    # Enhanced streaming with custom metadata
    async def enhanced_stream():
        try:
            start_data = {"agent": agent_name, "timestamp": datetime.utcnow().isoformat()}
            yield f"event: stream_start\ndata: {json.dumps(start_data)}\n\n"

            chunk_count = 0
            collected_response = []
            total_chunks = None  # We'll estimate this if possible

            async for chunk in agent_executor.execute_async(agent_name=agent_name, user_input=user_input):
                chunk_count += 1
                collected_response.append(chunk.get("content", ""))

                # Send the chunk data
                chunk_data = {
                    "id": chunk_count,
                    "content": chunk.get("content", ""),
                    "metadata": chunk.get("metadata", {}),
                    "agent": agent_name
                }
                yield f"event: chunk\ndata: {json.dumps(chunk_data)}\n\n"

                # Send progress updates every few chunks
                if chunk_count % 3 == 0:
                    progress_data = {
                        "progress": chunk_count,
                        "total_estimate": total_chunks if total_chunks else "unknown",
                        "current_content": chunk.get("content", ""),
                        "agent": agent_name
                    }
                    yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"

            # Send final summary
            summary = {
                "type": "summary",
                "total_chunks": chunk_count,
                "total_characters": len("".join(collected_response)),
                "agent": agent_name,
                "completed_at": datetime.utcnow().isoformat()
            }
            yield f"event: stream_complete\ndata: {json.dumps(summary)}\n\n"

        except Exception as e:
            error_data = {
                "error": str(e),
                "error_type": type(e).__name__,
                "agent": agent_name
            }
            yield f"event: stream_error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(enhanced_stream(), media_type="text/event-stream")

# Multi-agent collaborative streaming
@app.route(route="stream/collaborative", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
async def collaborative_streaming_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Stream responses from multiple agents in a workflow."""
    try:
        from azurefunctions.extensions.http.fastapi import StreamingResponse
    except ImportError:
        return func.HttpResponse(
            "Streaming requires azurefunctions-extensions-http-fastapi",
            status_code=501
        )

    try:
        req_json = req.get_json()
        user_input = req_json.get("message", "")
        workflow = req_json.get("workflow", ["analyzer", "reporter"])  # Default workflow

        if not user_input:
            return func.HttpResponse("Message is required", status_code=400)

    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)

    # Validate agents exist
    for agent_name in workflow:
        if agent_name not in app.agents:
            return func.HttpResponse(f"Agent '{agent_name}' not found", status_code=404)

    agent_executor = AgentExecutor(app.agents)

    # Multi-agent streaming workflow
    async def collaborative_stream():
        try:
            workflow_data = {
                "workflow": workflow,
                "timestamp": datetime.utcnow().isoformat(),
                "total_agents": len(workflow)
            }
            yield f"event: workflow_start\ndata: {json.dumps(workflow_data)}\n\n"

            previous_output = user_input

            for i, agent_name in enumerate(workflow):
                agent_start_data = {
                    "agent": agent_name,
                    "step": i + 1,
                    "total_steps": len(workflow),
                    "input_preview": previous_output[:100] + "..." if len(previous_output) > 100 else previous_output
                }
                yield f"event: agent_start\ndata: {json.dumps(agent_start_data)}\n\n"

                agent_response = []
                async for chunk in agent_executor.execute_async(agent_name=agent_name, user_input=previous_output):
                    agent_response.append(chunk.get("content", ""))

                    chunk_data = {
                        "agent": agent_name,
                        "step": i + 1,
                        "content": chunk.get("content", ""),
                        "metadata": chunk.get("metadata", {})
                    }
                    yield f"event: agent_chunk\ndata: {json.dumps(chunk_data)}\n\n"

                # Prepare input for next agent
                previous_output = " ".join(agent_response)

                agent_complete_data = {
                    "agent": agent_name,
                    "step": i + 1,
                    "output_length": len(previous_output),
                    "ready_for_next": i < len(workflow) - 1
                }
                yield f"event: agent_complete\ndata: {json.dumps(agent_complete_data)}\n\n"

            # Final workflow summary
            final_summary = {
                "workflow_complete": True,
                "total_steps": len(workflow),
                "final_output_length": len(previous_output),
                "completed_at": datetime.utcnow().isoformat()
            }
            yield f"event: workflow_complete\ndata: {json.dumps(final_summary)}\n\n"

        except Exception as e:
            error_data = {
                "error": str(e),
                "error_type": type(e).__name__,
                "workflow_step": i if 'i' in locals() else "unknown"
            }
            yield f"event: workflow_error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(collaborative_stream(), media_type="text/event-stream")

# Health endpoint with streaming information
@app.route(route="streaming/health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
async def streaming_health(req: func.HttpRequest) -> func.HttpResponse:
    """Check streaming capabilities and agent health."""
    try:
        from azurefunctions.extensions.http.fastapi import StreamingResponse
        streaming_available = True
    except ImportError:
        streaming_available = False

    health_data = {
        "streaming_available": streaming_available,
        "agents": {
            name: {
                "name": agent.name,
                "has_llm": bool(agent.llm_client),
                "supports_streaming": bool(
                    agent.llm_client and
                    hasattr(agent.llm_client, 'stream_completion')
                ) if agent.llm_client else False,
                "instructions_length": len(agent.instructions) if agent.instructions else 0,
            }
            for name, agent in app.agents.items()
        },
        "endpoints": {
            "standard_streaming": "/api/agents/{agent_name}/stream",
            "enhanced_streaming": "/api/stream/enhanced/{agent_name}",
            "collaborative_streaming": "/api/stream/collaborative",
            "health": "/api/streaming/health"
        },
        "requirements": {
            "for_streaming": "azurefunctions-extensions-http-fastapi",
            "status": "installed" if streaming_available else "missing"
        }
    }

    return func.HttpResponse(
        json.dumps(health_data),
        mimetype="application/json"
    )

# Debugging endpoint for streaming issues
@app.route(route="streaming/debug", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
async def debug_streaming(req: func.HttpRequest) -> func.HttpResponse:
    """Debug streaming functionality with detailed logging."""
    try:
        from azurefunctions.extensions.http.fastapi import StreamingResponse
    except ImportError:
        return func.HttpResponse(
            "Streaming requires azurefunctions-extensions-http-fastapi",
            status_code=501
        )

    try:
        req_json = req.get_json()
        agent_name = req_json.get("agent", "analyzer")
        message = req_json.get("message", "Test message for debugging")

    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)

    if agent_name not in app.agents:
        return func.HttpResponse(f"Agent '{agent_name}' not found", status_code=404)

    agent_executor = AgentExecutor(app.agents)

    async def debug_stream():
        try:
            debug_start = {
                "debug": True,
                "agent": agent_name,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "available_agents": list(app.agents.keys())
            }
            yield f"event: debug_start\ndata: {json.dumps(debug_start)}\n\n"

            chunk_count = 0

            async for chunk in agent_executor.execute_async(agent_name=agent_name, user_input=message):
                chunk_count += 1

                debug_chunk = {
                    "chunk_number": chunk_count,
                    "chunk_type": type(chunk).__name__,
                    "chunk_keys": list(chunk.keys()) if isinstance(chunk, dict) else "not_dict",
                    "content_preview": str(chunk.get("content", chunk))[:100] if chunk else "empty",
                    "full_chunk": chunk
                }
                yield f"event: debug_chunk\ndata: {json.dumps(debug_chunk)}\n\n"

            debug_complete = {
                "total_chunks": chunk_count,
                "agent": agent_name,
                "completed_at": datetime.utcnow().isoformat()
            }
            yield f"event: debug_complete\ndata: {json.dumps(debug_complete)}\n\n"

        except Exception as e:
            import traceback
            error_details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "agent": agent_name
            }
            yield f"event: debug_error\ndata: {json.dumps(error_details)}\n\n"

    return StreamingResponse(debug_stream(), media_type="text/event-stream")

# Example frontend integration
@app.route(route="streaming/frontend-example", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
async def frontend_example(req: func.HttpRequest) -> func.HttpResponse:
    """Serve frontend integration example."""
    frontend_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Azure Functions Agent Streaming Example</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { margin: 20px 0; }
        textarea { width: 100%; height: 100px; }
        button { padding: 10px 20px; margin: 5px; }
        .response { border: 1px solid #ccc; padding: 10px; margin: 10px 0; min-height: 100px; }
        .status { font-weight: bold; color: #007acc; }
        .error { color: red; }
        .progress { color: #008000; }
    </style>
</head>
<body>
    <h1>Azure Functions Agent Streaming</h1>

    <div class="container">
        <label for="message">Message:</label>
        <textarea id="message" placeholder="Enter your message here...">Analyze the current trends in AI technology</textarea>
    </div>

    <div class="container">
        <label for="agent">Agent:</label>
        <select id="agent">
            <option value="analyzer">Analyzer</option>
            <option value="reporter">Reporter</option>
            <option value="creative_writer">Creative Writer</option>
        </select>
    </div>

    <div class="container">
        <button onclick="startStream()">Start Enhanced Stream</button>
        <button onclick="startCollaborativeStream()">Start Collaborative Stream</button>
        <button onclick="clearResponse()">Clear</button>
    </div>

    <div class="container">
        <div id="status" class="status">Ready</div>
        <div id="progress" class="progress"></div>
    </div>

    <div id="response" class="response"></div>

    <script>
    async function startStream() {
        const agent = document.getElementById('agent').value;
        const message = document.getElementById('message').value;

        if (!message.trim()) {
            alert('Please enter a message');
            return;
        }

        clearResponse();
        updateStatus('Starting stream...');

        try {
            const response = await fetch(`/api/stream/enhanced/${agent}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const events = chunk.split('\\n\\n').filter(Boolean);

                for (const event of events) {
                    const lines = event.split('\\n');
                    let eventType = 'message';
                    let data = '';

                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7);
                        } else if (line.startsWith('data: ')) {
                            data = line.slice(6);
                        }
                    }

                    if (data) {
                        try {
                            const parsed = JSON.parse(data);
                            handleStreamEvent(eventType, parsed);
                        } catch (e) {
                            console.error('Failed to parse event data:', data);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Streaming error:', error);
            showError('Streaming error: ' + error.message);
        }
    }

    async function startCollaborativeStream() {
        const message = document.getElementById('message').value;

        if (!message.trim()) {
            alert('Please enter a message');
            return;
        }

        clearResponse();
        updateStatus('Starting collaborative stream...');

        try {
            const response = await fetch('/api/stream/collaborative', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    workflow: ['analyzer', 'reporter']
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Similar processing as above...
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const events = chunk.split('\\n\\n').filter(Boolean);

                for (const event of events) {
                    const lines = event.split('\\n');
                    let eventType = 'message';
                    let data = '';

                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7);
                        } else if (line.startsWith('data: ')) {
                            data = line.slice(6);
                        }
                    }

                    if (data) {
                        try {
                            const parsed = JSON.parse(data);
                            handleStreamEvent(eventType, parsed);
                        } catch (e) {
                            console.error('Failed to parse event data:', data);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Collaborative streaming error:', error);
            showError('Streaming error: ' + error.message);
        }
    }

    function handleStreamEvent(eventType, data) {
        switch (eventType) {
            case 'stream_start':
                updateStatus(`Stream started for agent: ${data.agent}`);
                break;

            case 'chunk':
                appendToResponse(data.content);
                break;

            case 'progress':
                updateProgress(`Progress: ${data.progress} chunks`);
                break;

            case 'stream_complete':
                updateStatus(`Completed: ${data.total_chunks} chunks, ${data.total_characters} characters`);
                break;

            case 'workflow_start':
                updateStatus(`Workflow started with ${data.total_agents} agents`);
                break;

            case 'agent_start':
                updateStatus(`Starting agent: ${data.agent} (step ${data.step}/${data.total_steps})`);
                break;

            case 'agent_chunk':
                appendToResponse(`[${data.agent}] ${data.content}`);
                break;

            case 'workflow_complete':
                updateStatus('Workflow completed successfully');
                break;

            case 'stream_error':
            case 'workflow_error':
                showError(`Error: ${data.error}`);
                break;

            default:
                console.log('Unknown event type:', eventType, data);
        }
    }

    function updateStatus(message) {
        document.getElementById('status').textContent = message;
    }

    function updateProgress(message) {
        document.getElementById('progress').textContent = message;
    }

    function appendToResponse(content) {
        const responseEl = document.getElementById('response');
        responseEl.textContent += content;
    }

    function showError(error) {
        document.getElementById('status').innerHTML = `<span class="error">${error}</span>`;
    }

    function clearResponse() {
        document.getElementById('response').textContent = '';
        document.getElementById('progress').textContent = '';
        updateStatus('Ready');
    }
    </script>
</body>
</html>
    """

    return func.HttpResponse(frontend_html, mimetype="text/html")

if __name__ == "__main__":
    # For local development
    print("Advanced streaming example loaded")
    print("Available endpoints:")
    print("- POST /api/stream/enhanced/{agent_name}")
    print("- POST /api/stream/collaborative")
    print("- GET /api/streaming/health")
    print("- GET /api/streaming/frontend-example")
    print("- POST /api/streaming/debug")
