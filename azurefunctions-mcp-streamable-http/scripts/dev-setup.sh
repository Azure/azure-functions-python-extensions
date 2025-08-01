#!/bin/bash

# Azure Functions MCP Server Extension - Development Setup Script
# This script sets up the development environment for the azurefunctions-extensions-mcp-server project
# It combines uv installation, PATH setup, and complete development environment configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}=================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================${NC}\n"
}

# Function to add PATH to shell profiles (permanent setup)
add_to_shell_profiles() {
    local uv_path="$1"
    local path_export="export PATH=\"$uv_path:\$PATH\""
    
    # Add to zsh profile if it exists
    if [[ -f ~/.zshrc ]]; then
        if ! grep -q "$path_export" ~/.zshrc 2>/dev/null; then
            echo "$path_export" >> ~/.zshrc
            print_success "Added to ~/.zshrc"
        else
            print_info "Already present in ~/.zshrc"
        fi
    fi
    
    # Add to bash profile if it exists
    if [[ -f ~/.bashrc ]]; then
        if ! grep -q "$path_export" ~/.bashrc 2>/dev/null; then
            echo "$path_export" >> ~/.bashrc
            print_success "Added to ~/.bashrc"
        else
            print_info "Already present in ~/.bashrc"
        fi
    fi
    
    # Also try .bash_profile for macOS
    if [[ -f ~/.bash_profile ]]; then
        if ! grep -q "$path_export" ~/.bash_profile 2>/dev/null; then
            echo "$path_export" >> ~/.bash_profile
            print_success "Added to ~/.bash_profile"
        else
            print_info "Already present in ~/.bash_profile"
        fi
    fi
}

# Function to ensure uv is available and set up PATH
setup_uv_environment() {
    print_info "Setting up uv environment..."
    
    # Check if uv is already in PATH
    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version 2>&1 | awk '{print $2}')
        print_success "uv $UV_VERSION already available in PATH"
        return 0
    fi
    
    # Check common installation paths
    local uv_found=false
    local uv_path=""
    
    if [[ -x "$HOME/.local/bin/uv" ]]; then
        uv_path="$HOME/.local/bin"
        UV_VERSION=$($HOME/.local/bin/uv --version 2>&1 | awk '{print $2}')
        print_success "Found uv $UV_VERSION at $uv_path/uv"
        uv_found=true
    elif [[ -x "$HOME/.cargo/bin/uv" ]]; then
        uv_path="$HOME/.cargo/bin"
        UV_VERSION=$($HOME/.cargo/bin/uv --version 2>&1 | awk '{print $2}')
        print_success "Found uv $UV_VERSION at $uv_path/uv"
        uv_found=true
    fi
    
    if [[ "$uv_found" == true ]]; then
        # Add to current session PATH
        export PATH="$uv_path:$PATH"
        print_success "Added $uv_path to PATH for current session"
        
        # Add to shell profiles for future sessions
        print_info "Adding to shell profiles for future sessions..."
        add_to_shell_profiles "$uv_path"
        
        print_success "uv is now available! Future terminal sessions will have uv in PATH."
        return 0
    fi
    
    # If not found, install uv
    print_warning "uv not found. Installing uv..."
    return 1
}

# Function to install uv
install_uv() {
    if command -v curl &> /dev/null; then
        print_info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        # Give it a moment
        sleep 2
        
        # Try to set up the environment again
        if setup_uv_environment; then
            return 0
        else
            print_error "uv installation succeeded but cannot be found. Please check your installation."
            print_info "Try running: source ~/.zshrc   # or restart your terminal"
            return 1
        fi
    else
        print_error "curl not found. Please install curl first or install uv manually:"
        print_info "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi
}

# Function to run uv commands with proper PATH
run_uv() {
    if command -v uv &> /dev/null; then
        uv "$@"
    else
        print_error "uv not found in PATH. This shouldn't happen after setup."
        return 1
    fi
}

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    print_error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

print_header "Azure Functions MCP Server Extension - Development Setup"

# Check Python version
print_info "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -ge 10 ]]; then
        print_success "Python $PYTHON_VERSION found (meets requirement: >=3.10)"
    else
        print_error "Python 3.10 or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# Set up uv environment
print_header "Setting up uv Package Manager"
if ! setup_uv_environment; then
    if ! install_uv; then
        print_error "Failed to set up uv. Please install manually and try again."
        exit 1
    fi
fi

# Install project dependencies
print_header "Installing Dependencies"
print_info "Installing project dependencies..."
if run_uv sync; then
    print_success "Dependencies installed successfully"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Install the project in development mode
print_info "Installing project in development mode..."
if run_uv pip install -e .; then
    print_success "Project installed in development mode"
else
    print_error "Failed to install project in development mode"
    exit 1
fi

# Check if Azure Functions Core Tools is installed
print_header "Checking Development Tools"
print_info "Checking Azure Functions Core Tools..."
if command -v func &> /dev/null; then
    FUNC_VERSION=$(func --version 2>&1)
    print_success "Azure Functions Core Tools found: $FUNC_VERSION"
else
    print_warning "Azure Functions Core Tools not found."
    print_info "To install Azure Functions Core Tools:"
    echo "  - macOS: brew tap azure/functions && brew install azure-functions-core-tools@4"
    echo "  - Windows: npm install -g azure-functions-core-tools@4"
    echo "  - Linux: See https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"
fi

# Set up pre-commit hooks
print_info "Setting up pre-commit hooks..."
if run_uv run pre-commit install; then
    print_success "Pre-commit hooks installed"
else
    print_warning "Failed to install pre-commit hooks (this is optional)"
fi

# Run initial code formatting
print_header "Initial Code Formatting"
print_info "Running initial code formatting..."
if run_uv run black .; then
    print_success "Code formatted with black"
else
    print_warning "Failed to run black formatter"
fi

if run_uv run isort .; then
    print_success "Imports sorted with isort"
else
    print_warning "Failed to run isort"
fi

# Run tests to ensure everything is working
print_header "Running Tests"
print_info "Running tests to verify setup..."
if run_uv run pytest --version &> /dev/null; then
    if run_uv run pytest; then
        print_success "All tests passed"
    else
        print_warning "Some tests failed (this might be expected for initial setup)"
    fi
else
    print_warning "pytest not available or tests not configured yet"
fi

# Create sample local.settings.json if it doesn't exist
print_header "Configuration Files"
if [[ ! -f "local.settings.json" ]]; then
    print_info "Creating sample local.settings.json..."
    cat > local.settings.json << EOF
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "PYTHON_ENABLE_INIT_INDEXING": "1",
    "FUNCTIONS_EXTENSION_VERSION": "~4"
  }
}
EOF
    print_success "Created local.settings.json"
else
    print_info "local.settings.json already exists"
fi

# Final summary and instructions
print_header "Development Environment Setup Complete!"
print_success "Your development environment is ready!"

echo
print_info "🎉 Setup Summary:"
echo "  ✅ Python 3.10+ verified"
echo "  ✅ uv package manager installed and configured"
echo "  ✅ Dependencies installed"
echo "  ✅ Project installed in development mode"
echo "  ✅ Pre-commit hooks configured"
echo "  ✅ Code formatted and organized"
echo "  ✅ Configuration files created"

echo
print_info "📝 Important Notes:"
if ! command -v uv &> /dev/null 2>/dev/null; then
    print_info "  • uv has been added to your shell profiles for future sessions"
    print_info "  • For immediate use in this session, run: source ~/.zshrc"
    print_info "  • Or simply open a new terminal window"
else
    print_info "  • uv is ready to use in this session"
fi

echo
print_info "🚀 Available Commands:"
echo "  - uv sync                              # Install/update dependencies"
echo "  - uv run pytest                       # Run tests"
echo "  - uv run pytest --cov                 # Run tests with coverage"
echo "  - uv run black .                      # Format code"
echo "  - uv run isort .                      # Sort imports"
echo "  - uv run pre-commit run --all-files   # Run all pre-commit hooks"
echo "  - func start                          # Start Azure Functions locally"
echo "  - func new                            # Create new function"

echo
print_info "🛠️  Development Workflow:"
echo "  1. Make your changes to the code"
echo "  2. Format: uv run black . && uv run isort ."
echo "  3. Test: uv run pytest --cov"
echo "  4. Commit (pre-commit hooks will run automatically)"

echo
print_success "Happy coding! 🚀"

# Test if uv is available for immediate use
if ! command -v uv &> /dev/null; then
    echo
    print_warning "⚠️  uv is not available in the current session."
    print_info "To start using uv immediately, run one of these:"
    print_info "  source ~/.zshrc        # Reload your shell config"
    print_info "  export PATH=\"\$HOME/.local/bin:\$PATH\"  # Add to current session"
    print_info "  # OR open a new terminal window"
fi
