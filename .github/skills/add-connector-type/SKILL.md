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

**File:** `azurefunctions-extensions-connectors/azurefunctions/extensions/connectors/{ConnectorName}/{newTypeName}.py`

```python
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import List

from azure.connectors.{ConnectorName} import {NewTypeName} as Azure{NewTypeName}
from azurefunctions.extensions.base import Datum, SdkType


class {NewTypeName}(SdkType, Azure{NewTypeName}):
    def __init__(self, *, data: Datum) -> None:
        self._json_payload = data

    @classmethod
    def supports_deferred_binding(cls) -> bool:
        """{ConnectorName} connector does not support deferred binding."""
        return False

    def get_sdk_type(self) -> List[Azure{NewTypeName}]:
        if not self._json_payload:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"No data provided."
            )
        try:
            messages = Azure{NewTypeName}.from_json(self._json_payload)
            return messages
        except Exception as e:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"Exception: {e}"
            ) from e
```

### Step 2: Update the Converter

**File:** `azurefunctions-extensions-connectors/azurefunctions/extensions/connectors/connectorConverter.py`

1. Add import at the top:
   ```python
   from .{ConnectorName}.{newTypeName} import {NewTypeName}
   ```

2. Add to `SUPPORTED_SDK_TYPES` tuple:
   ```python
   SUPPORTED_SDK_TYPES = (
       # ... existing types ...
       {NewTypeName}
   )
   ```

3. Add `elif` branch in `decode()` method:
   ```python
   elif sdk_type == {NewTypeName}:
       return {NewTypeName}(data=data).get_sdk_type()
   ```

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
   ```

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
| **Modified** | `connectorConverter.py`, `{ConnectorName}/__init__.py`, `tests/test_clientreceivemessage.py`, `samples/README.md` |
| **Created** | `{ConnectorName}/{newTypeName}.py`, `samples/{ConnectorName}_samples_{action_name}/` (4 files) |
