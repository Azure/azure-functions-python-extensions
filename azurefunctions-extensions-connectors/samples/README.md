# Office365 Connector Samples

This folder contains samples demonstrating how to use the `azurefunctions-extensions-connectors` extension for Office365.

## Samples

### office365_samples_clientreceivemessage
Demonstrates how to work with ClientReceiveMessage objects from Office365 Connector Triggers.

**Features:**
- Single message processing - splitOn enabled
- Batch message processing - splitOn disabled

**Setup:**
1. Create an Office365 connector using the `connection-setup` skill
2. Register the Office365 trigger using the `trigger-registration` skill
3. Install dependencies: `pip install -r requirements.txt`
4. Run the function app: `func start`

## Prerequisites

- Python 3.13 or later
- Azure Functions Core Tools
