#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
import unittest
from enum import Enum
from typing import Optional

from azure.eventhub import EventData
from azurefunctions.extensions.base import Datum

from azurefunctions.extensions.bindings.blob import BlobClient, BlobClientConverter
from azurefunctions.extensions.bindings.eventhub import EventHubData, EventHubDataConverter


# Mock classes for testing
class MockMBD:
    def __init__(self, version: str, source: str, content_type: str, content: str):
        self.version = version
        self.source = source
        self.content_type = content_type
        self.content = content


class MockBindingDirection(Enum):
    IN = 0
    OUT = 1
    INOUT = 2


class MockBinding:
    def __init__(
        self,
        name: str,
        direction: MockBindingDirection,
        data_type=None,
        type: Optional[str] = None,
    ):  # NoQa
        self.type = type
        self.name = name
        self._direction = direction
        self._data_type = data_type
        self._dict = {
            "direction": self._direction,
            "dataType": self._data_type,
            "type": self.type,
        }

    @property
    def data_type(self) -> Optional[int]:
        return self._data_type.value if self._data_type else None

    @property
    def direction(self) -> int:
        return self._direction.value


class MockParamTypeInfo:
    def __init__(self, binding_name: str, pytype: type):
        self.binding_name = binding_name
        self.pytype = pytype


class MockFunction:
    def __init__(self, bindings: MockBinding):
        self._bindings = bindings


class TestBlobClient(unittest.TestCase):
    def test_input_type(self):
        check_input_type = EventHubDataConverter.check_input_type_annotation
        self.assertTrue(check_input_type(EventHubData))
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(bytearray))

    def test_input_none(self):
        result = EventHubDataConverter.decode(
            data=None, trigger_metadata=None, pytype=EventHubData
        )
        self.assertIsNone(result)

        datum: Datum = Datum(value=b"string_content", type=None)
        result = EventHubDataConverter.decode(
            data=datum, trigger_metadata=None, pytype=BlobClient
        )
        self.assertIsNone(result)

    def test_input_incorrect_type(self):
        datum: Datum = Datum(value=b"string_content", type="bytearray")
        with self.assertRaises(ValueError):
            EventHubDataConverter.decode(
                data=datum, trigger_metadata=None, pytype=EventHubData
            )

    def test_input_empty(self):
        datum: Datum = Datum(value={}, type="model_binding_data")
        result: EventHubData = EventHubDataConverter.decode(
            data=datum, trigger_metadata=None, pytype=EventHubData
        )
        self.assertIsNone(result)

    def test_input_populated(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content = b'\x00Sr\xc1\x8e\x08\xa3\x1bx-opt-sequence-number-epochT\xff\xa3\x15x-opt-sequence-numberU\x04\xa3\x0cx-opt-offset\x81\x00\x00\x00\x01\x00\x00\x010\xa3\x13x-opt-enqueued-time\x00\xa3\x1dcom.microsoft:datetime-offset\x81\x08\xddW\x05\xc3Q\xcf\x10\x00St\xc1I\x02\xa1\rDiagnostic-Id\xa1700-bdc3fde4889b4e907e0c9dcb46ff8d92-21f637af293ef13b-00\x00Su\xa0\x08message1'
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: EventHubData = EventHubDataConverter.decode(
            data=datum, trigger_metadata=None, pytype=EventHubData
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, EventData)

        sdk_result = EventHubData(data=datum.value).get_sdk_type()

        self.assertIsNotNone(sdk_result)
        self.assertIsInstance(sdk_result, EventData)

    def test_invalid_input_populated(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content = b'\x00Sr\xc1\x8e\x08\xa3\x1bx-opt-sequence-number-epochT\xff\xa3\x15x-opt-sequence-numberU\x04\xa3\x0cx-opt-offset\x81\x00\x00\x00\x01\x00\x00\x010\xa3\x13x-opt-enqueued-time\x00\xa3\x1dcom.microsoft:datetime-offset\x81\x08\xddW\x05\xc3Q\xcf\x10\x00St\xc1I\x02\xa1\rDiagnostic-Id\xa1700-bdc3fde4889b4e907e0c9dcb46ff8d92-21f637af293ef13b-00\x00Su\xa0\x08message1'
        )

        with self.assertRaises(ValueError) as e:
            datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
            result: EventHubData = EventHubDataConverter.decode(
                data=datum, trigger_metadata=None, pytype=EventHubData
            )
        self.assertEqual(
            e.exception.args[0],
            "Storage account connection string NotARealConnectionString does not exist. "
            "Please make sure that it is a defined App Setting.",
        )

    def test_none_input_populated(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content = b'\x00Sr\xc1\x8e\x08\xa3\x1bx-opt-sequence-number-epochT\xff\xa3\x15x-opt-sequence-numberU\x04\xa3\x0cx-opt-offset\x81\x00\x00\x00\x01\x00\x00\x010\xa3\x13x-opt-enqueued-time\x00\xa3\x1dcom.microsoft:datetime-offset\x81\x08\xddW\x05\xc3Q\xcf\x10\x00St\xc1I\x02\xa1\rDiagnostic-Id\xa1700-bdc3fde4889b4e907e0c9dcb46ff8d92-21f637af293ef13b-00\x00Su\xa0\x08message1'
        )

        with self.assertRaises(ValueError) as e:
            datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
            result: EventHubData = EventHubDataConverter.decode(
                data=datum, trigger_metadata=None, pytype=EventHubData
            )
        self.assertEqual(
            e.exception.args[0],
            "Storage account connection string cannot be None. Please provide a connection string.",
        )

    def test_input_invalid_pytype(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content = b'\x00Sr\xc1\x8e\x08\xa3\x1bx-opt-sequence-number-epochT\xff\xa3\x15x-opt-sequence-numberU\x04\xa3\x0cx-opt-offset\x81\x00\x00\x00\x01\x00\x00\x010\xa3\x13x-opt-enqueued-time\x00\xa3\x1dcom.microsoft:datetime-offset\x81\x08\xddW\x05\xc3Q\xcf\x10\x00St\xc1I\x02\xa1\rDiagnostic-Id\xa1700-bdc3fde4889b4e907e0c9dcb46ff8d92-21f637af293ef13b-00\x00Su\xa0\x08message1'
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: EventHubData = EventHubDataConverter.decode(
            data=datum, trigger_metadata=None, pytype="str"
        )

        self.assertIsNone(result)
