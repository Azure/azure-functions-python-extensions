# Customer Service Hub - Conditional Handoff Pattern

This sample demonstrates the **CONDITIONAL handoff pattern** where agents use AI-powered routing to intelligently direct conversations to the most appropriate specialist based on request content, customer context, and business rules.

## Architecture

```text
                         ┌─────────────────┐
                         │ Customer Request│
                         │    (Any Type)   │
                         └─────────┬───────┘
                                   │
                         ┌─────────▼───────┐
                         │ Customer Service│◄─── Main Router
                         │     Agent       │     • Analyzes requests
                         │  (AI Router)    │     • Applies routing rules
                         └─────┬───┬───┬───┘     • Conditional handoffs
                               │   │   │
                 ┌─────────────┘   │   └─────────────┐
                 │                 │                 │
         ┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
         │ Technical     │ │ Billing       │ │ Sales         │
         │ Support       │ │ Support       │ │ Support       │
         │               │ │               │ │               │
         │ • Bug fixes   │ │ • Payments    │ │ • Products    │
         │ • Login help  │ │ • Invoices    │ │ • Features    │
         │ • Performance │ │ • Refunds     │ │ • Trials      │
         └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
                 │                 │                 │
                 └─────────────────┼─────────────────┘
                                   │
                         ┌─────────▼───────┐
                         │ Escalation      │
                         │ Support         │◄─── High Priority
                         │                 │     • Complex issues
                         │ • Complaints    │     • VIP customers
                         │ • Management    │     • Urgent matters
                         │ • Authority     │
                         └─────────────────┘
```

## Agents

### Customer Service Agent (AI Router)

- **Role**: Intelligent request analyzer and router
- **Capabilities**:
  - Natural language analysis of customer requests
  - Customer context lookup and analysis
  - Smart routing based on multiple criteria
  - Escalation detection and handling
- **Routing Logic**: Uses AI + rules to determine best agent

### Technical Support Agent

- **Role**: Technical issue resolution specialist  
- **Capabilities**: Troubleshooting, bug fixes, login help, performance issues
- **Triggers**: Keywords like "error", "bug", "not working", "login", "slow"

### Billing Support Agent

- **Role**: Billing and account management specialist
- **Capabilities**: Payment processing, invoices, refunds, subscriptions
- **Triggers**: Keywords like "bill", "payment", "charge", "refund", "subscription"

### Sales Support Agent

- **Role**: Product and sales specialist
- **Capabilities**: Product info, demos, trials, pricing, feature comparisons
- **Triggers**: Keywords like "buy", "purchase", "demo", "trial", "pricing"

### Escalation Support Agent

- **Role**: High-priority and complex issue specialist
- **Capabilities**: Management authority, complaint resolution, VIP handling
- **Triggers**: Escalation keywords, VIP customers, multiple issues, low satisfaction

## Key Features

### Intelligent Request Analysis

```python
def analyze_request_type(message: str) -> str:
    """AI-powered request categorization"""
    # Keyword scoring across categories
    # Returns: 'technical', 'billing', 'sales', 'escalation', 'general'
```

### Customer Context Awareness

```python
def get_customer_context(customer_id: str) -> Dict[str, Any]:
    """Customer history and profile analysis"""
    # Account type, satisfaction score, issue history
```

### Multi-Factor Routing

- **Content Analysis**: Keywords and natural language understanding
- **Customer Profile**: Account type, history, satisfaction scores  
- **Business Rules**: Escalation triggers, priority handling
- **AI Decision Making**: Best-match agent selection

### Automatic Escalation

- Premium customers with multiple issues
- Low satisfaction scores (< 3.0)
- Explicit escalation keywords
- Complex multi-department issues

## API Endpoints

### Standard Agent Endpoints

```bash
# Chat with customer service (main router)
POST /api/agents/customer_service/chat

# Chat with specific specialists directly
POST /api/agents/technical_support/chat
POST /api/agents/billing_support/chat  
POST /api/agents/sales_support/chat
POST /api/agents/escalation_support/chat

# List all agents
GET /api/agents

# Get agent information
GET /api/agents/{agent_name}/info
```

### Demo Endpoint

```bash
# Demonstrates conditional routing with analysis
POST /api/customer-service-demo

# Health check
GET /api/health
```

## Quick Start

### 1. Setup

```bash
cd samples/handoff-conditional
cp local.settings.json.template local.settings.json

# Edit local.settings.json and add your API keys:
# - OPENAI_API_KEY: Your OpenAI API key
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Locally

```bash
func start
```

### 4. Test Conditional Routing

#### Technical Support Routing

```bash
curl -X POST http://localhost:7071/api/customer-service-demo \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am having login errors and the app keeps crashing", 
    "customer_id": "customer_123"
  }'
```

Expected routing: `customer_service` → `technical_support`

#### Billing Support Routing

```bash
curl -X POST http://localhost:7071/api/customer-service-demo \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need help with my invoice and want to cancel my subscription",
    "customer_id": "customer_456"  
  }'
```

Expected routing: `customer_service` → `billing_support`

#### Sales Support Routing

```bash
curl -X POST http://localhost:7071/api/customer-service-demo \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to upgrade to the enterprise plan and need a demo",
    "customer_id": "customer_123"
  }'
```

Expected routing: `customer_service` → `sales_support`

#### Escalation Routing

```bash
curl -X POST http://localhost:7071/api/customer-service-demo \
  -H "Content-Type: application/json" \
  -d '{
    "message": "This is urgent! I need to speak to a manager about this issue",
    "customer_id": "customer_123"
  }'
```

Expected routing: `customer_service` → `escalation_support`

### 5. Test Standard Agent Endpoints

```bash
# Direct technical support
curl -X POST http://localhost:7071/api/agents/technical_support/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Help me troubleshoot my login issue"}'

# Direct billing support  
curl -X POST http://localhost:7071/api/agents/billing_support/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need my latest invoice"}'
```

## Response Format

```json
{
  "agent": "customer_service",
  "response": "I'll connect you with our technical support team...",
  "routing_info": {
    "request_type": "technical",
    "customer_context": {
      "account_type": "premium",
      "satisfaction_score": 4.2,
      "issues_history": ["billing", "technical"]
    },
    "routing_decision": "Determined by conditional handoff logic"
  },
  "handoff_path": ["customer_service", "technical_support"],
  "demonstration": "This shows conditional handoff routing in action"
}
```

## Routing Logic

### Request Type Analysis

The system analyzes requests using multiple factors:

1. **Keyword Scoring**: Counts category-specific keywords
2. **Customer History**: Previous issues and patterns
3. **Account Priority**: Premium vs. basic customers  
4. **Satisfaction Tracking**: Low scores trigger escalation
5. **Urgency Detection**: Critical/urgent language

### Conditional Functions

```python
# Each agent target has a condition function
def needs_technical_support(request_data: Dict[str, Any]) -> bool:
    message = request_data.get('message', '')
    return analyze_request_type(message) == 'technical'

def needs_escalation(request_data: Dict[str, Any]) -> bool:
    # Multi-factor escalation logic
    return should_escalate(message, customer_context)
```

### Priority Handling

- **Escalation**: Highest priority (priority=1)
- **Specialist Routing**: Standard priority
- **General Handling**: Fallback when no conditions match

## Advanced Configuration

### Custom Routing Rules

```python
def custom_routing_condition(request_data: Dict[str, Any]) -> bool:
    """Custom business logic for routing."""
    # Add your specific routing rules here
    return your_condition_logic(request_data)

HandoffTarget(
    agent_name="custom_specialist",
    condition=custom_routing_condition,
    description="Custom routing logic",
    priority=2
)
```

### Context Passing

```python
HandoffTarget(
    agent_name="specialist",
    condition=routing_condition,
    context_keys=["customer_id", "issue_history"],  # Pass context
    description="Route with customer context"
)
```

### AI-Powered Enhancement

The framework can be enhanced with more sophisticated AI routing:

```python
# Use LLM for routing decisions
routing_prompt = """
Analyze this customer request and determine the best agent:
- Technical Support: for technical issues
- Billing Support: for billing questions  
- Sales Support: for product inquiries
- Escalation Support: for complex issues

Request: {message}
Customer: {customer_context}
"""
```

## Production Considerations

### Performance

- Routing decisions are fast (< 100ms)
- Customer lookups are cached
- Knowledge base searches are optimized
- Minimal latency for standard requests

### Monitoring

- Track routing accuracy and customer satisfaction
- Monitor handoff success rates
- Alert on escalation patterns
- Measure resolution times by category

### Scalability

- Each agent can scale independently
- Routing logic is stateless and cacheable
- Customer context can be stored in external systems
- Supports horizontal scaling in Azure Functions

## Troubleshooting

### Common Issues

1. **Incorrect Routing**: Check keyword lists and scoring logic
2. **Missing Handoffs**: Verify condition functions return boolean
3. **Performance Issues**: Cache customer lookups and optimize queries
4. **Escalation Problems**: Review escalation triggers and customer context

### Debug Mode

Enable detailed logging to see routing decisions:

```python
logging.getLogger().setLevel(logging.DEBUG)
```

### Testing Routing Logic

Test individual routing functions:

```python
# Test request analysis
request_type = analyze_request_type("My app is crashing")
assert request_type == "technical"

# Test escalation logic  
should_escalate = needs_escalation({"message": "I want to speak to a manager"})
assert should_escalate == True
```

This sample demonstrates production-ready conditional handoff patterns with intelligent routing, customer context awareness, and comprehensive escalation handling.
