# GitHub Copilot SDK Agent binding sample

This sample injects a fresh `CopilotSession` into HTTP and queue-triggered
Functions. Copy `local.settings.template.json` to `local.settings.json`, replace
the placeholder settings, install `requirements.txt`, and pre-provision the
native runtime with:

```text
python -m copilot download-runtime
```

Run the app with `func start`. The sample uses `mode="empty"`, disables SDK
telemetry, and exposes only the discovered Skill and remote inventory MCP tool.
Set `COPILOT_BASE_DIRECTORY` to an isolated writable directory for the app's
runtime state; use separate directories when hosting multiple tenants.
`PermissionHandler.approve_all` is appropriate only when every configured tool
is trusted; use a restrictive handler for applications with broader tools.