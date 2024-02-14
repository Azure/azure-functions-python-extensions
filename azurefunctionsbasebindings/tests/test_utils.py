# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest

from abc import ABC

from azfuncbindingbase import meta, utils, sdkType


class MockParamTypeInfo:
    def __init__(self, binding_name: str, pytype: type):
        self.binding_name = binding_name
        self.pytype = pytype


class MockFunction(ABC):
    def __init__(self, bindings: utils.Binding):
        self._bindings = bindings


class TestUtils(unittest.TestCase):
    # Test Utils class
    def test_get_dict_repr_sdk(self):
        # Create mock blob
        meta._ConverterMeta._bindings = {"blob"}

        # Create test binding
        mock_blob = utils.Binding(name="client",
                                  direction=utils.BindingDirection.IN,
                                  data_type=None, type='blob')

        # Create test input_types dict
        mock_input_types = {"client": MockParamTypeInfo(
            binding_name='blobTrigger', pytype=sdkType.SdkType)}

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr = utils.get_raw_bindings(mock_indexed_functions,
                                           mock_input_types)
        self.assertEqual(dict_repr,
                         ['{"direction": "IN", '
                          '"dataType": null, "type": "blob", '
                          '"properties": '
                          '{"SupportsDeferredBinding": true}}'])

    def test_get_dict_repr_non_sdk(self):
        # Create mock blob
        meta._ConverterMeta._bindings = {"blob"}

        # Create test binding
        mock_blob = utils.Binding(name="blob",
                                  direction=utils.BindingDirection.IN,
                                  data_type=None, type='blob')

        # Create test input_types dict
        mock_input_types = {"blob": MockParamTypeInfo(
            binding_name='blobTrigger', pytype=bytes)}

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr = utils.get_raw_bindings(mock_indexed_functions,
                                           mock_input_types)
        self.assertEqual(dict_repr,
                         ['{"direction": "IN", '
                          '"dataType": null, "type": "blob", '
                          '"properties": '
                          '{"SupportsDeferredBinding": false}}'])

    def test_to_camel_case(self):
        test_str = ""
        self.assertRaises(ValueError,
                          utils.to_camel_case, test_str)

        test_str = "1iAmNotAWord"
        self.assertRaises(ValueError,
                          utils.to_camel_case, test_str)

        test_str = utils.to_camel_case("string_in_correct_format")
        self.assertEqual(test_str, "stringInCorrectFormat")

    def test_is_snake_case(self):
        test_str = "foo_bar_baz"
        self.assertTrue(utils.is_snake_case(test_str))

        test_str = "foo"
        self.assertFalse(utils.is_snake_case(test_str))

    def test_is_word(self):
        test_str = "1foo"
        self.assertFalse(utils.is_word(test_str))

        test_str = "foo_"
        self.assertFalse(utils.is_word(test_str))

        test_str = "foo"
        self.assertTrue(utils.is_word(test_str))
