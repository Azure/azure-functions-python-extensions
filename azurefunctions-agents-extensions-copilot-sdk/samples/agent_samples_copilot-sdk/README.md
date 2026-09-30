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
`PermissionHandler.approve_all` is appropriate only when every configured tool
is trusted; use a restrictive handler for applications with broader tools.