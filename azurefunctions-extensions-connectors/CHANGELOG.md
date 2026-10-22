# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Add the Salesforce `Item` SDK binding for record-created and record-updated
	triggers, preserving standard and custom fields, with a sample.
- Add the Planner `GetTaskResponseV2` SDK binding for new, completed, and assigned
	task triggers, with typed categories, connector assignment arrays, and a sample.
- Add Dataverse/CDS `Item`, `RowChangeNotification`, and `ActionEventNotification`
	bindings that preserve dynamic polling and webhook fields, with samples.
- Add Microsoft Teams SDK bindings for channel messages, membership changes,
  and seven webhook notification types, with polling and webhook samples.
- Add the OneDrive for Business `BlobMetadata` SDK binding for file-property
	triggers, with raw-array and Poll MANY support and a sample.
- Add SharePoint Online `Item` and `DeletedItem` SDK bindings for list-item,
  file-property, and deletion triggers, with dynamic-column preservation and samples.
- Add the `GraphCalendarEventClientWithActionType` Office 365 binding for changed
	calendar events. The existing `GraphCalendarEventListWithActionType` binding
	remains supported with the same list-returning behavior.

### Fixed
- Deserialize nested SDK models when their annotations also accept mappings,
  preserving typed Office 365 attachments with newer generated SDKs.

## [1.0.0b1] - 2026-05-11

### Added
- Initial beta release of azurefunctions-extensions-connectors-office365
- Support for Office365 Connector Triggers
- ClientReceiveMessage type support for single message processing
- List[ClientReceiveMessage] type support for batch message processing
- Integration with azure-connectors SDK
- Support for both model_binding_data and collection_model_binding_data cardinalities
