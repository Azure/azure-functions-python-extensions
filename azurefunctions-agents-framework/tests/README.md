# Azure Functions Agent Framework - Unit Tests

This directory contains comprehensive unit tests for the Azure Functions Agent Framework.

## 📁 Test Structure

```text
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and shared fixtures
├── unit/                    # Unit tests for individual components
│   ├── __init__.py
│   ├── test_agents.py       # Agent class tests
│   ├── test_core.py         # AgentFunctionApp tests
│   ├── test_runner.py       # Runner class tests
│   ├── test_types.py        # Type definitions tests
│   ├── test_tools/          # Tool-related tests
│   ├── test_handoff/        # Handoff system tests
│   ├── test_mcp/            # MCP integration tests
│   ├── test_model_providers/ # LLM provider tests
│   └── test_a2a/            # A2A protocol tests
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_agent_workflows.py # End-to-end agent workflows
│   ├── test_handoff_flows.py   # Multi-agent handoff workflows
│   ├── test_mcp_integration.py # MCP server integration
│   └── test_azure_functions.py # Azure Functions integration
├── fixtures/                # Test fixtures and test data
│   ├── __init__.py
│   ├── mock_llm_responses.py # Mock LLM responses
│   ├── sample_tools.py       # Sample tool implementations
│   └── test_agents.py        # Predefined test agents
└── README.md               # This file
```

## 🚀 Running Tests

### Install Test Dependencies

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Or install test dependencies separately
pip install pytest pytest-asyncio pytest-mock pytest-cov aioresponses
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=azurefunctions.agents --cov-report=html

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests only
pytest tests/unit/test_agents.py      # Specific test file
```

### Run Tests with Different Verbosity

```bash
# Verbose output
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Run parallel tests (requires pytest-xdist)
pytest -n auto
```

## 🧪 Test Categories

### Unit Tests

Test individual components in isolation with mocked dependencies:

- **Agent Tests**: Agent initialization, tool registration, request processing
- **Core Tests**: AgentFunctionApp routing, endpoint registration
- **Runner Tests**: Request normalization, agent execution
- **Handoff Tests**: Handoff configuration, control flow, routing logic
- **MCP Tests**: MCP server connections, tool discovery
- **Provider Tests**: LLM provider integrations, API calls

### Integration Tests

Test component interactions and end-to-end workflows:

- **Agent Workflows**: Complete request-response cycles
- **Handoff Flows**: Multi-agent collaboration scenarios
- **MCP Integration**: Real MCP server communication
- **Azure Functions**: HTTP endpoint testing

## 🔧 Test Configuration

### Environment Variables

Set these environment variables for comprehensive testing:

```bash
# Required for LLM provider tests (use test API keys or mocks)
TEST_OPENAI_API_KEY=test-key-or-mock
TEST_ANTHROPIC_API_KEY=test-key-or-mock
TEST_GOOGLE_API_KEY=test-key-or-mock

# Optional: For Azure integration tests
TEST_AZURE_CLIENT_ID=test-client-id
TEST_AZURE_CLIENT_SECRET=test-client-secret
TEST_AZURE_TENANT_ID=test-tenant-id

# Test configuration
PYTEST_CURRENT_TEST=true
TEST_MODE=unit  # or integration
```

### Pytest Configuration

The `conftest.py` file contains shared fixtures and configuration:

- **Mock LLM Responses**: Predefined responses for testing
- **Test Agents**: Preconfigured agents for testing
- **Test Tools**: Sample tools for testing
- **Async Test Support**: Proper async test handling

## 📊 Coverage Goals

Target test coverage for each module:

- **Core Components**: >95% coverage
- **Agent Classes**: >90% coverage
- **Handoff System**: >90% coverage
- **MCP Integration**: >85% coverage
- **Provider Integrations**: >80% coverage
- **Overall Project**: >85% coverage

## 🧩 Mock Strategy

### LLM Provider Mocking

- Mock external API calls to LLM providers
- Use predefined responses for consistent testing
- Test error scenarios and edge cases

### Azure Functions Mocking

- Mock Azure Functions context and bindings
- Test HTTP request/response handling
- Validate endpoint registration and routing

### MCP Server Mocking

- Mock MCP server communication
- Test tool discovery and execution
- Validate error handling and timeouts

## 🚨 Test Guidelines

### Writing Good Tests

1. **Descriptive Names**: Test names should clearly describe what's being tested
2. **Arrange-Act-Assert**: Follow the AAA pattern
3. **Independent Tests**: Tests should not depend on each other
4. **Mock External Dependencies**: Isolate units under test
5. **Test Edge Cases**: Include error conditions and boundary cases

### Example Test Structure

```python
import pytest
from unittest.mock import AsyncMock, Mock
from azurefunctions.agents import Agent, LLMConfig, LLMProvider

class TestAgent:
    @pytest.fixture
    def mock_llm_config(self):
        return LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )

    @pytest.fixture
    def sample_agent(self, mock_llm_config):
        return Agent(
            name="TestAgent",
            instructions="Test agent instructions",
            llm_config=mock_llm_config
        )

    @pytest.mark.asyncio
    async def test_agent_initialization(self, sample_agent):
        # Arrange - Done in fixture

        # Act & Assert
        assert sample_agent.name == "TestAgent"
        assert sample_agent.instructions == "Test agent instructions"
        assert sample_agent.llm_config.provider == LLMProvider.OPENAI

    @pytest.mark.asyncio
    async def test_agent_chat_with_mocked_response(self, sample_agent, mock_llm_response):
        # Arrange
        message = "Hello, agent!"

        # Act
        response = await sample_agent.chat(message)

        # Assert
        assert response.success
        assert "Hello" in response.content
```

## 🔄 Continuous Integration

### GitHub Actions Integration

The tests are designed to run in CI/CD pipelines:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest --cov=azurefunctions.agents --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## 🐛 Debugging Tests

### Common Issues

1. **Async Test Failures**: Ensure `@pytest.mark.asyncio` is used
2. **Mock Not Working**: Verify mock paths and patching
3. **Import Errors**: Check PYTHONPATH and package structure
4. **Resource Cleanup**: Use fixtures for proper setup/teardown

### Debug Commands

```bash
# Run with debugging
pytest --pdb                   # Drop into debugger on failure
pytest --pdb-trace            # Drop into debugger at start
pytest --capture=no           # Show all output
pytest -vvv                   # Maximum verbosity
```

This comprehensive test suite ensures the Azure Functions Agent Framework is robust, reliable, and maintainable.
