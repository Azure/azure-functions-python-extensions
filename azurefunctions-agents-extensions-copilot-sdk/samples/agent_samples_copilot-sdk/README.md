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
Configure `COPILOT_GITHUB_TOKEN`, `COPILOT_BASE_DIRECTORY`, and `COPILOT_MODEL`
using the exact names shown in `local.settings.template.json`. Set
`COPILOT_BASE_DIRECTORY` to an isolated writable directory for the app's runtime
state; use separate directories when hosting multiple tenants.
The extension creates one client lazily and reuses it for the lifetime of the
Python worker while creating a fresh session for each invocation.
`AgentFunctionApp()` defaults to `PermissionHandler.approve_all`, which is
appropriate only when every configured tool is trusted. Pass a restrictive
handler for applications with broader tools.

## Compare with the direct Copilot SDK

[`function_app.py`](function_app.py) uses `AgentFunctionApp` and the
`@app.markdown_agent` decorator to discover the Agent instructions, Skill, and
MCP server and inject a configured `CopilotSession` into each invocation.

[`direct_sdk.py`](direct_sdk.py) performs the same order-readiness assessment
without the binding. It shows the client authentication, instruction loading,
Skill and MCP wiring, tool allowlist, session security options, lifecycle
management, and response validation that application code must otherwise own.

The standalone script reads settings from its process environment; unlike Core
Tools, it does not load `local.settings.json`. Export the same `COPILOT_*` and
`INVENTORY_MCP_URL` values described above, then run:

```text
python direct_sdk.py
```
