#!/bin/bash

# Test runner script for Azure Functions MCP Server Extension
# This script runs tests with various configurations

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

print_header "Running Tests for Azure Functions MCP Server Extension"

# Parse command line arguments
COVERAGE=false
VERBOSE=false
FAST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --fast|-f)
            FAST=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --coverage, -c    Run tests with coverage report"
            echo "  --verbose, -v     Run tests in verbose mode"
            echo "  --fast, -f        Run only fast tests (skip slow integration tests)"
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

# Build test command
TEST_CMD="uv run pytest"

if [[ $VERBOSE == true ]]; then
    TEST_CMD="$TEST_CMD -v"
fi

if [[ $FAST == true ]]; then
    TEST_CMD="$TEST_CMD -m 'not slow'"
fi

if [[ $COVERAGE == true ]]; then
    TEST_CMD="$TEST_CMD --cov=azurefunctions.extensions.mcp_server --cov-report=html --cov-report=term-missing"
fi

# Run the tests
print_info "Running command: $TEST_CMD"
echo

if eval $TEST_CMD; then
    print_success "All tests passed!"
    
    if [[ $COVERAGE == true ]]; then
        print_info "Coverage report generated in htmlcov/"
        print_info "Open htmlcov/index.html in your browser to view the coverage report"
    fi
else
    print_error "Some tests failed!"
    exit 1
fi
