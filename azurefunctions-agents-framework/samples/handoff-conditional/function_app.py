"""
Customer Service Hub - Conditional Handoff Pattern Example

This sample demonstrates the CONDITIONAL handoff pattern where agents use
AI-powered routing to intelligently direct conversations to the most appropriate
specialist based on request content and context.

Architecture:
- Customer Service Agent: Main entry point with intelligent routing
- Technical Support Agent: Handles technical issues and troubleshooting
- Billing Agent: Manages billing, payments, and account issues
- Sales Agent: Handles product inquiries and sales processes
- Escalation Agent: Manages complex issues requiring human intervention

Flow:
1. Customer submits request to main customer service agent
2. Agent analyzes request using AI and routing rules
3. Agent conditionally hands off to appropriate specialist
4. Specialist processes request and may escalate if needed
5. Response returned with full routing path for transparency
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import azure.functions as func

from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.handoff import (
    ControlReturn,
    HandoffConfig,
    HandoffMode,
    HandoffTarget,
)
from azurefunctions.agents.types import LLMConfig, LLMProvider

# Mock customer data and systems
CUSTOMER_DATABASE = {
    "customer_123": {
        "name": "John Doe",
        "account_type": "premium",
        "subscription": "pro",
        "last_payment": "2024-01-15",
        "issues_history": ["billing", "technical"],
        "satisfaction_score": 4.2,
    },
    "customer_456": {
        "name": "Jane Smith",
        "account_type": "basic",
        "subscription": "starter",
        "last_payment": "2024-01-20",
        "issues_history": ["sales"],
        "satisfaction_score": 4.8,
    },
}

TICKET_DATABASE = {}


# Utility functions for routing logic
def analyze_request_type(message: str) -> str:
    """Analyze the type of request based on keywords."""
    message_lower = message.lower()

    # Technical keywords
    technical_keywords = [
        "error",
        "bug",
        "not working",
        "broken",
        "crash",
        "technical",
        "login",
        "password",
        "connection",
        "slow",
        "performance",
        "integration",
        "api",
        "setup",
        "configuration",
    ]

    # Billing keywords
    billing_keywords = [
        "bill",
        "billing",
        "payment",
        "charge",
        "refund",
        "invoice",
        "subscription",
        "upgrade",
        "downgrade",
        "cancel",
        "price",
        "cost",
        "fee",
        "account",
        "renewal",
    ]

    # Sales keywords
    sales_keywords = [
        "buy",
        "purchase",
        "plan",
        "feature",
        "demo",
        "trial",
        "pricing",
        "quote",
        "sales",
        "product",
        "service",
        "package",
        "enterprise",
        "custom",
    ]

    # Escalation keywords
    escalation_keywords = [
        "manager",
        "supervisor",
        "escalate",
        "complaint",
        "angry",
        "frustrated",
        "legal",
        "lawyer",
        "sue",
        "urgent",
        "critical",
    ]

    # Count keyword matches
    technical_score = sum(
        1 for keyword in technical_keywords if keyword in message_lower
    )
    billing_score = sum(1 for keyword in billing_keywords if keyword in message_lower)
    sales_score = sum(1 for keyword in sales_keywords if keyword in message_lower)
    escalation_score = sum(
        1 for keyword in escalation_keywords if keyword in message_lower
    )

    # Return highest scoring category
    scores = {
        "technical": technical_score,
        "billing": billing_score,
        "sales": sales_score,
        "escalation": escalation_score,
    }

    max_category = max(scores, key=scores.get)
    if scores[max_category] > 0:
        return max_category

    return "general"


def get_customer_context(customer_id: str) -> Dict[str, Any]:
    """Get customer context for routing decisions."""
    return CUSTOMER_DATABASE.get(customer_id, {})


def should_escalate(message: str, customer_context: Dict[str, Any]) -> bool:
    """Determine if issue should be escalated based on content and customer."""
    escalation_triggers = [
        "manager",
        "supervisor",
        "complaint",
        "angry",
        "frustrated",
        "legal",
        "lawyer",
        "sue",
        "urgent",
        "critical",
        "disappointed",
    ]

    has_escalation_keywords = any(
        trigger in message.lower() for trigger in escalation_triggers
    )
    is_premium_customer = customer_context.get("account_type") == "premium"
    has_history = len(customer_context.get("issues_history", [])) > 2
    low_satisfaction = customer_context.get("satisfaction_score", 5.0) < 3.0

    return (
        has_escalation_keywords
        or (is_premium_customer and has_history)
        or low_satisfaction
    )


# Mock service functions
async def lookup_customer(customer_id: str) -> Dict[str, Any]:
    """Look up customer information."""
    customer = CUSTOMER_DATABASE.get(customer_id, {})
    logging.info(f"Customer lookup for {customer_id}: {customer}")
    return customer


async def create_ticket(issue_type: str, customer_id: str, description: str) -> str:
    """Create a support ticket."""
    ticket_id = f"TICKET-{len(TICKET_DATABASE) + 1:04d}"
    ticket = {
        "id": ticket_id,
        "type": issue_type,
        "customer_id": customer_id,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "status": "open",
    }
    TICKET_DATABASE[ticket_id] = ticket
    logging.info(f"Created ticket {ticket_id} for customer {customer_id}")
    return ticket_id


async def search_knowledge_base(query: str) -> List[Dict[str, Any]]:
    """Search knowledge base for relevant articles."""
    # Mock knowledge base
    articles = [
        {
            "id": "KB001",
            "title": "Password Reset Instructions",
            "category": "technical",
            "content": "To reset your password, click on 'Forgot Password' and follow the instructions.",
        },
        {
            "id": "KB002",
            "title": "Billing Cycle Information",
            "category": "billing",
            "content": "Your billing cycle begins on the day you first subscribed to our service.",
        },
        {
            "id": "KB003",
            "title": "Feature Comparison Guide",
            "category": "sales",
            "content": "Compare our plans to find the right features for your needs.",
        },
    ]

    # Simple keyword matching
    query_lower = query.lower()
    relevant_articles = [
        article
        for article in articles
        if any(
            word in article["content"].lower() or word in article["title"].lower()
            for word in query_lower.split()
        )
    ]

    return relevant_articles[:3]  # Return top 3


# Configure LLM (using OpenAI by default)
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key="your-openai-api-key",  # Replace with actual API key
)


# Define routing condition functions
def needs_technical_support(request_data: Dict[str, Any]) -> bool:
    """Check if request needs technical support."""
    message = request_data.get("message", "")
    return analyze_request_type(message) == "technical"


def needs_billing_support(request_data: Dict[str, Any]) -> bool:
    """Check if request needs billing support."""
    message = request_data.get("message", "")
    return analyze_request_type(message) == "billing"


def needs_sales_support(request_data: Dict[str, Any]) -> bool:
    """Check if request needs sales support."""
    message = request_data.get("message", "")
    return analyze_request_type(message) == "sales"


def needs_escalation(request_data: Dict[str, Any]) -> bool:
    """Check if request needs escalation."""
    message = request_data.get("message", "")
    customer_id = request_data.get("customer_id", "unknown")
    customer_context = get_customer_context(customer_id)
    return should_escalate(message, customer_context)


# Create Customer Service Agent (Main Router)
customer_service_agent = Agent(
    name="customer_service",
    instructions="""
    You are the main Customer Service Agent responsible for intelligently routing customer requests.

    Your role:
    1. Greet customers warmly and understand their needs
    2. Analyze requests to determine the best specialist to help
    3. Route appropriately using conditional handoffs
    4. Provide immediate help when possible
    5. Ensure customers feel heard and valued

    Available specialists:
    - Technical Support: For technical issues, bugs, login problems
    - Billing Support: For billing, payments, subscription questions
    - Sales Support: For product inquiries, upgrades, new features
    - Escalation Support: For complex issues requiring management attention

    Always explain to the customer which specialist you're connecting them with and why.
    """,
    tools=[lookup_customer, create_ticket, search_knowledge_base],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.CONDITIONAL,
        control_return=ControlReturn.BUBBLE_UP,
        targets=[
            HandoffTarget(
                agent_name="technical_support",
                condition=needs_technical_support,
                description="Hand off to technical support for technical issues",
            ),
            HandoffTarget(
                agent_name="billing_support",
                condition=needs_billing_support,
                description="Hand off to billing support for billing questions",
            ),
            HandoffTarget(
                agent_name="sales_support",
                condition=needs_sales_support,
                description="Hand off to sales support for product inquiries",
            ),
            HandoffTarget(
                agent_name="escalation_support",
                condition=needs_escalation,
                description="Hand off to escalation support for complex issues",
                priority=1,  # Highest priority - checked first
            ),
        ],
    ),
)

# Create Technical Support Agent
technical_support_agent = Agent(
    name="technical_support",
    instructions="""
    You are a Technical Support Specialist focused on resolving technical issues.

    Your expertise:
    - Troubleshooting technical problems
    - Login and authentication issues
    - Performance and connectivity problems
    - API and integration support
    - Bug reporting and tracking

    Always:
    1. Acknowledge the technical issue clearly
    2. Provide step-by-step troubleshooting
    3. Create tickets for unresolved issues
    4. Escalate complex problems when needed
    5. Follow up with clear next steps
    """,
    tools=[create_ticket, search_knowledge_base],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.CONDITIONAL,
        control_return=ControlReturn.BUBBLE_UP,
        targets=[
            HandoffTarget(
                agent_name="escalation_support",
                condition=needs_escalation,
                description="Escalate complex technical issues",
            )
        ],
    ),
)

# Create Billing Support Agent
billing_support_agent = Agent(
    name="billing_support",
    instructions="""
    You are a Billing Support Specialist focused on billing and account issues.

    Your expertise:
    - Billing inquiries and invoice questions
    - Payment processing and methods
    - Subscription management
    - Refunds and credits
    - Account upgrades and downgrades

    Always:
    1. Verify customer account details
    2. Explain billing clearly and transparently
    3. Process requests promptly
    4. Document all billing changes
    5. Provide clear confirmation of actions taken
    """,
    tools=[lookup_customer, create_ticket],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.CONDITIONAL,
        control_return=ControlReturn.BUBBLE_UP,
        targets=[
            HandoffTarget(
                agent_name="escalation_support",
                condition=needs_escalation,
                description="Escalate billing disputes or complex issues",
            )
        ],
    ),
)

# Create Sales Support Agent
sales_support_agent = Agent(
    name="sales_support",
    instructions="""
    You are a Sales Support Specialist focused on helping customers with products and services.

    Your expertise:
    - Product information and features
    - Plan comparisons and recommendations
    - Pricing and quotes
    - Demos and trials
    - Custom enterprise solutions

    Always:
    1. Understand customer needs thoroughly
    2. Provide accurate product information
    3. Make appropriate recommendations
    4. Offer trials or demos when relevant
    5. Create opportunities for upselling appropriately
    """,
    tools=[lookup_customer, search_knowledge_base],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.CONDITIONAL,
        control_return=ControlReturn.BUBBLE_UP,
        targets=[
            HandoffTarget(
                agent_name="escalation_support",
                condition=needs_escalation,
                description="Escalate complex sales inquiries",
            )
        ],
    ),
)

# Create Escalation Support Agent
escalation_support_agent = Agent(
    name="escalation_support",
    instructions="""
    You are an Escalation Support Specialist handling complex and sensitive issues.

    Your role:
    - Handle escalated issues from other agents
    - Manage customer complaints and concerns
    - Coordinate with management when needed
    - Ensure premium customer satisfaction
    - Resolve complex multi-department issues

    Always:
    1. Acknowledge the escalation with empathy
    2. Take ownership of the issue immediately
    3. Provide realistic timelines for resolution
    4. Keep customers updated on progress
    5. Follow up to ensure complete satisfaction

    You have authority to make decisions and provide solutions that other agents cannot.
    """,
    tools=[lookup_customer, create_ticket],
    llm_config=llm_config,
)

# Deploy all agents
agents = {
    "customer_service": customer_service_agent,
    "technical_support": technical_support_agent,
    "billing_support": billing_support_agent,
    "sales_support": sales_support_agent,
    "escalation_support": escalation_support_agent,
}

agent_app = AgentFunctionApp(agents=agents, http_auth_level=func.AuthLevel.ANONYMOUS)


# Demo endpoint to showcase conditional routing
@agent_app.route(route="customer-service-demo", auth_level=func.AuthLevel.ANONYMOUS)
async def customer_service_demo(req: func.HttpRequest) -> func.HttpResponse:
    """
    Demo endpoint showcasing conditional handoff routing.

    This endpoint demonstrates how the customer service agent analyzes
    requests and routes them to appropriate specialists based on content
    and customer context.
    """
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json",
            )

        message = req_body.get("message", "")
        customer_id = req_body.get("customer_id", "customer_123")

        if not message:
            return func.HttpResponse(
                json.dumps({"error": "Message is required"}),
                status_code=400,
                mimetype="application/json",
            )

        # Get customer service runner
        customer_service_runner = agent_app.runners["customer_service"]

        # Add customer context to request
        request_data = {"message": message, "customer_id": customer_id, **req_body}

        # Process request through customer service agent
        # This will trigger conditional handoffs based on request content
        response = await customer_service_runner.run(request_data)

        # Add routing information to response
        routing_info = {
            "request_type": analyze_request_type(message),
            "customer_context": get_customer_context(customer_id),
            "routing_decision": "Determined by conditional handoff logic",
        }

        return func.HttpResponse(
            json.dumps(
                {
                    "agent": "customer_service",
                    "response": response,
                    "routing_info": routing_info,
                    "demonstration": "This shows conditional handoff routing in action",
                }
            ),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Error in customer service demo: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Demo error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


if __name__ == "__main__":
    # For local development
    print("Customer Service Hub with Conditional Handoffs")
    print("Available agents:", list(agents.keys()))
    print("Demo endpoint: POST /api/customer-service-demo")
    print("Standard endpoints: /api/agents/{agent_name}/chat")
