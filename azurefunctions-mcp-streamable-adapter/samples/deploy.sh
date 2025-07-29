#!/bin/bash

# Azure Functions MCP Server Deployment Script
# This script helps deploy the MCP server to Azure Functions

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

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed. Please install it first."
        print_info "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    print_success "Azure CLI found"
    
    # Check Azure Functions Core Tools
    if ! command -v func &> /dev/null; then
        print_error "Azure Functions Core Tools is not installed. Please install it first."
        print_info "Install from: https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"
        exit 1
    fi
    print_success "Azure Functions Core Tools found"
    
    # Check if logged in to Azure
    if ! az account show &> /dev/null; then
        print_error "Not logged in to Azure. Please run 'az login' first."
        exit 1
    fi
    print_success "Azure CLI authenticated"
}

# Get deployment parameters
get_deployment_params() {
    print_header "Deployment Configuration"
    
    # Function App Name
    if [ -z "$FUNCTION_APP_NAME" ]; then
        read -p "Enter Function App name: " FUNCTION_APP_NAME
    fi
    
    # Resource Group
    if [ -z "$RESOURCE_GROUP" ]; then
        read -p "Enter Resource Group name (will be created if it doesn't exist): " RESOURCE_GROUP
    fi
    
    # Location
    if [ -z "$LOCATION" ]; then
        read -p "Enter Azure region (e.g., eastus, westus2): " LOCATION
    fi
    
    # Storage Account (auto-generate if not provided)
    if [ -z "$STORAGE_ACCOUNT" ]; then
        STORAGE_ACCOUNT="${FUNCTION_APP_NAME}storage$(date +%s)"
    fi
    
    print_info "Deployment Configuration:"
    print_info "  Function App: $FUNCTION_APP_NAME"
    print_info "  Resource Group: $RESOURCE_GROUP"
    print_info "  Location: $LOCATION"
    print_info "  Storage Account: $STORAGE_ACCOUNT"
    
    echo
    read -p "Continue with deployment? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_info "Deployment cancelled"
        exit 0
    fi
}

# Create Azure resources
create_resources() {
    print_header "Creating Azure Resources"
    
    # Create resource group
    print_info "Creating resource group..."
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION" || {
        print_warning "Resource group might already exist"
    }
    print_success "Resource group ready"
    
    # Create storage account
    print_info "Creating storage account..."
    az storage account create \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Standard_LRS || {
        print_warning "Storage account might already exist"
    }
    print_success "Storage account ready"
    
    # Create function app
    print_info "Creating function app..."
    az functionapp create \
        --resource-group "$RESOURCE_GROUP" \
        --consumption-plan-location "$LOCATION" \
        --runtime python \
        --runtime-version 3.11 \
        --functions-version 4 \
        --name "$FUNCTION_APP_NAME" \
        --storage-account "$STORAGE_ACCOUNT" \
        --os-type Linux || {
        print_error "Failed to create function app"
        exit 1
    }
    print_success "Function app created"
}

# Configure function app
configure_function_app() {
    print_header "Configuring Function App"
    
    print_info "Setting application settings..."
    az functionapp config appsettings set \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --settings \
        "PYTHON_ENABLE_INIT_INDEXING=1" \
        "PYTHON_ENABLE_WORKER_EXTENSIONS=1" \
        "FUNCTIONS_EXTENSION_VERSION=~4"
    
    print_success "Application settings configured"
}

# Deploy function code
deploy_function() {
    print_header "Deploying Function Code"
    
    print_info "Publishing function app..."
    func azure functionapp publish "$FUNCTION_APP_NAME" --python
    
    print_success "Function app deployed successfully"
}

# Show deployment results
show_results() {
    print_header "Deployment Complete"
    
    FUNCTION_URL="https://${FUNCTION_APP_NAME}.azurewebsites.net"
    
    print_success "MCP Server deployed successfully!"
    print_info "Function App URL: $FUNCTION_URL"
    print_info "Health Check: $FUNCTION_URL/api/health"
    print_info "MCP Endpoint: $FUNCTION_URL/api/mcp"
    
    echo
    print_info "Next Steps:"
    print_info "1. Test the health endpoint: curl $FUNCTION_URL/api/health"
    print_info "2. Configure your MCP client to use: $FUNCTION_URL/api/mcp"
    print_info "3. Monitor logs in Azure Portal or with 'func azure functionapp logstream $FUNCTION_APP_NAME'"
    print_info "4. Update function keys if using AuthLevel.FUNCTION"
    
    echo
    print_info "Useful Azure CLI commands:"
    print_info "  View logs: az functionapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
    print_info "  Get function key: az functionapp keys list --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
    print_info "  Restart function: az functionapp restart --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
}

# Main deployment flow
main() {
    print_header "Azure Functions MCP Server Deployment"
    
    check_prerequisites
    get_deployment_params
    create_resources
    configure_function_app
    deploy_function
    show_results
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Environment variables:"
        echo "  FUNCTION_APP_NAME   - Name of the Azure Function App"
        echo "  RESOURCE_GROUP      - Name of the Azure Resource Group"  
        echo "  LOCATION           - Azure region (e.g., eastus)"
        echo "  STORAGE_ACCOUNT    - Storage account name (auto-generated if not set)"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Interactive deployment"
        echo "  FUNCTION_APP_NAME=my-mcp-server $0   # With preset app name"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
