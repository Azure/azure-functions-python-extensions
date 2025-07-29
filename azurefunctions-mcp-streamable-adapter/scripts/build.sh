#!/bin/bash

# Build and package script for Azure Functions MCP Server Extension
# This script builds the package for distribution

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

print_header "Building Azure Functions MCP Server Extension Package"

# Clean previous builds
print_info "Cleaning previous builds..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/
print_success "Cleaned previous builds"

# Run tests before building
print_info "Running tests before building..."
if uv run pytest; then
    print_success "All tests passed"
else
    print_error "Tests failed. Please fix tests before building."
    exit 1
fi

# Run code quality checks
print_info "Running code quality checks..."
if ./scripts/format.sh --check; then
    print_success "Code quality checks passed"
else
    print_error "Code quality checks failed. Please fix issues before building."
    exit 1
fi

# Build the package
print_info "Building the package..."
if uv build; then
    print_success "Package built successfully"
else
    print_error "Failed to build package"
    exit 1
fi

# List built packages
print_info "Built packages:"
ls -la dist/

print_success "Build completed successfully! 🎉"
print_info "Built packages are available in the 'dist/' directory"
