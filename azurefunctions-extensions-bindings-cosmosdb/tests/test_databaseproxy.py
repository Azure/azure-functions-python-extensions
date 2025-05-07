#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
import unittest
from enum import Enum
from typing import Optional

from azure.cosmos import DatabaseProxy as DatabaseProxySdk
from azurefunctions.extensions.base import Datum

from azurefunctions.extensions.bindings.cosmosdb import (
    CosmosClientConverter, DatabaseProxy
)


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


class TestDatabaseProxy(unittest.TestCase):
    def test_input_type(self):
        check_input_type = CosmosClientConverter.check_input_type_annotation
        self.assertTrue(check_input_type(DatabaseProxy))
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(bytearray))

    def test_input_none(self):
        result = CosmosClientConverter.decode(
            data=None, trigger_metadata=None, pytype=DatabaseProxy
        )
        self.assertIsNone(result)

        datum: Datum = Datum(value=b"string_content", type=None)
        result = CosmosClientConverter.decode(
            data=datum, trigger_metadata=None, pytype=DatabaseProxy
        )
        self.assertIsNone(result)

    def test_input_incorrect_type(self):
        datum: Datum = Datum(value=b"string_content", type="bytearray")
        with self.assertRaises(ValueError):
            CosmosClientConverter.decode(
                data=datum, trigger_metadata=None, pytype=DatabaseProxy
            )

    def test_input_empty(self):
        datum: Datum = Datum(value={}, type="model_binding_data")
        with self.assertRaises(ValueError):
            CosmosClientConverter.decode(
                data=datum, trigger_metadata=None, pytype=DatabaseProxy
            )

    def test_input_populated(self):
        content = {
            "DatabaseName": "test-db",
            "ContainerName": "test-items",
            "Connection": "CosmosDBConnection"
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="CosmosDB",
            content_type="application/json",
            content=json.dumps(content),
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: DatabaseProxy = CosmosClientConverter.decode(
            data=datum, trigger_metadata=None, pytype=DatabaseProxy
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, DatabaseProxySdk)

        sdk_result = DatabaseProxy(data=datum.value).get_sdk_type()

        self.assertIsNotNone(sdk_result)
        self.assertIsInstance(sdk_result, DatabaseProxySdk)

    def test_invalid_input_populated(self):
        content = {
            "DatabaseName": "test-db",
            "ContainerName": "test-items",
            "Connection": "NotARealConnectionString"
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="CosmosDB",
            content_type="application/json",
            content=json.dumps(content),
        )

        with self.assertRaises(ValueError) as e:
            datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
            CosmosClientConverter.decode(
                data=datum, trigger_metadata=None, pytype=DatabaseProxy
            )
        self.assertEqual(
            e.exception.args[0],
            "Cosmos DB connection string NotARealConnectionString does not exist. "
            "Please make sure that it is a defined App Setting.",
        )

    def test_none_input_populated(self):
        content = {
            "DatabaseName": "test-db",
            "ContainerName": "test-items",
            "Connection": None
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="CosmosDB",
            content_type="application/json",
            content=json.dumps(content),
        )

        with self.assertRaises(ValueError) as e:
            datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
            CosmosClientConverter.decode(
                data=datum, trigger_metadata=None, pytype=DatabaseProxy
            )
        self.assertEqual(
            e.exception.args[0],
            "Cosmos DB connection string cannot be None. "
            "Please provide a connection string or account endpoint.",
        )

    def test_input_populated_managed_identity_input(self):
        content = {
            "DatabaseName": "test-db",
            "ContainerName": "test-items",
            "Connection": "input"
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="CosmosDB",
            content_type="application/json",
            content=json.dumps(content),
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: DatabaseProxy = CosmosClientConverter.decode(
            data=datum, trigger_metadata=None, pytype=DatabaseProxy
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, DatabaseProxySdk)

        sdk_result = DatabaseProxy(data=datum.value).get_sdk_type()

        self.assertIsNotNone(sdk_result)
        self.assertIsInstance(sdk_result, DatabaseProxySdk)

    def test_input_invalid_pytype(self):
        content = {
            "DatabaseName": "test-db",
            "ContainerName": "test-items",
            "Connection": "CosmosDBConnection"
        }

        sample_mbd = MockMBD(
            version="1.0",
            source="CosmosDB",
            content_type="application/json",
            content=json.dumps(content),
        )

        datum: Datum = Datum(value=sample_mbd, type="model_binding_data")
        result: DatabaseProxy = CosmosClientConverter.decode(
            data=datum, trigger_metadata=None, pytype="str"
        )

        self.assertIsNone(result)

    def test_database_proxy_invalid_creation(self):
        # Create test binding
        mock_cosmos = MockBinding(
            name="cosmosDB", direction=MockBindingDirection.IN, data_type=None,
            type="cosmosDB"
        )

        # Create test input_types dict
        mock_input_types = {
            "cosmosDB": MockParamTypeInfo(binding_name="cosmosDB", pytype=bytes)
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_cosmos])

        dict_repr, logs = CosmosClientConverter.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )

        self.assertEqual(
            dict_repr,
            [
                '{"direction": "MockBindingDirection.IN", '
                '"type": "cosmosDB", '
                '"properties": '
                '{"SupportsDeferredBinding": false}}'
            ],
        )

        self.assertEqual(logs, {"cosmosDB": {bytes: "False"}})

    def test_database_proxy_valid_creation(self):
        # Create test binding
        mock_cosmos = MockBinding(
            name="client",
            direction=MockBindingDirection.IN,
            data_type=None,
            type="cosmosDB",
        )

        # Create test input_types dict
        mock_input_types = {
            "client": MockParamTypeInfo(
                binding_name="cosmosDB", pytype=DatabaseProxy
            )
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_cosmos])

        dict_repr, logs = CosmosClientConverter.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )

        self.assertEqual(
            dict_repr,
            [
                '{"direction": "MockBindingDirection.IN", '
                '"type": "cosmosDB", '
                '"properties": '
                '{"SupportsDeferredBinding": true}}'
            ],
        )

        self.assertEqual(logs, {"client": {DatabaseProxy: "True"}})
