# Based on Azure Functions Python image with Core Tools
# Based on Azure Functions Python image with Core Tools
FROM mcr.microsoft.com/azure-functions/python:4-python3.11-core-tools

# Update and install dependencies
RUN apt-get update \
    && apt-get install -y \
        curl \
        npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

    # Workaround for core tools hasn't support APT install for MCP version 4.0.7332-preview1 yet.
RUN npm uninstall -g azure-functions-core-tools-4 -y
# Install Azurite globally using npm
RUN npm install -g azurite
RUN npm install -g azure-functions-core-tools@4.0.7332-preview1

# Set up Azure Functions environment variables
ENV AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Expose ports
EXPOSE 7071    

