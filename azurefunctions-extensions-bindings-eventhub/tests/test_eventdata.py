#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import sys
import unittest
from typing import List, Optional

from azure.eventhub import EventData as EventDataSdk
from azurefunctions.extensions.base import Datum

from azurefunctions.extensions.bindings.eventhub import EventData, EventDataConverter

EVENTHUB_SAMPLE_CONTENT = b"\x00Sr\xc1\x8e\x08\xa3\x1bx-opt-sequence-number-epochT\xff\xa3\x15x-opt-sequence-numberU\x04\xa3\x0cx-opt-offset\x81\x00\x00\x00\x01\x00\x00\x010\xa3\x13x-opt-enqueued-time\x00\xa3\x1dcom.microsoft:datetime-offset\x81\x08\xddW\x05\xc3Q\xcf\x10\x00St\xc1I\x02\xa1\rDiagnostic-Id\xa1700-bdc3fde4889b4e907e0c9dcb46ff8d92-21f637af293ef13b-00\x00Su\xa0\x08message1"

# Mock classes for testing
class MockMBD:
    def __init__(self, version: str, source: str, content_type: str, content: str):
        self.version = version
        self.source = source
        self.content_type = content_type
        self.content = content

    @property
    def data_type(self) -> Optional[int]:
        return self._data_type.value if self._data_type else None

    @property
    def direction(self) -> int:
        return self._direction.value
    
    
class MockCMBD:
    def __init__(self, model_binding_data_list: List[MockMBD]):
        self.model_binding_data = model_binding_data_list

    @property
    def data_type(self) -> Optional[int]:
        return self._data_type.value if self._data_type else None

    @property
    def direction(self) -> int:
        return self._direction.value


class TestEventData(unittest.TestCase):
    def test_input_type(self):
        check_input_type = EventDataConverter.check_input_type_annotation

        # Generic types are not subscriptable in Python < 3.9
        if sys.version_info >= (3, 9):
            self.assertTrue(check_input_type(list[EventData]))
            self.assertTrue(check_input_type(tuple[EventData]))
        self.assertTrue(check_input_type(EventData))
        self.assertTrue(check_input_type(List[EventData]))
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(bytearray))
        self.assertFalse(check_input_type(dict[str, EventData]))

    def test_input_none(self):
        result = EventDataConverter.decode(
            data=None, trigger_metadata=None, pytype=EventData
        )
        self.assertIsNone(result)

        datum: Datum = Datum(value=b"string_content", type=None)
        result = EventDataConverter.decode(
            data=datum, trigger_metadata=None, pytype=EventData
        )
        self.assertIsNone(result)

    def test_input_incorrect_type(self):
        datum: Datum = Datum(value=b"string_content", type="bytearray")
        with self.assertRaises(ValueError):
            EventDataConverter.decode(
                data=datum, trigger_metadata=None, pytype=EventData
            )

    def test_input_empty_mbd(self):
        datum: Datum = Datum(value={}, type="model_binding_data")
        result: EventData = EventDataConverter.decode(
            data=datum, trigger_metadata=None, pytype=EventData
        )
        self.assertIsNone(result)

    def test_input_empty_cmbd(self):
        datum: Datum = Datum(value={}, type="collection_model_binding_data")
        result: EventData = EventDataConverter.decode(
            data=datum, trigger_metadata=None, pytype=EventData
        )
        self.assertIsNone(result)

    def test_input_populated_mbd(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureEventHubsEventData",
            content_type="application/octet-stream",
            content = EVENTHUB_SAMPLE_CONTENT
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: EventData = EventDataConverter.decode(
            data=datum, trigger_metadata=None, pytype=EventData
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, EventDataSdk)

        sdk_result = EventData(data=datum.value).get_sdk_type()

        self.assertIsNotNone(sdk_result)
        self.assertIsInstance(sdk_result, EventDataSdk)

    def test_input_populated_cmbd(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureEventHubsEventData",
            content_type="application/octet-stream",
            content = EVENTHUB_SAMPLE_CONTENT
        )

        datum: Datum = Datum(value=MockCMBD([sample_mbd, sample_mbd]), type="collection_model_binding_data")
        result: EventData = EventDataConverter.decode(
            data=datum, trigger_metadata=None, pytype=EventData
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, EventDataSdk)

        sdk_result = EventData(data=datum.value).get_sdk_type()

        self.assertIsNotNone(sdk_result)
        self.assertIsInstance(sdk_result, EventDataSdk)

    def test_input_invalid_pytype(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureEventHubsEventData",
            content_type="application/octet-stream",
            content = EVENTHUB_SAMPLE_CONTENT
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: EventData = EventDataConverter.decode(
            data=datum, trigger_metadata=None, pytype="str"
        )

        self.assertIsNone(result)
