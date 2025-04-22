#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
import unittest
from enum import Enum
from typing import Optional

from azure.servicebus import ServiceBusReceivedMessage as ServiceBusSDK
from azurefunctions.extensions.base import Datum

from azurefunctions.extensions.bindings.servicebus import (ServiceBusReceivedMessage,
                                                           ServiceBusConverter)

SERVICEBUS_SAMPLE_CONTENT = b"_\241S\374f\335OI\202]\356\033|4<\373\000Sp\300\013\005@@pH\031\010\000@R\001\000Sq\301$\002\243\020x-opt-lock-token\230\374S\241_\335fIO\202]\356\033|4<\373\000Sr\301U\006\243\023x-opt-enqueued-time\203\000\000\001\216v\307\333\310\243\025x-opt-sequence-numberU\014\243\022x-opt-locked-until\203\000\000\001\216v\310\3067\000Ss\300?\r\241 f00d2a33551440389d68e299d31adc7c@@@@@@@\203\000\000\001\216\276\340\343\310\203\000\000\001\216v\307\333\310@@@\000Su\240\005hello"  # noqa


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


class TestServiceBusReceivedMessage(unittest.TestCase):
    def test_input_type(self):
        check_input_type = ServiceBusConverter.check_input_type_annotation
        self.assertTrue(check_input_type(ServiceBusReceivedMessage))
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(bytearray))

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

    def test_input_empty(self):
        datum: Datum = Datum(value={}, type="model_binding_data")
        result: ServiceBusReceivedMessage = ServiceBusConverter.decode(
            data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
        )
        self.assertIsNone(result)

    def test_input_populated(self):
        sample_mbd = MockMBD(
            version="1.0",
            source="AzureServiceBusReceivedMessage",
            content_type="application/octet-stream",
            content=SERVICEBUS_SAMPLE_CONTENT,
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

    def test_invalid_input_populated(self):
        content = {
            "Connection": "NotARealConnectionString",
            "ContainerName": "test-blob",
            "BlobName": "text.txt",
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content=json.dumps(content),
        )

        with self.assertRaises(ValueError) as e:
            datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
            _: ServiceBusReceivedMessage = ServiceBusConverter.decode(
                data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
            )
        self.assertEqual(
            e.exception.args[0],
            "Storage account connection string NotARealConnectionString"
            " does not exist. Please make sure that it is a defined App Setting.",
        )

    def test_none_input_populated(self):
        content = {
            "Connection": None,
            "ContainerName": "test-blob",
            "BlobName": "text.txt",
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content=json.dumps(content),
        )

        with self.assertRaises(ValueError) as e:
            datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
            _: ServiceBusReceivedMessage = ServiceBusConverter.decode(
                data=datum, trigger_metadata=None, pytype=ServiceBusReceivedMessage
            )
        self.assertEqual(
            e.exception.args[0],
            "Storage account connection string cannot be None."
            " Please provide a connection string.",
        )

    def test_input_populated_managed_identity_input(self):
        content = {
            "Connection": "input",
            "ContainerName": "test-blob",
            "BlobName": "text.txt",
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content=json.dumps(content),
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

    def test_input_populated_managed_identity_trigger(self):
        content = {
            "Connection": "trigger",
            "ContainerName": "test-blob",
            "BlobName": "text.txt",
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content=json.dumps(content),
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

    def test_input_invalid_pytype(self):
        content = {
            "Connection": "AzureWebJobsStorage",
            "ContainerName": "test-blob",
            "BlobName": "text.txt",
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="AzureStorageBlobs",
            content_type="application/json",
            content=json.dumps(content),
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: ServiceBusReceivedMessage = ServiceBusConverter.decode(
            data=datum, trigger_metadata=None, pytype="str"
        )

        self.assertIsNone(result)

    def test_blob_client_invalid_creation(self):
        # Create test binding
        mock_blob = MockBinding(
            name="blob", direction=MockBindingDirection.IN, data_type=None, type="blob"
        )

        # Create test input_types dict
        mock_input_types = {
            "blob": MockParamTypeInfo(binding_name="blobTrigger", pytype=bytes)
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr, logs = ServiceBusConverter.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )

        self.assertEqual(
            dict_repr,
            [
                '{"direction": "MockBindingDirection.IN", '
                '"type": "blob", '
                '"properties": '
                '{"SupportsDeferredBinding": false}}'
            ],
        )

        self.assertEqual(logs, {"blob": {bytes: "False"}})

    def test_blob_client_valid_creation(self):
        # Create test binding
        mock_blob = MockBinding(
            name="client",
            direction=MockBindingDirection.IN,
            data_type=None,
            type="blob",
        )

        # Create test input_types dict
        mock_input_types = {
            "client": MockParamTypeInfo(binding_name="blobTrigger",
                                        pytype=ServiceBusReceivedMessage)
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr, logs = ServiceBusConverter.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )

        self.assertEqual(
            dict_repr,
            [
                '{"direction": "MockBindingDirection.IN", '
                '"type": "blob", '
                '"properties": '
                '{"SupportsDeferredBinding": true}}'
            ],
        )

        self.assertEqual(logs, {"client": {ServiceBusReceivedMessage: "True"}})
