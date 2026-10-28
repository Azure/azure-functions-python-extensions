# Connector SDK Binding Samples

This folder shows how to use `azurefunctions-extensions-connectors` with
Office 365, SharePoint Online, OneDrive for Business, Microsoft Teams, Dataverse/CDS,
Planner, Salesforce, Azure DevOps, and Power Query Dataflows.

## Samples

**Setup:**
1. Create a connection for the selected connector using the `connection-setup` skill
2. Register the selected trigger using the `trigger-registration` skill
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
Demonstrates `CalendarGetOnChangedItemsV3` ("When an event is added, updated or
deleted"). Annotate handlers with `List[office365.GraphCalendarEventClientWithActionType]`
to receive SDK event items with `action_type`, `is_added`, and `is_updated` fields.
The existing `GraphCalendarEventListWithActionType` binding remains supported and
returns the same list of SDK items.

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

## SharePoint Online samples

These bindings are new in this checkout. Until a package containing them is
published, install the extension from the repository into the sample environment
instead of relying on the released package alone. Each sample includes the same
experimental connector extension-bundle configuration as the Office 365 samples.
Start Azurite for the development-storage setting before running locally.

### sharepointonline_samples_on_new_item

Demonstrates `GetOnNewItems` with `List[sharepointonline.Item]`. The same type
works for the other list-item and file-property operations in the
[trigger mapping](../docs/trigger-sdk-type-mapping.md#sharepoint-online).
Read custom columns through `item.dynamic_properties`; values retain their JSON
types and exact field names.

The sample includes separate split-on and batch handlers. Configure the trigger
to deliver to the handler you want to test; the type annotation does not set the
trigger's split-on behavior.

### sharepointonline_samples_on_deleted_item

Demonstrates `GetOnDeletedItems` with `List[sharepointonline.DeletedItem]` and
typed deletion fields such as `id` and `is_folder`. The same binding works for
`GetOnDeletedFileItems`. The sample includes split-on and batch handlers.

## OneDrive for Business sample

### onedriveforbusiness_samples_on_new_file_properties

Demonstrates `OnNewFilesV2` ("When a file is created (properties only)") with
`List[onedrive.BlobMetadata]`, imported from
`azurefunctions.extensions.connectors.onedriveforbusiness`. The same binding
works for `OnUpdatedFilesV2` ("When a file is modified (properties only)").
Each element is a generated OneDrive for Business SDK model with file metadata
such as `name`, `size`, `is_folder`, and `e_tag`.

The sample includes separate split-on and batch handlers. Configure the trigger
to deliver to the handler you want to test. The binding accepts both the source
array and a single record, returning a list in either case. Do not register the
singular `OnNewFileV2` or `OnUpdatedFileV2` content operations for these handlers.

Install the extension from this checkout until the new binding is published,
and start Azurite for the included development-storage setting. The sample uses
the same experimental connector extension bundle as the other samples.

## Microsoft Teams samples

Install the extension from this checkout until the new Teams bindings are
published. Start Azurite before using the included development-storage settings.
Register the selected operation with the matching handler; annotations do not
configure split-on behavior or choose a connector operation.

### teams_samples_polling

Contains channel-message handlers using `List[teams.ChatMessage]` and membership
handlers using `teams.OnGroupMemberChangeResponse`, which returns the SDK's list
of member dictionaries. The four handlers cover `OnNewChannelMessage`,
`OnNewChannelMessageMentioningMe`, `OnGroupMembershipAdd`, and
`OnGroupMembershipRemoval`.

### teams_samples_webhooks

Contains one handler for each of the seven webhook operations in the
[Teams mapping](../docs/trigger-sdk-type-mapping.md#microsoft-teams). Each returns
a list of SDK notification models. Chat notifications retain their `value`
reference arrays; dynamic notifications expose raw JSON through
`additional_properties`. Recording and transcript handlers receive metadata and
content URLs rather than downloaded files.

These examples log counts rather than message content, identifiers, or URLs.
The fixtures and local checks use synthetic callbacks, not captured live events.

## Dataverse (CDS) samples

These samples target the `commondataservice` connector, not the separate
`commondataserviceforapps` connector. Install the extension from this checkout
until the new bindings are published, and start Azurite for local development
storage. Register each operation separately with its matching handler.

### commondataservice_samples_webhooks

`SubscribeWebhookTrigger` uses `List[cds.RowChangeNotification]` and
`BusinessEventsTrigger` uses `List[cds.ActionEventNotification]`, imported from
`azurefunctions.extensions.connectors.commondataservice`. The handler receives
generated SDK `ObjectEntity` records; `additional_properties` holds the complete
row-change or action-event JSON, including custom columns and event metadata.
The binding names do not imply a fixed SDK notification schema. These handlers
log field counts rather than customer data.

### commondataservice_samples_legacy_polling

Shows compatibility handlers for existing `GetOnNewItems_V2`,
`GetOnUpdatedItems_V2`, and `GetOnDeletedItems_V2` registrations. All use
`List[cds.Item]`, with raw columns in `dynamic_properties`. The operations are
deprecated; use the supported webhook operations for new registrations where
available. Both split-on records and source batches return lists.

Tests use synthetic dynamic callbacks and do not prove live Dataverse delivery.
Connector trigger registration and authorization remain separate setup steps.

## Planner sample

### planner_samples_tasks

Uses `List[planner.GetTaskResponseV2]`, imported from
`azurefunctions.extensions.connectors.planner`. The four handlers demonstrate
split-on and batch callbacks for `OnNewTask_V3`, plus `OnCompleteTask_V3` and
`OnTaskAssignedToMe_V2`. Every handler receives a list of generated SDK task items.

The handlers show scalar task fields, typed `applied_categories`, and the raw
`assignments` list produced from the connector's `_assignments` wire field.
They log counts and flags rather than task titles, identifiers, or user details.
Select the intended handler when registering the trigger; annotations do not set
the operation or split-on behavior.

Install the extension from this checkout until the new binding is published,
and start Azurite for the sample's development-storage setting. The sample uses
the same experimental connector extension bundle as the other examples. Tests
and local sample checks use synthetic payloads; live Planner delivery is unverified.

## Salesforce sample

### salesforce_samples_records

Uses `List[salesforce.Item]`, imported from
`azurefunctions.extensions.connectors.salesforce`. The three handlers demonstrate
split-on and batch callbacks for `GetOnNewItems`, plus `GetOnUpdatedItems`.
Each receives a list of generated SDK items with standard and custom fields in
`dynamic_properties`, not an `ItemsList` envelope. Read fields by their exact
wire names, such as `record.dynamic_properties["Id"]` and
`record.dynamic_properties["Custom__c"]`, checking for a null property bag first.

The handlers log record and field counts rather than customer values. Select the
Salesforce object through the required `table` parameter when registering each
trigger, and point it at the intended handler. The annotation does not select the
operation or configure split-on behavior.

Install the extension from this checkout until the new binding is published,
and start Azurite for the sample's development-storage setting. The sample uses
the same experimental connector extension bundle as the other examples. Tests
and local sample checks use synthetic payloads; live Salesforce delivery is
unverified. Connection authorization and trigger registration remain separate
setup steps.

## Azure DevOps sample

### visualstudioteamservices_samples_polling

Imports the five binding types from
`azurefunctions.extensions.connectors.visualstudioteamservices`. Ten handlers
cover all nine SDK polling triggers: build completion (split-on and batch), Git
pushes, pull-request creation and closure, TFVC check-ins, and V2 work-item
assignment, creation, closure, and updates. Every handler receives a list of SDK
items, not a `VstsList...` response envelope.

**SDK prerequisite:** the published `azure-connectors==0.5.0b1` does not contain
this connector. The sample requirements pin [SDK main revision 5e93a98](https://github.com/Azure/connectors-python-sdk/commit/5e93a98c11a9eec43c4d3bbf441333b80d9ac7cb)
through a Git source dependency. Install those requirements and the extension
from this checkout until releases contain both changes. A version-only check
cannot distinguish the released SDK from the new source, which currently has
the same package version. Tests for these bindings skip when the SDK module is
absent; run them against this source revision to validate Azure DevOps support.

Register each trigger separately with `account` and `project`. Git triggers also
require `repository`; `OnWorkItemAssignedV2` also requires `team` and
`wiql__System_AssignedTo`. Select the intended handler and configure split-on in
the registration, not through its annotation. These are polling operations,
not webhook subscription actions.

Nested fixed-schema fields become SDK models. Work-item custom columns stay raw
JSON in `item.fields`, with exact names such as `System.Title`; check for null
before accessing them. The sample logs counts rather than titles, identities,
URLs, or field values. It includes the existing experimental connector bundle
and development storage settings; start Azurite before local use. Tests index
and execute the handlers with synthetic data; live delivery remains unverified.

## Dataflows sample

### dataflows_samples_refresh_completed

Uses `List[dataflows.RefreshModel]`, imported from
`azurefunctions.extensions.connectors.dataflows`, for `OnRefreshComplete`.
The polling trigger returns one refresh object. The extension supplies a list
of generated SDK refresh records to the handler, not the `DataflowModel` action
response or a `value` collection. Transport arrays and MANY deliveries are also
accepted, but the annotation does not select the operation or change the source
cardinality.

Register the trigger with `workspaceType`, `groupIdForOnRefreshComplete`, and
`dataflowIdForOnRefreshComplete`. Connection authorization and registration are
separate setup steps. The handler logs only completion and failure counts, not
dataflow names or identifiers. `Failed` and `Cancelled` refreshes are valid
callback records; dates remain nullable SDK strings.

**SDK prerequisite:** published `azure-connectors==0.5.0b1` lacks `dataflows`.
The sample requirements pin [SDK main revision 116d96f](https://github.com/Azure/connectors-python-sdk/commit/116d96fa55473217f8e50a11ee523c9b38854bf9)
as a Git source dependency. Install those requirements and the extension from
this checkout until releases contain both changes. A version-only check cannot
distinguish the old wheel from the new source, which has the same package version.
New Dataflows tests skip when the SDK module is absent; run them against this
source revision to validate the binding.

The sample keeps the existing experimental connector bundle and development
storage settings; start Azurite before local use. Tests index and execute the
handler with synthetic empty, successful, failed, and cancelled callbacks.
Live Dataflows delivery remains unverified.

## Prerequisites

-A [supported Python version for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/supported-languages?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages-by-runtime-version)
- Azure Functions Core Tools
