# Office365 Connector Samples

This folder contains samples demonstrating how to use the `azurefunctions-extensions-connectors-office365` extension.

## Samples

### office365_samples_clientreceivemessage
Demonstrates how to work with ClientReceiveMessage objects from Office365 Connector Triggers.

**Features:**
- Single message processing (cardinality = one)
- Batch message processing (cardinality = many)

**Setup:**
1. Set the `OFFICE365_CONNECTION` environment variable in `local.settings.json`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the function app: `func start`

## Prerequisites

- Python 3.13 or later
- Azure Functions Core Tools
- Office365 account with connector configuration
