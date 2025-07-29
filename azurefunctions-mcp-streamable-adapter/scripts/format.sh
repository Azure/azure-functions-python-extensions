#!/bin/bash

# Code formatting and linting script for Azure Functions MCP Server Extension
# This script runs all code quality checks and formatters

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}=================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================${NC}\n"
}

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    print_error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

print_header "Code Quality Check for Azure Functions MCP Server Extension"

# Parse command line arguments
FIX=false
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix|-f)
            FIX=true
            shift
            ;;
        --check|-c)
            CHECK_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --fix, -f         Auto-fix formatting issues"
            echo "  --check, -c       Only check formatting, don't modify files"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

FAILED=false

# Run isort
print_info "Checking import sorting with isort..."
if [[ $FIX == true ]]; then
    if uv run isort .; then
        print_success "Imports sorted successfully"
    else
        print_error "Failed to sort imports"
        FAILED=true
    fi
elif [[ $CHECK_ONLY == true ]]; then
    if uv run isort --check-only .; then
        print_success "Import sorting is correct"
    else
        print_error "Import sorting issues found. Run with --fix to auto-fix"
        FAILED=true
    fi
else
    if uv run isort --diff .; then
        print_success "Import sorting is correct"
    else
        print_warning "Import sorting issues found. Run with --fix to auto-fix"
    fi
fi

# Run black
print_info "Checking code formatting with black..."
if [[ $FIX == true ]]; then
    if uv run black .; then
        print_success "Code formatted successfully"
    else
        print_error "Failed to format code"
        FAILED=true
    fi
elif [[ $CHECK_ONLY == true ]]; then
    if uv run black --check .; then
        print_success "Code formatting is correct"
    else
        print_error "Code formatting issues found. Run with --fix to auto-fix"
        FAILED=true
    fi
else
    if uv run black --diff .; then
        print_success "Code formatting is correct"
    else
        print_warning "Code formatting issues found. Run with --fix to auto-fix"
    fi
fi

# Run pre-commit hooks if available
if [[ -f ".pre-commit-config.yaml" ]]; then
    print_info "Running pre-commit hooks..."
    if uv run pre-commit run --all-files; then
        print_success "All pre-commit hooks passed"
    else
        if [[ $CHECK_ONLY == true ]]; then
            print_error "Pre-commit hooks failed"
            FAILED=true
        else
            print_warning "Some pre-commit hooks failed"
        fi
    fi
fi

# Summary
if [[ $FAILED == true ]]; then
    print_error "Code quality checks failed!"
    exit 1
else
    print_success "All code quality checks passed!"
fi
