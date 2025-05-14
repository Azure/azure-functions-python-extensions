#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest
from typing import List, Optional


from azure.servicebus import ServiceBusReceivedMessage as ServiceBusSDK
from azurefunctions.extensions.base import Datum

from azurefunctions.extensions.bindings.servicebus import (ServiceBusReceivedMessage,
                                                           ServiceBusConverter)
from azurefunctions.extensions.bindings.servicebus.utils import get_decoded_message


SERVICEBUS_SAMPLE_CONTENT = b"_\241S\374f\335OI\202]\356\033|4<\373\000Sp\300\013\005@@pH\031\010\000@R\001\000Sq\301$\002\243\020x-opt-lock-token\230\374S\241_\335fIO\202]\356\033|4<\373\000Sr\301U\006\243\023x-opt-enqueued-time\203\000\000\001\216v\307\333\310\243\025x-opt-sequence-numberU\014\243\022x-opt-locked-until\203\000\000\001\216v\310\3067\000Ss\300?\r\241 f00d2a33551440389d68e299d31adc7c@@@@@@@\203\000\000\001\216\276\340\343\310\203\000\000\001\216v\307\333\310@@@\000Su\240\005hello"  # noqa: E501


# Mock classes for testing
class MockMBD:
    def __init__(self, version: str, source: str, content_type: str, content: str):
        self.version = version
        self.source = source
        self.content_type = content_type
        self.content = content


class MockCMBD:
    def __init__(self, model_binding_data_list: List[MockMBD]):
        self.model_binding_data = model_binding_data_list

    @property
    def data_type(self) -> Optional[int]:
        return self._data_type.value if self._data_type else None

    @property
    def direction(self) -> int:
        return self._direction.value


class TestServiceBus(unittest.TestCase):
    def test_input_type(self):
        check_input_type = ServiceBusConverter.check_input_type_annotation
        self.assertTrue(check_input_type(ServiceBusReceivedMessage))
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type("hello"))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(bytearray))
        self.assertTrue(check_input_type(List[ServiceBusReceivedMessage]))
        self.assertTrue(check_input_type(list[ServiceBusReceivedMessage]))
        self.assertTrue(check_input_type(tuple[ServiceBusReceivedMessage]))
        self.assertTrue(check_input_type(set[ServiceBusReceivedMessage]))
        self.assertFalse(check_input_type(dict[str, ServiceBusReceivedMessage]))

    def test_input_none(self):
        result = ServiceBusConverter.decode(
            data=None, trigger_metadata=None, pytype=ServiceBusReceivedMessage
        )
        self.assertIsNone(result)

        datum: Datum = Datum(value=b"string_content", type=None)
        result = ServiceBusConverter.decode(
            data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
        )
        self.assertIsNone(result)

    def test_input_incorrect_type(self):
        datum: Datum = Datum(value=b"string_content", type="bytearray")
        with self.assertRaises(ValueError):
            ServiceBusConverter.decode(
                data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
            )

    def test_input_empty_mbd(self):
        datum: Datum = Datum(value={}, type="model_binding_data")
        result: ServiceBusReceivedMessage = ServiceBusConverter.decode(
            data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
        )
        self.assertIsNone(result)

    def test_input_empty_cmbd(self):
        datum: Datum = Datum(value=MockCMBD([None]),
                             type="collection_model_binding_data")
        result: ServiceBusReceivedMessage = ServiceBusConverter.decode(
            data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
        )
        self.assertEqual(result, [None])

    def test_input_populated_mbd(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureServiceBusReceivedMessage",
            content_type="application/octet-stream",
            content=SERVICEBUS_SAMPLE_CONTENT
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: ServiceBusReceivedMessage = ServiceBusConverter.decode(
            data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, ServiceBusSDK)

        sdk_result = ServiceBusReceivedMessage(data=datum.value).get_sdk_type()

        self.assertIsNotNone(sdk_result)
        self.assertIsInstance(sdk_result, ServiceBusSDK)

    def test_input_populated_cmbd(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureServiceBusReceivedMessage",
            content_type="application/octet-stream",
            content=SERVICEBUS_SAMPLE_CONTENT
        )

        datum: Datum = Datum(value=MockCMBD([sample_mbd, sample_mbd]),
                             type="collection_model_binding_data")
        result: ServiceBusReceivedMessage = ServiceBusConverter.decode(
            data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
        )

        self.assertIsNotNone(result)
        for event_data in result:
            self.assertIsInstance(event_data, ServiceBusSDK)

        sdk_results = []
        for mbd in datum.value.model_binding_data:
            sdk_results.append(ServiceBusReceivedMessage(data=mbd).get_sdk_type())

        self.assertNotEqual(sdk_results, [None, None])
        for event_data in sdk_results:
            self.assertIsInstance(event_data, ServiceBusSDK)

    def test_input_invalid_datum_type(self):
        with self.assertRaises(ValueError) as e:
            datum: Datum = Datum(value="hello", type="str")
            _: ServiceBusReceivedMessage = ServiceBusConverter.decode(
                data=datum, trigger_metadata=None, pytype=""
            )
        self.assertEqual(
            e.exception.args[0],
            "Unexpected type of data received for the 'servicebus' binding: 'str'",
        )

    def test_input_get_decoded_message_ex(self):
        with self.assertRaises(ValueError) as e:
            _ = get_decoded_message("Invalid message")

        self.assertIn("Failed to decode ServiceBus content", e.exception.args[0])
