# Hybrid Function Agent

This sample keeps validation and calculations in ordinary Azure Functions code
while injecting a fresh Microsoft Agent Framework `Agent` for each invocation.
The prompt receives only the validated, minimized order projection.

From `src/`, copy `local.settings.template.json` to `local.settings.json`, fill
in the Foundry values, start Azurite, and run `func start`.

```bash
curl -X POST http://localhost:7071/orders/42 \
  -H "Content-Type: application/json" \
  -d '{"customer":{"id":"C-1007","loyalty_tier":"gold"},"currency":"usd","shipping":{"country":"ca","method":"overnight"},"items":[{"sku":"A-100","quantity":2,"unit_price":"24.95"}]}'
```