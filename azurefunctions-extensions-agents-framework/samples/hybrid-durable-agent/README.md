# Hybrid Durable Agent

This sample keeps orchestration deterministic while scheduling markdown-defined
Agent calls through a hidden activity. Order validation, calculations, and data
minimization remain explicit application code.

From `src/`, copy `local.settings.template.json` to `local.settings.json`, fill
in the Foundry values, start Azurite, and run `func start`.

```bash
curl -X POST http://localhost:7071/orders/orchestrations \
  -H "Content-Type: application/json" \
  -d '{"order_id":"D-2048","customer":{"id":"C-1007","loyalty_tier":"gold"},"currency":"usd","shipping":{"country":"ca","method":"overnight"},"items":[{"sku":"A-100","quantity":2,"unit_price":"24.95"}]}'
```