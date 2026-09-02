# Microsoft Agent Framework samples

- `hybrid-function-agent`: injects a fresh Agent into HTTP and queue Functions.
- `hybrid-durable-agent`: schedules Agent calls from a replay-safe orchestrator.

Both samples use raw `.agent.md` instructions and an explicit Foundry client
factory. They do not depend on the Azure Functions Agents runtime.