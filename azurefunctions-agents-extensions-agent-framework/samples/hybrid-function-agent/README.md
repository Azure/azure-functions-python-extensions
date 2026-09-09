# Hybrid Function Agent

This sample keeps validation and calculations in ordinary Azure Functions code
while injecting a fresh Microsoft Agent Framework `Agent` for each invocation.
The prompt receives only the validated, minimized order projection. The HTTP
and queue bindings use the discovered `order-policy` Skill and `inventory` MCP
server. All Agent bindings receive every valid capability under the app root.

From `src/`, copy `local.settings.template.json` to `local.settings.json`, fill
in the Foundry values, start Azurite, and run `func start`.

Install the sample's `[mcp]` dependency profile and set
`INVENTORY_MCP_URL` to a trusted streamable-HTTP MCP endpoint before invoking
the HTTP route.

```bash
curl -X POST http://localhost:7071/orders/42 \
  -H "Content-Type: application/json" \
  -d '{"customer":{"id":"C-1007","loyalty_tier":"gold"},"currency":"usd","shipping":{"country":"ca","method":"overnight"},"items":[{"sku":"A-100","quantity":2,"unit_price":"24.95"}]}'
```