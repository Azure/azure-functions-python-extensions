# Contributing to Azure Functions Agent Framework

Thank you for your interest in contributing to the Azure Functions Agent Framework! This document provides guidelines and information for developers who want to contribute to the project.

## 📋 Table of Contents

- [Getting Started](#-getting-started)
- [Development Setup](#-development-setup)
- [Project Architecture](#-project-architecture)
- [Development Workflow](#-development-workflow)
- [Code Quality](#-code-quality)
- [Testing](#-testing)
- [Pull Request Process](#-pull-request-process)
- [Release Process](#-release-process)

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** (3.10, 3.11, 3.12, 3.13 supported)
- **Git** for version control
- **Azure Functions Core Tools** for local development and testing
- **Docker** (optional, for containerized development)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/azure-functions-python-extensions.git
   cd azure-functions-python-extensions/azurefunctions-agents-framework
   ```

## 🛠 Development Setup

### 1. Create Virtual Environment

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Development Dependencies

```bash
# Install the package in editable mode with all dependencies
pip install -e ".[all,dev]"

# Or install development requirements
pip install -r requirements.txt
```

### 3. Install Pre-commit Hooks

We use pre-commit hooks to ensure code quality. These will automatically run linting and formatting on every commit:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# (Optional) Run on all files to test
pre-commit run --all-files
```

### 4. Manual Linting

You can also run linting manually using our script:

```bash
# Make the script executable
chmod +x scripts/lint.sh

# Run all linting tools
./scripts/lint.sh
```

The linting includes:

- **autoflake**: Removes unused imports and variables
- **isort**: Sorts and organizes imports
- **black**: Code formatting
- **flake8**: Code linting and style checking

## 🏗 Project Architecture

### Core Components

```text
azurefunctions/agents/
├── __init__.py              # Main package exports
├── agents.py                # Core Agent class and functionality
├── core.py                  # Azure Functions integration layer
├── runner.py                # Agent execution and handoff system
├── types.py                 # Type definitions and schemas
├── a2a/                     # Agent-to-Agent communication
├── handoff/                 # Agent handoff system
├── mcp/                     # Model Context Protocol integration
├── model_providers/         # LLM provider implementations
└── tools/                   # Built-in agent tools
```

### Key Architecture Principles

1. **Modular Design**: Each component has a specific responsibility
2. **Provider Abstraction**: Support for multiple LLM providers through common interfaces
3. **Azure-First**: Built specifically for Azure Functions with enterprise features
4. **Extensible**: Easy to add new providers, tools, and capabilities
5. **Production-Ready**: Comprehensive error handling, logging, and monitoring

### Core Classes

- **`Agent`**: Main agent class with LLM integration and tool execution
- **`AgentRunner`**: Handles agent execution, streaming, and handoffs
- **`MCPTool`**: Integration with Model Context Protocol servers
- **`HandoffSystem`**: Manages agent-to-agent communication and workflows

## 🔄 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Development Guidelines

- **Write tests** for new functionality
- **Update documentation** for API changes
- **Follow coding standards** (enforced by pre-commit hooks)
- **Add samples** for new features when appropriate
- **Update type hints** for all new code

### 3. Test Your Changes

```bash
# Run tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_your_feature.py

# Run with coverage
python -m pytest --cov=azurefunctions tests/
```

### 4. Test with Samples

Test your changes with the provided samples:

```bash
cd samples/single-agent
func start
```

## ✅ Code Quality

### Linting and Formatting

The project uses several tools to maintain code quality:

- **autoflake**: Removes unused imports and variables
- **isort**: Sorts imports according to PEP8
- **black**: Code formatter with 88 character line length
- **flake8**: Linting for style and potential errors
- **mypy**: Static type checking (optional but recommended)

### Configuration

All tools are configured in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 88

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503", "E501"]
```

### Excluded Directories

The following directories are excluded from linting:

- `tests/` - Test files may have different style requirements
- `samples/` - Sample code for demonstration purposes
- `test_files_llm_created/` - Auto-generated test files
- `docs/`, `.venv/`, `__pycache__/` - Standard exclusions

## 🧪 Testing

### Test Structure

```text
tests/
├── unit/                    # Unit tests
├── integration/             # Integration tests
├── samples/                 # Sample-based tests
└── conftest.py             # Pytest configuration
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test category
python -m pytest tests/unit/
python -m pytest tests/integration/

# Run with coverage report
python -m pytest --cov=azurefunctions --cov-report=html

# Run tests matching a pattern
python -m pytest -k "test_agent"
```

### Writing Tests

- Use `pytest` as the testing framework
- Follow the AAA pattern (Arrange, Act, Assert)
- Mock external dependencies (LLM APIs, Azure services)
- Test both success and error scenarios
- Include integration tests for complete workflows

Example test structure:

```python
import pytest
from azurefunctions.agents import Agent

class TestAgent:
    def test_agent_initialization(self):
        # Arrange
        agent_config = {...}

        # Act
        agent = Agent(agent_config)

        # Assert
        assert agent.name == "test-agent"

    @pytest.mark.asyncio
    async def test_agent_execution(self):
        # Test async agent functionality
        pass
```

## 📝 Pull Request Process

### 1. Before Submitting

- [ ] All tests pass locally
- [ ] Pre-commit hooks pass
- [ ] Documentation is updated
- [ ] CHANGELOG is updated (if applicable)
- [ ] Code follows project conventions

### 2. PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added for new functionality
```

### 3. Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: Team members review for:
   - Code quality and style
   - Architecture alignment
   - Test coverage
   - Documentation completeness
3. **Final Review**: Maintainer approval required

## 🚀 Release Process

### Versioning

The project follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Steps

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. Tag release after merge
5. Automated deployment to PyPI

## 📞 Getting Help

### Community Support

- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Discord/Slack**: Real-time community chat (link when available)

### Development Questions

For development-specific questions:

1. Check existing GitHub issues and discussions
2. Review the documentation and samples
3. Create a new issue with the `question` label

### Code of Conduct

Please note that this project follows the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). By participating, you are expected to uphold this code.

## 📚 Additional Resources

- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)

---

Thank you for contributing to the Azure Functions Agent Framework! 🎉
