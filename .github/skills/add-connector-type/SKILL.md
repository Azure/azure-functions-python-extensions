---
name: add-connector-type
description: 'Add a new SDK type to the Azure Functions Connector Extension. USE WHEN: adding support for a new connector action type (e.g., OnNewEmail, OnFlaggedEmail, OnCalendarEvent), creating the SDK wrapper class, updating the converter, adding unit tests, or creating samples. NOT FOR: connection setup (use connection-setup skill), trigger registration (use trigger-registration skill).'
---

# Add New Connector Type

Checklist for adding a new SDK type to the `azurefunctions-extensions-connectors` package.

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{ConnectorName}` | The connector directory name | `office365`, `sharepoint`, `teams` |
| `{NewTypeName}` | The SDK type class name | `ClientReceiveMessage`, `GraphCalendarEventListWithActionType` |
| `{newTypeName}` | The SDK type file name (camelCase) | `clientReceiveMessage`, `graphCalendarEventListWithActionType` |
| `{action_name}` | The action name for samples folder | `on_new_email`, `on_flagged_email`, `on_calendar_event` |
| `{Action Description}` | Human-readable action description | `"On New Email"`, `"When an event is added, updated or deleted"` |

## Procedure

### Step 1: Create the SDK Type Wrapper

Do not modify the generated Azure Connectors SDK model or add a `from_json()`
method to it. Trigger callback normalization and conversion belong to this
extension because those rules vary by SDK binding type.

First add a type-specific function to the connector's `_deserialization.py`:

```python
from .._deserialization import deserialize_model, parse_payload


def deserialize_{newTypeName}(data: Datum) -> List[Azure{NewTypeName}]:
    """Deserialize the trigger callback into generated SDK models."""
    return [
        deserialize_model(Azure{NewTypeName}, item)
        for item in parse_payload(data)
    ]
```

Add explicit aliases and converters there if the callback field names or value
semantics differ from the generated model contract.

**File:** `azurefunctions-extensions-connectors/azurefunctions/extensions/connectors/{ConnectorName}/{newTypeName}.py`

```python
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import List

from azure.connectors.{ConnectorName} import {NewTypeName} as Azure{NewTypeName}
from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_{newTypeName}


class {NewTypeName}(
    ConnectorSdkType[List[Azure{NewTypeName}]],
    Azure{NewTypeName},
):
    """Azure Functions binding for {ConnectorName} trigger values."""

    _deserialize = staticmethod(deserialize_{newTypeName})
```

### Step 2: Update the Converter

**File:** `azurefunctions-extensions-connectors/azurefunctions/extensions/connectors/connectorConverter.py`

No converter change is needed. The converter recognizes every
`ConnectorSdkType` subclass and constructs the selected wrapper, which delegates
to its `_deserialize` function.

### Step 3: Update Package Exports

**File:** `azurefunctions-extensions-connectors/azurefunctions/extensions/connectors/{ConnectorName}/__init__.py`

1. Add import:
   ```python
   from .{newTypeName} import {NewTypeName}
   ```

2. Add to `__all__` list:
   ```python
   __all__ = [
       # ... existing types ...
       "{NewTypeName}",
   ]
   ```

### Step 4: Add Unit Tests

**File:** `azurefunctions-extensions-connectors/tests/test_clientreceivemessage.py`

1. Add to imports:
   ```python
   from azurefunctions.extensions.connectors.{ConnectorName} import (
       # ... existing imports ...
       {NewTypeName},
   )
   ```

2. Add test methods to `TestConnectorConverter` class:
   ```python
   def test_{newtype}_input_type_single(self):
       """Test that {NewTypeName} type annotation is accepted"""
       check_input_type = ConnectorConverter.check_input_type_annotation
       self.assertTrue(check_input_type({NewTypeName}))

   def test_{newtype}_input_type_list(self):
       """Test that List[{NewTypeName}] type annotation is accepted"""
       check_input_type = ConnectorConverter.check_input_type_annotation
       self.assertTrue(check_input_type(List[{NewTypeName}]))

   def test_{newtype}_input_none(self):
       """Test that None data returns None for {NewTypeName}"""
       result = ConnectorConverter.decode(
           data=None, trigger_metadata=None, pytype={NewTypeName}
       )
       self.assertIsNone(result)
   ```

3. Add new test class:
   ```python
   class Test{NewTypeName}(unittest.TestCase):
       def test_supports_deferred_binding_false(self):
           """Test that {NewTypeName} does not support deferred binding"""
           self.assertFalse({NewTypeName}.supports_deferred_binding())

       def test_get_sdk_type_deserializes_payload(self):
           """Test callback fields and nested values are deserialized"""
           data = Datum(
               value={"body": {"value": [{"id": "item-1"}]}},
               type="json",
           )

           values = {NewTypeName}(data=data).get_sdk_type()

           self.assertEqual(len(values), 1)
           self.assertEqual(values[0].id, "item-1")
   ```

Add focused cases for both batch and single-item envelopes, string and decoded
JSON inputs, aliases, scalar conversions, nested generated models, empty input,
malformed input, and the exact return shape required by the SDK type.

### Step 5: Create Sample Folder

**Folder:** `azurefunctions-extensions-connectors/samples/{ConnectorName}_samples_{action_name}/`

Create these files:

**function_app.py:**
```python
# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.{ConnectorName} as {ConnectorName}

app = func.FunctionApp()

"""
FOLDER: {ConnectorName}_samples_{action_name}
DESCRIPTION:
    These samples demonstrate how to handle the "{Action Description}" action
    from a {ConnectorName} Connector Trigger. The {NewTypeName} type is the
    rich payload returned for this action.
"""


@app.connector_trigger(arg_name="message")
def {ConnectorName}_{action_name}_single(
    message: List[{ConnectorName}.{NewTypeName}]
):
    """
    Single message processing - splitOn enabled
    Each event triggers an independent function invocation.
    """
    logging.info(
        f"Python {ConnectorName} Connector trigger processed a message\n"
        f"Message: {message[0]}"
    )


@app.connector_trigger(arg_name="messages")
def {ConnectorName}_{action_name}_batch(
    messages: List[{ConnectorName}.{NewTypeName}]
):
    """
    Batch message processing - splitOn disabled
    Multiple events are sent in a single function invocation.
    """
    logging.info(
        f"Python {ConnectorName} Connector trigger processed "
        f"{len(messages)} messages"
    )
    for idx, message in enumerate(messages):
        logging.info(f"Message {idx + 1}: {message}")
```

**host.json:** (copy from existing sample)
```json
{
  "version": "2.0",
  "logging": {
    "logLevel": {
      "Microsoft.Azure.Functions.Extensions.Connector": "Information"
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle.Experimental",
    "version": "[4.6.0, 5.0.0)"
  }
}
```

**local.settings.json:** (copy from existing sample)
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python"
  }
}
```

**requirements.txt:**
```
azure-functions>=2.2.0b4
azurefunctions-extensions-connectors
```

### Step 6: Update Samples README

**File:** `azurefunctions-extensions-connectors/samples/README.md`

Add a new section:
```markdown
### {ConnectorName}_samples_{action_name}
Demonstrates how to handle the "{Action Description}" action. The {NewTypeName} type is the rich payload returned for this action.

**Features:**
- Single message processing - splitOn enabled
- Batch message processing - splitOn disabled
```

## Summary

| Action | Files |
|--------|-------|
| **Modified** | `connectorConverter.py`, `{ConnectorName}/_deserialization.py`, `{ConnectorName}/__init__.py`, `tests/test_clientreceivemessage.py`, `samples/README.md` |
| **Created** | `{ConnectorName}/{newTypeName}.py`, `samples/{ConnectorName}_samples_{action_name}/` (4 files) |
