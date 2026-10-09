# Durable GitHub Copilot SDK Agent binding sample

This sample schedules Copilot SDK Agent calls as replay-safe Durable activities.
Install `requirements.txt`, configure the settings from
`local.settings.template.json`, pre-provision the native runtime with
`python -m copilot download-runtime`, and run `func start`.
Configure `COPILOT_GITHUB_TOKEN`, `COPILOT_BASE_DIRECTORY`, and `COPILOT_MODEL`
using the exact names shown in `local.settings.template.json`. Set
`COPILOT_BASE_DIRECTORY` to an isolated writable directory for the app's runtime
state; use separate directories when hosting multiple tenants.
The extension creates one client lazily and reuses it for the lifetime of the
Python worker while creating a fresh session for each activity invocation.
`AgentFunctionApp()` defaults to `PermissionHandler.approve_all`; pass a
restrictive handler unless every configured tool is trusted.

The orchestrator only schedules `context.call_agent(...)`; model and tool work
runs in the extension's hidden activity.