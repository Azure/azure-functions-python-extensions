# Azure Functions Extensions Connectors library for Python

This library binds Office 365, SharePoint Online, OneDrive for Business, Teams,
Dataverse/CDS, Planner, Salesforce, Azure DevOps, and Dataflows connector trigger
payloads to model types from the Azure Connectors SDK in Python Function Apps.

Supported connectors:

* Office 365 (Outlook)
* SharePoint Online
* OneDrive for Business (file properties)
* Microsoft Teams
* Dataverse (the `commondataservice` connector)
* Planner
* Salesforce
* Azure DevOps (requires an SDK build containing `visualstudioteamservices`)
* Power Query Dataflows (requires an SDK build containing `dataflows`)

[Source code](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-connectors)
| [Package (PyPI)](https://pypi.org/project/azurefunctions-extensions-connectors/)
| [Samples](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-connectors/samples)


## Getting started

### Prerequisites
* A supported Python version is required. For more details, see the [Python Functions version support policy](https://learn.microsoft.com/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).

* You must have an [Azure subscription](https://azure.microsoft.com/free/) and an account with access to the selected connector.

### Install the package
Install the connector SDK type-binding extension with pip:

```bash
pip install azurefunctions-extensions-connectors
```

### Bind to the SDK-type
The Azure Functions Extensions Connectors Office365 library for Python allows you to create a function app with an Office365 Connector Trigger and define the type as a ClientReceiveMessage or List[ClientReceiveMessage]. Instead of receiving raw data, when the function is executed, the type returned will be the defined SDK-type and have all of the methods available from the `azure-connectors` SDK.

SharePoint Online handlers import `Item` or `DeletedItem` from
`azurefunctions.extensions.connectors.sharepointonline`. Each binding returns
a list of generated SDK items. See the [SharePoint samples](samples/README.md#sharepoint-online-samples).

OneDrive for Business handlers import `BlobMetadata` from
`azurefunctions.extensions.connectors.onedriveforbusiness`. The binding returns
a list of generated `azure.connectors.onedriveforbusiness.BlobMetadata` models.
See the [OneDrive sample](samples/README.md#onedrive-for-business-sample).

Teams handlers import their binding types from
`azurefunctions.extensions.connectors.teams`. Polling and webhook bindings return
lists, but chat webhook models keep their own notification-reference collections.
See the [Teams samples](samples/README.md#microsoft-teams-samples).

Dataverse/CDS handlers import `Item`, `RowChangeNotification`, or
`ActionEventNotification` from `azurefunctions.extensions.connectors.commondataservice`.
See the [CDS samples](samples/README.md#dataverse-cds-samples) for the different
polling and webhook return contracts.

Planner handlers import `GetTaskResponseV2` from
`azurefunctions.extensions.connectors.planner`. The binding returns generated SDK
task items, not a list-response envelope. See the [Planner sample](samples/README.md#planner-sample).

Salesforce handlers import `Item` from
`azurefunctions.extensions.connectors.salesforce`. The binding returns generated
SDK items with the selected object's fields in `dynamic_properties`. See the
[Salesforce sample](samples/README.md#salesforce-sample).

Azure DevOps handlers import `BuildResult`, `GitPush`, `GitPullRequest`,
`TfvcChangeset`, or `TriggerWorkItemResponse` from
`azurefunctions.extensions.connectors.visualstudioteamservices`. See the
[Azure DevOps sample](samples/README.md#azure-devops-sample) for the SDK source
prerequisite; the published `azure-connectors==0.5.0b1` lacks this connector.

Dataflows handlers import `RefreshModel` from
`azurefunctions.extensions.connectors.dataflows`. The binding returns SDK refresh
records for `OnRefreshComplete`. See the
[Dataflows sample](samples/README.md#dataflows-sample) for its SDK source prerequisite.

## Key concepts

### ClientReceiveMessage
The `ClientReceiveMessage` type represents a message received from an Office365 connector. The extension automatically parses the incoming JSON payload and converts it into typed ClientReceiveMessage objects from the `azure-connectors` SDK.

### Supported Office 365 trigger types

Import binding types from `azurefunctions.extensions.connectors.office365`, not
directly from the generated SDK module. The binding converts the callback into
instances of the corresponding `azure.connectors.office365` model.

| Trigger operations | Binding item type |
| --- | --- |
| `OnNewEmailV3`, `OnFlaggedEmailV4`, `OnNewMentionMeEmailV3`, `SharedMailboxOnNewEmailV2` | `GraphClientReceiveMessage` |
| `CalendarGetOnNewItemsV3`, `CalendarGetOnUpdatedItemsV3`, `OnUpcomingEventsV3` | `GraphCalendarEventClientReceive` |
| `CalendarGetOnChangedItemsV3` | `GraphCalendarEventClientWithActionType` |

`ClientReceiveMessage` remains supported for legacy email handlers. The existing
`GraphCalendarEventListWithActionType` binding also remains supported; it returns
the same list of changed-calendar SDK items as `GraphCalendarEventClientWithActionType`.
No existing binding name or return shape has changed.

### Supported SharePoint Online trigger types

| Trigger operations | Binding item type |
| --- | --- |
| `GetOnNewItems`, `GetOnUpdatedItems`, `GetOnChangedItems`, `GetOnNewFileItems`, `GetOnUpdatedFileItems`, `GetOnUpdatedFileClassifiedTimes`, `GetOnNewItemsFromForm`, `GetOnRecurrenceDigest` | `sharepointonline.Item` |
| `GetOnDeletedItems`, `GetOnDeletedFileItems` | `sharepointonline.DeletedItem` |

`Item.dynamic_properties` preserves raw JSON columns, including strings, numbers,
booleans, nulls, arrays, and nested objects. Access columns by their exact wire
names, such as `item.dynamic_properties["ID"]`. No fixed model can describe every
list's custom columns. If an input record consists solely of the SDK's
`dynamicProperties` object, the binding uses that object as the property bag.
Records with other columns retain every top-level key, including a column named
`dynamicProperties`, without flattening or merging it.

`DeletedItem` exposes `id`, `name`, `file_name_with_extension`,
`deleted_by_user_name`, `time_deleted`, and `is_folder`. The binding uses the SDK's
wire-name metadata, including the uppercase `ID` field.

Both types support single records, callback body envelopes, source batches, and
Functions Poll MANY collections. Malformed batch members raise `ValueError`
rather than being dropped. The legacy binary-content triggers `OnNewFile` and
`OnUpdatedFile` are not covered by these two model bindings.

### Supported OneDrive for Business trigger types

| Trigger operations | Binding item type |
| --- | --- |
| `OnNewFilesV2`, `OnUpdatedFilesV2` (properties only) | `onedriveforbusiness.BlobMetadata` |

The binding exposes all twelve generated SDK metadata fields: `id`, `name`,
`name_no_ext`, `display_name`, `path`, `last_modified`, `size`, `media_type`,
`is_folder`, `e_tag`, `file_locator`, and `last_modified_by`. It maps SDK wire
names such as `NameNoExt`, `ETag`, and `LastModifiedBy`, including SDK versions
that omit field metadata. Date/time and ETag fields retain the SDK's string types.

Supported shapes include the trigger's raw source array, a split-on record,
callback `body` envelopes, `value` collections, and Functions Poll MANY
collections. Empty source batches return empty lists. Malformed batch members
raise `ValueError` instead of being silently dropped.

The singular operations `OnNewFileV2` and `OnUpdatedFileV2` return binary file
content, not metadata, and have no generated SDK callback model. They are not
covered by this binding. Encoded `$content` envelopes are rejected rather than
turned into empty metadata models. This is the OneDrive for Business model, not
the Azure Blob Storage or personal OneDrive model with the same class name.

### Supported Microsoft Teams trigger types

Import these binding types from `azurefunctions.extensions.connectors.teams`.

| Trigger operations | Binding type |
| --- | --- |
| `OnNewChannelMessage`, `OnNewChannelMessageMentioningMe` | `ChatMessage` |
| `OnGroupMembershipAdd`, `OnGroupMembershipRemoval` | `OnGroupMemberChangeResponse` |
| `WebhookChatMessageTrigger` | `ChatMessageWebhookResponseSchema` |
| `WebhookNewMessageTrigger` | `DynamicNewMessageWebhookTriggerResponseSchema` |
| `WebhookAtMentionTrigger` | `DynamicAtMentionWebhookTriggerResponseSchema` |
| `WebhookKeywordTrigger` | `DynamicKeywordWebhookTriggerResponseSchema` |
| `WebhookMessageReactionTrigger` | `MessageReactionWebhookResponseSchema` |
| `RecordingTrigger` | `RecordingWebhookResponseSchema` |
| `TranscriptTrigger` | `TranscriptWebhookResponseSchema` |

`ChatMessage` returns generated message models with nested body, sender,
attachment, mention, and reaction dictionaries. `OnGroupMemberChangeResponse`
returns a list of dictionaries, matching the SDK's alias rather than inventing a
fixed member model.

Webhook bindings return a list of generated notification models. In particular,
`ChatMessageWebhookResponseSchema.value` contains message references, not full
`ChatMessage` records. The binding preserves that collection inside each model,
including empty or null collections. Dynamic new-message, mention, and keyword
models retain the whole JSON notification in `additional_properties`, including
its nested objects and fields named `value` or `additional_properties`.

Recording and transcript notifications contain metadata and content URLs, not
downloaded content. Their distinct `id` and `@odata.id` values map to `id` and
`id_2`; `meeting_organizer` becomes a generated `TeamsIdentitySet` containing raw
identity dictionaries.

Teams polling bindings extract source `value` arrays; webhook bindings do not.
All support raw object arrays, JSON text or bytes, and Poll MANY collections.
An object whose only key is `body` is treated as the callback envelope; a
notification's own body field remains data when other record fields are present.
Malformed batches raise `ValueError` rather than dropping members.

### Supported Dataverse/CDS trigger types

These bindings target the `commondataservice` connector. They do not register
triggers, replace connection setup, or provide an alias for the distinct
`commondataserviceforapps` connector.

| Trigger operations | Extension binding type | Returned SDK models |
| --- | --- | --- |
| `SubscribeWebhookTrigger` | `RowChangeNotification` | `list[azure.connectors.commondataservice.ObjectEntity]` |
| `BusinessEventsTrigger` | `ActionEventNotification` | `list[azure.connectors.commondataservice.ObjectEntity]` |
| `GetOnDeletedItems_V2`, `GetOnNewItems_V2`, `GetOnUpdatedItems_V2` (legacy polling) | `Item` | `list[azure.connectors.commondataservice.Item]` |

`RowChangeNotification` and `ActionEventNotification` are extension binding
names, not new generated SDK models. Both preserve each complete webhook
record in `ObjectEntity.additional_properties`. Read table columns, action
parameters, and event metadata by their exact JSON keys; no fixed row or action
schema is inferred. Fields named `value`, `schema`, `dynamicProperties`, or
`additional_properties` remain data, not envelopes to flatten or unwrap.

The generated `WebhookNotificationContent` classes expose a `schema` field for
dynamic schema metadata. They are not the return contract for these bindings;
converting actual notifications into those wrappers would discard their fields.

Legacy `Item` preserves columns in `dynamic_properties`, including nulls,
booleans, numbers, arrays, nested objects, and OData keys. A record consisting
only of `dynamicProperties` or `dynamic_properties` supplies that bag directly.
Other records retain their entire top-level structure. Polling bindings extract
`value` only when the other envelope fields are OData metadata; webhook bindings
never extract `value`.

All three bindings support JSON objects or arrays, callback envelopes containing
only `body`, and transport collections. A record's own `body` field stays data
when other record fields are present. Malformed batch members raise `ValueError`.
The legacy operations are deprecated and exist here for compatibility, not as a
recommendation for new registrations. Dynamic callback tests are synthetic;
live Dataverse delivery has not been tested.

### Supported Planner trigger types

| Trigger operations | Binding item type |
| --- | --- |
| `OnCompleteTask_V3`, `OnNewTask_V3`, `OnTaskAssignedToMe_V2` | `planner.GetTaskResponseV2` |

All three operations are polling triggers. The binding returns a list of
`azure.connectors.planner.GetTaskResponseV2` items. It extracts tasks from the
SDK's `ListTasksResponse` envelope without returning that envelope, fetching next
pages, or using the different V3 task model for action responses.

The fourteen task fields retain the SDK's types. `applied_categories` becomes a
generated `AppliedCategories` model with all 25 nullable category flags.
`created_by` and assignment entries remain raw JSON dictionaries, preserving
nested fields and nulls. Dates stay strings, while false flags, zero counts,
and empty assignment arrays remain unchanged.

The connector's `_assignments` array maps to `assignments` and takes precedence
over a simultaneous `assignments` field. The latter is accepted as a Python-field
fallback only when `_assignments` is absent. Native Microsoft Graph assignment
objects are not this connector's array contract; invalid assignment shapes raise
`ValueError` instead of being converted into a different model.

Supported callback shapes include single task records, source arrays, callback
`body` envelopes, `value` batches with OData metadata, and Poll MANY collections.
Malformed batch members raise `ValueError` rather than being silently dropped.
An object containing only `body` is treated as a callback envelope; extra task
fields named `body` or `value` cannot hide the task's SDK fields.

### Supported Salesforce trigger types

| Trigger operations | Binding item type |
| --- | --- |
| `GetOnNewItems`, `GetOnUpdatedItems` | `salesforce.Item` |

Both operations are polling triggers with a required `table` parameter. The
binding returns a list of `azure.connectors.salesforce.Item` models, not an
`ItemsList` envelope. It does not fetch continuation pages or register triggers.

Each item's `dynamic_properties` preserves standard and custom fields with their
exact wire names, such as `Id` and `Custom__c`. Nested `attributes`, relationships,
arrays, nulls, false flags, zero values, and empty strings remain raw JSON. The
binding does not guess fixed fields or convert dynamic values into empty SDK
objects. A record containing only `dynamicProperties` or `dynamic_properties`
supplies that object or null as the bag. Records with other fields keep their
entire top-level structure without merging a similarly named field.

Supported inputs include split-on records, source arrays, sole-`body` callback
envelopes, `value` batches with only OData metadata alongside them, and Poll MANY
collections. Records with other fields named `value` or `body` retain those fields.
Malformed batch members raise `ValueError` instead of being silently dropped.
Tests use synthetic callbacks; live Salesforce delivery remains unverified.

### Supported Azure DevOps trigger types

| Trigger operations | Binding item type |
| --- | --- |
| `OnBuildCompleted` | `visualstudioteamservices.BuildResult` |
| `OnGitPush` | `visualstudioteamservices.GitPush` |
| `OnGitPullCreated`, `OnGitPullClosed` | `visualstudioteamservices.GitPullRequest` |
| `OnTfvcCheckIn` | `visualstudioteamservices.TfvcChangeset` |
| `OnWorkItemAssignedV2`, `OnWorkItemClosedV2`, `OnWorkItemCreatedV2`, `OnWorkItemUpdatedV2` | `visualstudioteamservices.TriggerWorkItemResponse` |

These are the nine GET polling operations in the referenced SDK's trigger
registry, not separate webhook subscription actions. Each binding returns a
list of generated SDK items rather than a `VstsList...` response envelope.
Build users, definitions, and `_links.web`; Git repositories, identities, ref
updates, reviewers, commits, and options; and TFVC author identities become
their corresponding generated SDK models. Dates and URLs keep SDK string types.

`TriggerWorkItemResponse` exposes `id`, `rev`, `url`, and `fields`. Its `fields`
dictionary keeps exact dotted names such as `System.Title` and `Custom.Flag`,
nested JSON, nulls, false flags, zero values, and empty strings. The binding does
not invent a fixed work-item schema or use the different action-response model.
A missing or null `fields` value stays null; other non-object values raise
`ValueError`.

All five bindings accept single records, arrays, sole-`body` callback envelopes,
OData `value` batches, and Poll MANY transport collections. They preserve order,
reject malformed batch members, and do not fetch continuation pages. Type
annotations do not register an operation or choose split-on behavior. Legacy
work-item operations without `V2` are not part of this inventory.

The implementation references [SDK main revision 5e93a98](https://github.com/Azure/connectors-python-sdk/blob/5e93a98c11a9eec43c4d3bbf441333b80d9ac7cb/src/azure/connectors/visualstudioteamservices.py).
Until a release contains this module, install that SDK source revision or a
later build containing it. The sample requirements pin the source. Importing
this namespace with an older SDK raises an actionable `ImportError`; other
connector namespaces do not import it. The shared SDK dependency floor remains
unchanged for existing connectors. Tests use synthetic callbacks, not live
Azure DevOps delivery.

### Supported Dataflows trigger type

| Trigger operation | Binding item type |
| --- | --- |
| `OnRefreshComplete` | `dataflows.RefreshModel` |

This Power Query Dataflows operation is a GET polling trigger. Its callback is
one `azure.connectors.dataflows.RefreshModel` record, not a `value` collection.
The binding returns a list containing that SDK record, following the extension's
list-returning convention. It does not use `DataflowModel`, which describes the
separate refresh action response, or fetch related dataflows or continuation pages.

The six nullable string fields are `dataflow_id`, `dataflow_name`, `refresh_type`,
`start_time`, `end_time`, and `status`. The binding maps the SDK wire names such
as `dataflowId` and `refreshType`. Dates remain strings, nulls and empty strings
stay distinct, and `Failed` or `Cancelled` statuses remain callback data rather
than raising conversion errors. No fixed status enum is imposed.

Supported inputs include a direct record, a sole-`body` callback envelope,
JSON text or bytes, arrays of transport records, and Functions MANY collections.
Transport arrays do not change the connector's single-record source schema.
Malformed members and value-only collection envelopes raise `ValueError` rather
than producing partial results or empty SDK models.

The binding references [SDK main revision 116d96f](https://github.com/Azure/connectors-python-sdk/blob/116d96fa55473217f8e50a11ee523c9b38854bf9/src/azure/connectors/dataflows.py).
The published `azure-connectors==0.5.0b1` lacks this module. Install the pinned
SDK source from the sample requirements or a later build containing it.
Importing only this namespace with an older SDK raises an actionable
`ImportError`; existing connector namespaces remain available. Synthetic tests
cover conversion and sample execution; live Dataflows delivery remains unverified.

### Cardinality
All supported SDK bindings return lists for single-item callbacks
and source batches where the connector supports them. For example, use
`List[office365.GraphCalendarEventClientWithActionType]` for changed events.

Both direct binding annotations and `List[BindingType]` annotations are accepted;
the annotation does not select the return shape or configure trigger cardinality.
For Functions Poll MANY delivery, the bindings flatten transport events and
polling source batches into one list. Teams chat webhooks keep each notification
envelope's reference collection inside the generated model rather than flattening it.

## Examples

### Office365 Connector Trigger - Single Message

```python
import logging
import azure.functions as func
import azurefunctions.extensions.connectors.office365 as office365

app = func.FunctionApp()

@app.connector_trigger(arg_name="message", connection="OFFICE365_CONNECTION")
def office365_trigger_single(message: office365.ClientReceiveMessage):
    logging.info(f"Received Office365 message: {message}")
    # Access message properties using the Azure Connectors SDK methods
```

### Office365 Connector Trigger - Batch Messages

```python
import logging
from typing import List
import azure.functions as func
import azurefunctions.extensions.connectors.office365 as office365

app = func.FunctionApp()

@app.connector_trigger(arg_name="messages", connection="OFFICE365_CONNECTION")
def office365_trigger_batch(messages: List[office365.ClientReceiveMessage]):
    logging.info(f"Received {len(messages)} Office365 messages")
    for message in messages:
        logging.info(f"Processing message: {message}")
        # Access message properties using the Azure Connectors SDK methods
```

## Troubleshooting

### General
Connector SDK binding errors are raised as `ValueError` exceptions with descriptive messages.

### Logging
Enable verbose logging in your function app to see detailed information about message processing:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Next steps

### More sample code
Get started with the [connector SDK binding samples](samples/README.md).

## Contributing
This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
