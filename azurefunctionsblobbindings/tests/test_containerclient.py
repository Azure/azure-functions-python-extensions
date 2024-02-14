#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import unittest
from typing import Optional
from enum import Enum

from azfuncbindingbase import Datum

from azfuncblobclient import ContainerClient
from azfuncblobclient import BlobClientConverter

from azure.storage.blob import ContainerClient as ContainerClientSdk


# Mock classes for testing
class MockMBD:
    def __init__(self, version: str, source: str,
                 content_type: str, content: str):
        self.version = version
        self.source = source
        self.content_type = content_type
        self.content = content


class MockBindingDirection(Enum):
    IN = 0
    OUT = 1
    INOUT = 2


class MockBinding:
    def __init__(self, name: str,
                 direction: MockBindingDirection,
                 data_type=None,
                 type: Optional[str] = None):  # NoQa
        self.type = type
        self.name = name
        self._direction = direction
        self._data_type = data_type
        self._dict = {
            "direction": self._direction,
            "dataType": self._data_type,
            "type": self.type
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


class TestContainerClient(unittest.TestCase):
    def test_input_type(self):
        check_input_type = BlobClientConverter.check_input_type_annotation
        self.assertTrue(check_input_type(ContainerClient))
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(bytearray))

    def test_input_none(self):
        result = BlobClientConverter.decode(
            data=None, trigger_metadata=None, pytype=ContainerClient)
        self.assertIsNone(result)

    def test_input_incorrect_type(self):
        datum: Datum = Datum(value=b'string_content', type='bytearray')
        with self.assertRaises(ValueError):
            BlobClientConverter.decode(data=datum,
                                       trigger_metadata=None,
                                       pytype=ContainerClient)

    def test_input_empty(self):
        datum: Datum = Datum(value={}, type='model_binding_data')
        result: ContainerClient = BlobClientConverter.decode(
            data=datum, trigger_metadata=None, pytype=ContainerClient)
        self.assertIsNone(result)

    def test_input_populated(self):
        sample_mbd = MockMBD(version="1.0",
                             source="AzureStorageBlobs",
                             content_type="application/json",
                             content="{\"Connection\":\"AzureWebJobsStorage\","
                                     "\"ContainerName\":\"test-blob\","
                                     "\"BlobName\":\"test.txt\"}")

        datum: Datum = Datum(value=sample_mbd, type='model_binding_data')
        result: ContainerClient = BlobClientConverter.decode(
            data=datum,
            trigger_metadata=None,
            pytype=ContainerClient)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, ContainerClient)

        sdk_result = ContainerClient(data=datum).get_sdk_type()
        self.assertIsNotNone(sdk_result)
        self.assertIsInstance(sdk_result, ContainerClientSdk)

    def test_container_client_invalid_creation(self):
        # Create test binding
        mock_blob = MockBinding(name="blob",
                                direction=MockBindingDirection.IN,
                                data_type=None, type='blob')

        # Create test input_types dict
        mock_input_types = {"blob": MockParamTypeInfo(
            binding_name='blobTrigger', pytype=bytes)}

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr = BlobClientConverter.get_raw_bindings(
            mock_indexed_functions, mock_input_types)

        self.assertEqual(dict_repr,
                         ['{"direction": "MockBindingDirection.IN", '
                          '"dataType": null, "type": "blob", '
                          '"properties": '
                          '{"SupportsDeferredBinding": false}}'])

    def test_container_client_valid_creation(self):
        # Create test binding
        mock_blob = MockBinding(name="client",
                                direction=MockBindingDirection.IN,
                                data_type=None, type='blob')

        # Create test input_types dict
        mock_input_types = {"client": MockParamTypeInfo(
            binding_name='blobTrigger', pytype=ContainerClient)}

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr = BlobClientConverter.get_raw_bindings(
            mock_indexed_functions, mock_input_types)

        self.assertEqual(dict_repr,
                         ['{"direction": "MockBindingDirection.IN", '
                          '"dataType": null, "type": "blob", '
                          '"properties": '
                          '{"SupportsDeferredBinding": true}}'])
