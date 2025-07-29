# Development Scripts

This directory contains scripts to help with development, testing, and building of the Azure Functions MCP Server Extension.

## Scripts Overview

### `dev-setup.sh` ⭐
**Complete development environment setup script**

This is the **main script** that handles everything you need to get started:

- **Python version verification** (>=3.10 requirement)
- **uv installation and PATH setup** (automatic installation if not present)
- **Shell profile configuration** (adds uv to ~/.zshrc, ~/.bashrc, ~/.bash_profile)
- **Project dependencies installation** via `uv sync`
- **Development mode installation** of the project
- **Azure Functions Core Tools check**
- **Pre-commit hooks setup**
- **Initial code formatting** (black + isort)
- **Test execution** to verify setup
- **Sample configuration files** creation

```bash
# Run this once to set up everything:
./scripts/dev-setup.sh
```

**Features:**
- ✅ **Smart uv detection**: Finds uv in common locations (`~/.local/bin`, `~/.cargo/bin`)
- ✅ **Automatic PATH setup**: Adds uv to your shell profiles for permanent access
- ✅ **Current session support**: Makes uv available immediately
- ✅ **Comprehensive error handling**: Clear error messages and recovery suggestions
- ✅ **Progress tracking**: Organized sections with clear status updates

### `test.sh`
**Test runner with various options**

Runs tests with different configurations:

```bash
# Run all tests
./scripts/test.sh

# Run tests with coverage
./scripts/test.sh --coverage

# Run tests in verbose mode
./scripts/test.sh --verbose

# Run only fast tests (skip slow integration tests)
./scripts/test.sh --fast

# Combine options
./scripts/test.sh --coverage --verbose
```

### `format.sh`
**Code formatting and quality checks**

Runs code formatters and linters:

```bash
# Check formatting (shows diff but doesn't modify files)
./scripts/format.sh

# Auto-fix formatting issues
./scripts/format.sh --fix

# Only check formatting (exit with error if issues found)
./scripts/format.sh --check
```

### `build.sh`
**Package building script**

Builds the package for distribution:
- Runs tests before building
- Performs code quality checks
- Builds wheel and source distributions

```bash
./scripts/build.sh
```

## Usage Workflow

**Simplified Setup** (recommended):

1. **Complete Setup**: Run `./scripts/dev-setup.sh` once to set up everything
2. **Development**: Use the available commands for development workflow
3. **Building**: Use `./scripts/build.sh` when ready to create distribution packages

**Traditional Workflow** (if you prefer step-by-step):

1. **Initial Setup**: Run `./scripts/dev-setup.sh` once to set up your development environment
2. **Development**: Use `./scripts/format.sh --fix` to format code and `./scripts/test.sh` to run tests
3. **Pre-commit**: The setup installs pre-commit hooks that run automatically
4. **Building**: Use `./scripts/build.sh` when ready to create distribution packages

## PATH Setup for uv

The `dev-setup.sh` script automatically handles uv PATH configuration:

- **Detects existing uv installations** in `~/.local/bin` or `~/.cargo/bin`
- **Installs uv automatically** if not found
- **Updates shell profiles** (`.zshrc`, `.bashrc`, `.bash_profile`) for permanent access
- **Provides clear instructions** for immediate use in current session

**If you need manual PATH setup:**
```bash
# For current session only:
export PATH="$HOME/.local/bin:$PATH"

# For permanent setup, add to your shell profile:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Requirements

- **macOS/Linux**: These scripts are designed for Unix-like systems
- **Bash**: All scripts require bash shell
- **Python 3.10+**: Required for the project
- **curl**: Used for uv installation (if needed)

## Tool Configuration

The scripts work with configuration in `pyproject.toml`:
- **pytest**: Test configuration and markers
- **black**: Code formatting settings
- **isort**: Import sorting configuration
- **coverage**: Coverage reporting settings
- **mypy**: Type checking configuration

## Integration with uv

All scripts are designed to work with `uv` package manager:
- Dependencies are managed through `uv sync`
- Tools are run via `uv run <tool>`
- Development dependencies are specified in `[tool.uv] dev-dependencies`
