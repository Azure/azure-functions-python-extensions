# Office365 Connector Samples

This folder contains samples demonstrating how to use the `azurefunctions-extensions-connectors` extension for Office365.

## Samples

**Setup:**
1. Create an Office365 connector using the `connection-setup` skill
2. Register the Office365 trigger using the `trigger-registration` skill
3. Install dependencies: `pip install -r requirements.txt`
4. Run the function app: `func start`

### office365_samples_on_new_email
Demonstrates how to handle the "On New Email" action. The ClientReceiveMessage type is the rich payload returned when a new email arrives in the mailbox.

**Features:**
- Single message processing - splitOn enabled
- Batch message processing - splitOn disabled

### office365_samples_on_flagged_email
Demonstrates how to handle the "On Flagged Email" action. The GraphClientReceiveMessage type is the rich payload returned when an email is flagged in the mailbox.

**Features:**
- Single message processing - splitOn enabled
- Batch message processing - splitOn disabled

### office365_samples_on_calendar_event
Demonstrates how to handle the "When an event is added, updated or deleted" action. The GraphCalendarEventListWithActionType type is the rich payload returned when a calendar event is added, updated, or deleted.

**Features:**
- Single event processing - splitOn enabled
- Batch event processing - splitOn disabled

### office365_samples_on_calendar_event_created
Demonstrates how to handle calendar event creation and modification actions. The GraphCalendarEventClientReceive type is the rich payload returned for the following actions:
- When a new event is created
- When an event is modified
- When an upcoming event is starting soon

**Features:**
- Single event processing - splitOn enabled
- Batch event processing - splitOn disabled

## Prerequisites

- Python 3.13 or later
- Azure Functions Core Tools
