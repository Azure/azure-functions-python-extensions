# Durable GitHub Copilot SDK Agent binding sample

This sample schedules Copilot SDK Agent calls as replay-safe Durable activities.
Install `requirements.txt`, configure the settings from
`local.settings.template.json`, pre-provision the native runtime with
`python -m copilot download-runtime`, and run `func start`.

The orchestrator only schedules `context.call_agent(...)`; model and tool work
runs in the extension's hidden activity.