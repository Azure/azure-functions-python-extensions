# Durable GitHub Copilot SDK Agent binding sample

This sample schedules Copilot SDK Agent calls as replay-safe Durable activities.
Install `requirements.txt`, configure the settings from
`local.settings.template.json`, pre-provision the native runtime with
`python -m copilot download-runtime`, and run `func start`.
Set `COPILOT_BASE_DIRECTORY` to an isolated writable directory for the app's
runtime state; use separate directories when hosting multiple tenants.

The orchestrator only schedules `context.call_agent(...)`; model and tool work
runs in the extension's hidden activity.