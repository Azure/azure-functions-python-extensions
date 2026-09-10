---
page_type: sample
languages:
    - python
products:
    - azure
    - azure-functions
    - azure-functions-extensions
    - microsoft-foundry
    - azurefunctions-agents-extensions-agent-framework
urlFragment: extension-agent-framework-samples
---

# Azure Functions Microsoft Agent Framework Extension for Python samples

These code samples show common scenarios for using Microsoft Agent Framework
Agents in Python Function Apps. All samples use raw `.agent.md` instructions.
The first two use explicit Microsoft Foundry client factories, while the local
examples use deterministic clients without model credentials.

* [agent_samples_agent-framework](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-agents-extensions-agent-framework/samples/agent_samples_agent-framework) - Examples for adding an Agent to an existing Function App:
    * Inject a fresh Agent into HTTP and queue-triggered Functions
    * Discover app-wide Skills and MCP servers
    * Keep validation and deterministic processing in application code

* [agent_samples_agent-framework_durable](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-agents-extensions-agent-framework/samples/agent_samples_agent-framework_durable) - Examples for using Agents in Durable Functions:
    * Schedule Agent calls from a replay-safe orchestrator
    * Inject a durable markdown agent and run two turns in one shared session
    * Combine deterministic activity output with model-generated results

* [Endpoint-only local agent](lazy-owned-dafx/README.md) uses `durable=True`
    discovery and the generated DAFX HTTP endpoint. No handwritten handlers or
    model credentials are needed.
* [Durable markdown binding](durable-markdown-binding/README.md) injects a proxy
    into a generator orchestrator, runs two turns in one session, and includes an
    HTTP starter. It also uses a deterministic local client.
- [Durable YAML workflows](durable-yaml-workflow/README.md) enables
    `durable=True, workflows=True` for shared state, a Markdown agent activity,
    and a separate approval question. No handwritten handlers are needed.
    Requires Python 3.13 and the `[durable,workflows]` extras.

## Prerequisites

* Python 3.13 or later is required. For more details, see the [Python Functions version support policy](https://learn.microsoft.com/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).
* The Foundry samples require an [Azure subscription](https://azure.microsoft.com/free/), a Microsoft Foundry project, and a deployed model.
* You must have [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite) or an Azure Storage account for Functions host storage, queue triggers, and Durable Functions state.
* The non-Durable sample also requires a trusted streamable-HTTP MCP endpoint.
* Durable samples require the prototype's SDK 2-compatible DAFX dependencies
    and a compatible Functions host/backend to run under Core Tools. They do not
    depend on the Azure Functions Agents runtime. Follow the
    [prototype setup steps](lazy-owned-dafx/README.md#install-and-verify) first.

## Setup

1. Install [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?tabs=windows%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-python).
2. Clone or download this sample repository.
3. Open the sample folder in Visual Studio Code or your IDE of choice.
4. For a Foundry sample, sign in with an identity authorized to use your Microsoft Foundry project. For example:

```bash
az login
```

## Running the samples

The following steps apply to the Foundry samples. For the local-client examples,
follow the linked README for its installation steps, settings, and HTTP requests.

1. Open a terminal window and `cd` to the directory containing the sample you want to run.
2. Create `local.settings.json` from `local.settings.template.json` and replace the placeholders with your Foundry project and model settings.
3. Create and activate a virtual environment.
4. Install the required dependencies:

```bash
python -m pip install -r requirements.txt
```

5. Start Azurite or configure `AzureWebJobsStorage` to use an Azure Storage account.
6. Start the Functions runtime:

```bash
func start
```

7. Follow the selected sample's README to invoke its HTTP, queue, or Durable Functions and inspect the output.

## Next steps

Visit the [Agent Framework extension documentation](../README.md) to learn more
about Agent bindings, automatic Skill and MCP discovery, and replay-safe Durable
Agent calls. For the underlying Agent APIs, see the
[Microsoft Agent Framework documentation](https://learn.microsoft.com/agent-framework/).
